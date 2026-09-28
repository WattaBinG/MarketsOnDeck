"""No-key, primary-source weekly Watch Today numbers. Never accept an old release.

EIA: official WPSR JSON, U.S. commercial crude stocks excluding SPR.
DOL: official UI weekly claims PDF, seasonally adjusted initial claims.
The publication date and reference week must match the scheduled event date.
"""
import json
import re
from datetime import date, timedelta
from io import BytesIO
from urllib.request import Request, urlopen

EIA_URL = 'https://ir.eia.gov/wpsr/psw00.json'
DOL_URL = 'https://www.dol.gov/ui/data.pdf'
UA = 'MarketsOnDeck calendar bot (+https://marketsondeck.net/)'


def _read(url):
    with urlopen(Request(url, headers={'User-Agent': UA}), timeout=25) as response:
        return response.read()


def kind_for(label):
    if re.fullmatch(r'EIA Weekly Petroleum Status Report', label, re.I):
        return 'crude_stocks'
    if re.fullmatch(r'Initial Jobless Claims', label, re.I):
        return 'initial_claims'
    return None


def _date(s):
    return date.fromisoformat(s)


def _signed_millions(delta_thousand):
    if abs(delta_thousand) > 30000:
        raise ValueError('implausible weekly crude stocks change')
    return f'{delta_thousand / 1000:+.1f}M bbl'


def eia(today, actual=True, payload=None):
    """Return current release's change (Act), or previous release's change (Prev)."""
    doc = json.loads(payload if payload is not None else _read(EIA_URL))
    meta = doc['metadata']
    if meta['source'] != 'U.S. Energy Information Administration' or meta['release_name'] != 'Weekly Petroleum Status Report':
        raise ValueError('unexpected EIA dataset')
    release = _date(meta['release_date'])
    # Next Wednesday's previous print is good for Prev; only today's print is Act.
    expected = today if actual else today - timedelta(days=7)
    if release != expected:
        raise ValueError(f'EIA release {release} is not expected date for {today}')
    series = doc['data']['U.S.']
    if series['sourcekey'] != 'WCESTUS1' or series['units'] != 'thousand barrels':
        raise ValueError('unexpected EIA series or units')
    points = series['time_series'][-2:]
    if len(points) != 2 or any(p['suppression_flag'] is not None for p in points):
        raise ValueError('EIA values unavailable')
    if _date(points[-1]['date']) != release - timedelta(days=5):
        raise ValueError('EIA reference week is not current')
    if _date(points[-2]['date']) != _date(points[-1]['date']) - timedelta(days=7):
        raise ValueError('EIA weekly sequence invalid')
    a, b = points[-1], points[-2]
    return 'crude stocks ' + _signed_millions(float(a['value']) - float(b['value']))


def _dol_text(payload):
    from pypdf import PdfReader
    reader = PdfReader(BytesIO(payload))
    # News-release headline and seasonally adjusted figure are on the first page.
    return reader.pages[0].extract_text(extraction_mode='plain')


def dol(today, actual=True, payload=None):
    """Return seasonally adjusted initial claims, never unadjusted claims."""
    text = _dol_text(payload if payload is not None else _read(DOL_URL))
    normalized = re.sub(r'\s+', ' ', text)
    m = re.search(r'EMBARGOED UNTIL\s+8:30 A\.M\.\s*\(Eastern\)\s+\w+,\s+(\w+ \d{1,2}, 20\d\d)', normalized, re.I)
    if not m:
        raise ValueError('DOL publication date not found')
    from datetime import datetime
    release = datetime.strptime(m.group(1), '%B %d, %Y').date()
    expected = today if actual else today - timedelta(days=7)
    if release != expected:
        raise ValueError(f'DOL release {release} is not expected date for {today}')
    m = re.search(r'SEASONALLY ADJUSTED DATA\s+In the week ending\s+(\w+ \d{1,2}),\s+the advance figure for seasonally adjusted initial claims was\s+([\d,]+),', normalized, re.I)
    if not m:
        raise ValueError('DOL seasonally adjusted initial claims not found')
    week = datetime.strptime(m.group(1) + ' ' + str(release.year), '%B %d %Y').date()
    if week != release - timedelta(days=5):
        raise ValueError('DOL reference week is not current')
    value = int(m.group(2).replace(',', ''))
    if not 100000 <= value <= 2000000:
        raise ValueError('implausible claims figure')
    return f'{value // 1000:,}K' if value % 1000 == 0 else f'{value / 1000:.1f}K'


def value(kind, today, actual=True):
    if kind == 'crude_stocks':
        return eia(today, actual)
    if kind == 'initial_claims':
        return dol(today, actual)
    raise ValueError(f'unknown official kind {kind}')
