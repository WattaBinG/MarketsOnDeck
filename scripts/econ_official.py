"""No-key, primary-source weekly Watch Today numbers. Never accept an old release.

EIA: official WPSR JSON, U.S. commercial crude stocks excluding SPR.
DOL: official UI weekly claims PDF, seasonally adjusted initial claims.
The publication date and reference week must match the scheduled event date.
"""
import json
import re
from datetime import date, timedelta, datetime
from io import BytesIO
from urllib.request import Request, urlopen

EIA_URL = 'https://ir.eia.gov/wpsr/psw00.json'
DOL_URL = 'https://www.dol.gov/ui/data.pdf'
EIA_GAS_URL = 'https://ir.eia.gov/ngs/wngsr.json'
UA = 'MarketsOnDeck calendar bot (+https://marketsondeck.net/)'


def _read(url):
    with urlopen(Request(url, headers={'User-Agent': UA}), timeout=25) as response:
        return response.read()


def kind_for(label):
    if re.fullmatch(r'EIA Weekly Petroleum Status Report', label, re.I):
        return 'crude_stocks'
    if re.fullmatch(r'Initial Jobless Claims', label, re.I):
        return 'initial_claims'
    if re.fullmatch(r'EIA Weekly Natural Gas Storage Report', label, re.I):
        return 'natural_gas_storage'
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


def eia_gas(today, actual=True, payload=None):
    """Lower-48 net weekly storage change, tied to release and reference week."""
    raw = payload if payload is not None else _read(EIA_GAS_URL)
    doc = json.loads(raw.decode('utf-8-sig') if isinstance(raw, bytes) else raw)
    expected = today if actual else today - timedelta(days=7)
    stamp = doc['release_date'][:10 if doc['release_date'][5:7].isdigit() else 11]
    release = (date.fromisoformat(stamp) if stamp[5:7].isdigit()
               else datetime.strptime(stamp, '%Y-%b-%d').date())
    if doc.get('release_name') != 'Weekly Natural Gas Storage Report' or release != expected:
        raise ValueError(f'EIA gas release {release} is not expected date for {today}')
    if _date(doc['current_week']) != release - timedelta(days=6) or _date(doc['week_ago']) != release - timedelta(days=13):
        raise ValueError('EIA gas reference week is not current')
    series = next((s for s in doc['series'] if s.get('series_id') == 'png.nw2_epg0_swo_r48_bcf.w'), None)
    if not series or series.get('units') != 'billion cubic feet' or series.get('source') != 'U.S. Energy Information Administration':
        raise ValueError('unexpected EIA gas series')
    points = series['data'][:2]
    if len(points) != 2 or [p[0] for p in points] != [doc['current_week'], doc['week_ago']]:
        raise ValueError('EIA gas series week mismatch')
    delta = float(points[0][1]) - float(points[1][1])
    if abs(delta) > 1000 or delta != float(series['calculated']['net_change']):
        raise ValueError('implausible EIA gas change')
    return f'natural gas {delta:+.0f} Bcf'


def value(kind, today, actual=True):
    if kind == 'crude_stocks':
        return eia(today, actual)
    if kind == 'initial_claims':
        return dol(today, actual)
    if kind == 'natural_gas_storage':
        return eia_gas(today, actual)
    raise ValueError(f'unknown official kind {kind}')
