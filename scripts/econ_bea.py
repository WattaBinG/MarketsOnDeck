"""Keyless BEA headline actuals. Match both release day and reference period."""
import html
import re
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import urljoin

LIST_URL = 'https://www.bea.gov/news/current-releases'
UA = 'MarketsOnDeck calendar bot (+https://marketsondeck.net/)'


def _text(markup):
    return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', markup))).strip()


def _read(url):
    with urlopen(Request(url, headers={'User-Agent': UA}), timeout=25) as r:
        return r.read().decode('utf-8', 'replace')


def kind_for(label):
    if re.match(r'^(?:Gross Domestic Product|GDP)\s*[,\(]', label, re.I) and re.search(r'\d(?:st|nd|rd|th) Quarter', label, re.I):
        return 'gdp'
    if re.match(r'^Personal Income and Outlays,?\s+[A-Z][a-z]+ 20\d\d', label, re.I):
        return 'pce'
    return None


def _period(kind, label):
    if kind == 'gdp':
        m = re.search(r'(\d)(?:st|nd|rd|th) Quarter(?: and Year)? 20(\d\d)', label, re.I)
        if not m: raise ValueError('GDP period not identified')
        return int('20' + m[2]), int(m[1])
    m = re.search(r'([A-Z][a-z]+) (20\d\d)', label)
    if not m: raise ValueError('PCE period not identified')
    return int(m[2]), datetime.strptime(m[1], '%B').month


def _candidate(kind, title, period):
    if kind == 'gdp':
        m = re.search(r'(\d)(?:st|nd|rd|th) Quarter(?: and Year)? 20(\d\d)', title, re.I)
        return bool(m and (int('20' + m[2]), int(m[1])) == period and re.match(r'^(GDP|Gross Domestic Product)\s*[,\(]', title, re.I))
    m = re.search(r'Personal Income and Outlays,?\s+([A-Z][a-z]+) (20\d\d)', title, re.I)
    return bool(m and (int(m[2]), datetime.strptime(m[1], '%B').month) == period)


def value(kind, label, today, listing=None, page=None):
    if kind not in ('gdp', 'pce'): raise ValueError('unsupported BEA kind')
    period = _period(kind, label)
    listing = listing if listing is not None else _read(LIST_URL)
    rows = re.findall(r'<tr\b[^>]*class="[^"]*release-row[^"]*"[^>]*>(.*?)</tr>', listing, re.S | re.I)
    matches = []
    for row in rows:
        a = re.search(r'<a\s+href="(/news/20\d\d/[^"]+)"[^>]*>(.*?)</a>', row, re.S | re.I)
        t = re.search(r'<time\s+datetime="(20\d\d-\d\d-\d\d)T', row, re.I)
        if a and t and t[1] == today.isoformat() and _candidate(kind, _text(a[2]), period):
            matches.append(urljoin(LIST_URL, html.unescape(a[1])))
    if len(matches) != 1: raise ValueError(f'BEA current release match count {len(matches)} for {label} on {today}')
    body = _text(page if page is not None else _read(matches[0]))
    release_date = re.search(r'EMBARGOED UNTIL RELEASE AT .*?\b(?:Monday|Tuesday|Wednesday|Thursday|Friday),\s+([A-Z][a-z]+ \d{1,2}, 20\d\d)', body)
    if not release_date or datetime.strptime(release_date[1], '%B %d, %Y').date() != today:
        raise ValueError('BEA article publication date mismatch')
    if kind == 'gdp':
        m = re.search(r'Real gross domestic product \(GDP\) (increased|decreased) at an annual rate of (\d+(?:\.\d+)?) percent in the (first|second|third|fourth) quarter of (20\d\d)', body, re.I)
        if not m or (int(m[4]), ['first','second','third','fourth'].index(m[3].lower()) + 1) != period:
            raise ValueError('GDP article reference period mismatch')
        sign = '+' if m[1].lower() == 'increased' else '-'
        return f'GDP {sign}{m[2]}% annualized'
    m = re.search(r'From the preceding month, the PCE price index for ([A-Z][a-z]+) (increased|decreased) (\d+(?:\.\d+)?) percent', body, re.I)
    if not m or datetime.strptime(m[1], '%B').month != period[1] or not re.search(r'Personal Income and Outlays,?\s+' + re.escape(m[1]) + r' ' + str(period[0]), body, re.I):
        raise ValueError('PCE article reference period mismatch')
    return f'PCE price {"+" if m[2].lower() == "increased" else "-"}{m[3]}% m/m'
