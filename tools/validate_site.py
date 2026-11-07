import sys, os, re, json, html
from pathlib import Path
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET

docs = Path(sys.argv[1])
errors, warnings = [], []
html_files = list(docs.rglob('*.html'))
print('html files:', len(html_files))

def resolve(path):
    path = unquote(path)
    p = path.lstrip('/')
    target = docs / p
    if target.is_dir():
        target = target / 'index.html'
    if not target.exists() and not p.endswith('/'):
        target2 = docs / p / 'index.html'
        if target2.exists():
            target = target2
    return target.exists()

ld_count = 0
for fp in html_files:
    s = fp.read_text(encoding='utf-8')
    rel = fp.relative_to(docs)
    # headings
    h1s = re.findall(r'<h1\b[^>]*>(.*?)</h1>', s, re.S | re.I)
    if len(h1s) > 1:
        errors.append(f'{rel}: {len(h1s)} <h1> tags')
    # json-ld
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        ld_count += 1
        try:
            json.loads(m.group(1))
        except Exception as e:
            errors.append(f'{rel}: bad JSON-LD: {e}')
    # canonical
    if 'rel="canonical"' not in s and fp.name != '404.html':
        warnings.append(f'{rel}: no canonical')
    # shortcodes / wp comments
    if re.search(r'\[(?:/?)(?:vip|erphpdown|hide|crypto_content)\]', s):
        errors.append(f'{rel}: shortcode leftover')
    if '<!-- wp:' in s:
        warnings.append(f'{rel}: wp block comment leftover')
    # links and images
    for m in re.finditer(r'(?:href|src)="([^"]+)"', s):
        u = html.unescape(m.group(1))
        if u.startswith(('#', 'mailto:', 'tel:', 'data:', 'javascript:')):
            continue
        pr = urlparse(u)
        if pr.scheme in ('http', 'https'):
            continue
        if u.startswith('//'):
            continue
        if u.startswith('/'):
            if not resolve(pr.path):
                errors.append(f'{rel}: broken link {u[:120]}')
        else:
            target = (fp.parent / unquote(pr.path))
            if pr.path and not target.exists() and not (target.is_dir() and (target / 'index.html').exists()):
                # relative links are rare
                warnings.append(f'{rel}: relative link {u[:80]}')
    # img alt
    for m in re.finditer(r'<img\b[^>]*>', s):
        if 'alt=' not in m.group(0):
            errors.append(f'{rel}: img without alt: {m.group(0)[:80]}')

for xmlf in ('sitemap.xml', 'feed.xml'):
    try:
        ET.parse(docs / xmlf)
    except Exception as e:
        errors.append(f'{xmlf}: XML error {e}')

# sitemap URLs resolve?
try:
    tree = ET.parse(docs / 'sitemap.xml')
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    locs = [e.text for e in tree.getroot().findall('.//s:loc', ns)]
    for loc in locs:
        path = urlparse(loc).path
        if not resolve(path):
            errors.append(f'sitemap: missing page {loc}')
    print('sitemap urls:', len(locs))
except Exception as e:
    errors.append(f'sitemap parse: {e}')

# search index
try:
    idx = json.loads((docs / 'search-index.json').read_text(encoding='utf-8'))
    for it in idx:
        if not resolve(it['url']):
            errors.append(f'search index: bad url {it["url"]}')
    print('search index entries:', len(idx))
except Exception as e:
    errors.append(f'search index: {e}')

print('json-ld blocks:', ld_count)
print('errors:', len(errors))
for e in errors[:40]:
    print('  ERROR', e)
print('warnings:', len(warnings))
for w in warnings[:20]:
    print('  WARN', w)
