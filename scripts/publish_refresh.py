#!/usr/bin/env python3
"""Publish generated refresh data from current main, with bounded race recovery."""
import argparse
import datetime as dt
import os
from pathlib import Path
import subprocess
import time

TASKS = {
    'wire': {
        'commands': [
            ['python3', 'scripts/refresh_wire.py'],
            ['python3', 'scripts/build_ticker.py'],
            ['python3', 'scripts/build_ai_strip.py'],
            ['python3', 'scripts/fetch_watch_results.py'],
            ['python3', 'scripts/log_sentiment.py'],
        ],
        'paths': ['site/assets/wire.json', 'site/assets/wire-archive.json',
                  'site/index.html', 'data/wire-state.json',
                  'site/assets/ticker.json', 'site/assets/ai-tools.json',
                  'site/assets/watch-today.json', 'site/assets/sentiment-history.json'],
        'fallback': 'Refresh The Wire',
    },
    'crypto': {
        'commands': [['python3', 'scripts/refresh_crypto.py']],
        'paths': ['site/assets/crypto.json'],
        'fallback': 'Refresh crypto ticker',
    },
}


def run(args, check=True):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    if result.stdout:
        print(result.stdout, end='', flush=True)
    if check and result.returncode:
        raise subprocess.CalledProcessError(result.returncode, args)
    return result


def cycle_key(task, cycle):
    if not cycle:
        return None  # Manual runs remain available and never dedupe each other.
    timestamp = dt.datetime.fromisoformat(cycle.replace('Z', '+00:00'))
    if timestamp.tzinfo is None:
        raise ValueError('Cycle must include a timezone')
    timestamp = timestamp.astimezone(dt.timezone.utc)
    timestamp = timestamp.replace(minute=timestamp.minute // 15 * 15,
                                  second=0, microsecond=0)
    return task + ':' + timestamp.isoformat().replace('+00:00', 'Z')


def publish(task, cycle='', attempts=3, generator=None, pause=time.sleep):
    config = TASKS[task]
    key = cycle_key(task, cycle)
    if run(['git', 'status', '--porcelain'], check=True).stdout.strip():
        raise RuntimeError('Publisher requires a clean CI checkout')
    run(['git', 'config', 'user.name', 'github-actions[bot]'])
    run(['git', 'config', 'user.email',
         '41898282+github-actions[bot]@users.noreply.github.com'])
    for attempt in range(1, attempts + 1):
        # An interrupted/failed rebase must be cleared before any new attempt.
        if Path(run(['git', 'rev-parse', '--git-path', 'rebase-merge']).stdout.strip()).exists() or Path(run(['git', 'rev-parse', '--git-path', 'rebase-apply']).stdout.strip()).exists():
            run(['git', 'rebase', '--abort'])
        run(['git', 'fetch', 'origin', 'main'])
        run(['git', 'checkout', '-B', 'main', 'origin/main'])
        if key:
            history = run(['git', 'log', '-300', '--format=%B', 'origin/main']).stdout
            if 'Refresh-Cycle: ' + key in history.splitlines():
                print('Cycle already published; skip generation and deploy', flush=True)
                return False
        if generator is None:
            outputs = [run(command).stdout for command in config['commands']]
        else:
            outputs = [generator(attempt)]
        changed = run(['git', 'diff', '--name-only']).stdout.splitlines()
        untracked = run(['git', 'ls-files', '--others', '--exclude-standard']).stdout.splitlines()
        if set(changed + untracked) - set(config['paths']):
            raise RuntimeError('Generator changed a file outside its owned output')
        # A no-change cycle still gets a receipt, so its duplicate stays a no-op.
        run(['git', 'add', '--', *config['paths']])
        subject = next((line.removeprefix('COMMIT_MSG=')
                        for output in outputs for line in output.splitlines()
                        if line.startswith('COMMIT_MSG=')), config['fallback'])
        command = ['git', 'commit']
        if key:
            command += ['--allow-empty']
        elif not changed and not untracked:
            print('Manual run: no changes')
            return False
        command += ['-m', subject]
        if key:
            command += ['-m', 'Refresh-Cycle: ' + key]
        run(command)
        result = run(['git', 'push', 'origin', 'HEAD:main'], check=False)
        if result.returncode == 0:
            return True
        # Only an observed remote advance is a publish race. Auth, network,
        # protection and other push failures stay red, with no fake recovery.
        local_base = run(['git', 'rev-parse', 'origin/main']).stdout.strip()
        run(['git', 'fetch', 'origin', 'main'])
        remote = run(['git', 'rev-parse', 'origin/main']).stdout.strip()
        if remote == local_base or attempt == attempts:
            raise RuntimeError('Publish failed; no recoverable race or retries exhausted')
        print('Remote main advanced; discard stale generated commit and rebuild', flush=True)
        run(['git', 'reset', '--hard', 'origin/main'])
        pause(attempt * 5)
    raise RuntimeError('Publish retries exhausted')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', choices=TASKS, required=True)
    parser.add_argument('--cycle', default='')
    args = parser.parse_args()
    published = publish(args.task, args.cycle)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('published=' + str(published).lower() + '\n')


if __name__ == '__main__':
    main()
