"""Offline integration tests: only temporary local repositories, no live data."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
spec = importlib.util.spec_from_file_location('publisher', Path(__file__).with_name('publish_refresh.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.previous = Path.cwd()
        self.remote = self.base / 'remote.git'
        self.work = self.base / 'work'
        self.other = self.base / 'other'
        self.git('init', '--bare', str(self.remote))
        self.git('clone', str(self.remote), str(self.work))
        os.chdir(self.work)
        self.git('checkout', '-b', 'main')
        self.git('config', 'user.name', 'test')
        self.git('config', 'user.email', 'test@example.invalid')
        Path('site/assets').mkdir(parents=True)
        Path('site/assets/crypto.json').write_text('initial\n')
        self.git('add', '.')
        self.git('commit', '-m', 'initial')
        self.git('push', 'origin', 'main')
        self.git('clone', '-b', 'main', str(self.remote), str(self.other))
        self.git('-C', str(self.other), 'config', 'user.name', 'other')
        self.git('-C', str(self.other), 'config', 'user.email', 'other@example.invalid')
        self.calls = []
    def tearDown(self):
        os.chdir(self.previous)
        self.tmp.cleanup()
    def git(self, *args):
        return subprocess.run(['git', *args], check=True, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    def generate(self, attempt):
        self.calls.append(attempt)
        Path('site/assets/crypto.json').write_text(f'generated-{attempt}\n')
        return 'COMMIT_MSG=Test refresh'
    def publish(self, generator=None, cycle='2026-10-07T05:15:30Z'):
        with contextlib.redirect_stdout(io.StringIO()):
            return p.publish('crypto', cycle, generator=generator or self.generate, pause=lambda _: None)
    def test_duplicate_normalizes_seconds_and_skips_deploy(self):
        self.assertTrue(self.publish())
        self.assertFalse(self.publish(cycle='2026-10-07T05:15:25Z'))
        self.assertEqual(self.calls, [1])
    def test_publish_race_regenerates_from_new_main(self):
        def race(attempt):
            if attempt == 1:
                (self.other/'site/assets/crypto.json').write_text('other refresh\n')
                self.git('-C',str(self.other),'add','.')
                self.git('-C',str(self.other),'commit','-m','other refresh')
                self.git('-C',str(self.other),'push','origin','main')
            return self.generate(attempt)
        self.assertTrue(self.publish(race))
        self.assertEqual(self.calls,[1,2])
        self.assertEqual(Path('site/assets/crypto.json').read_text(),'generated-2\n')
    def test_generator_failure_stays_red(self):
        before=self.git('rev-parse','origin/main')
        def fail(attempt): raise RuntimeError('source failed')
        with self.assertRaisesRegex(RuntimeError,'source failed'):self.publish(fail)
        self.assertEqual(before,self.git('rev-parse','origin/main'))
    def test_push_denial_stays_red(self):
        hook=self.remote/'hooks/pre-receive';hook.write_text('#!/bin/sh\nexit 1\n');hook.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError,'no recoverable race'):self.publish()
        self.assertEqual(self.calls,[1])
    def test_no_change_cycle_has_receipt(self):
        self.assertTrue(self.publish(lambda _: 'unchanged'))
        self.assertFalse(self.publish(lambda _: self.fail('must not generate again')))
    def test_manual_runs_not_deduped(self):
        self.assertTrue(self.publish(cycle=''))
        self.assertFalse(self.publish(lambda _: 'unchanged',cycle=''))
    def test_outside_owned_output_rejected(self):
        def bad(_):Path('trades.json').write_text('not allowed');return ''
        with self.assertRaisesRegex(RuntimeError,'outside'):self.publish(bad)

if __name__=='__main__':unittest.main()
