import re, os, glob

SITE = r"D:\AI Projects\MarketsOnDeck\site"
html_files = glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)

broken = []
checked = 0
for f in html_files:
    with open(f, encoding="utf-8") as fh:
        content = fh.read()
    for m in re.finditer(r'href="(/[^"#]*)(#[^"]*)?"', content):
        href = m.group(1)
        checked += 1
        target = os.path.join(SITE, href.lstrip("/"))
        if not os.path.isfile(target):
            broken.append((os.path.relpath(f, SITE), href))
    for m in re.finditer(r'src="(/[^"]*)"', content):
        src = m.group(1)
        checked += 1
        target = os.path.join(SITE, src.lstrip("/"))
        if not os.path.isfile(target):
            broken.append((os.path.relpath(f, SITE), src))

print(f"Checked {checked} internal links across {len(html_files)} files.")
if broken:
    print(f"BROKEN LINKS ({len(broken)}):")
    for source, href in broken:
        print(f"  {source}  ->  {href}")
else:
    print("No broken internal links found.")
