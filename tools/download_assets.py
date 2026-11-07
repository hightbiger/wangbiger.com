import sys, os, re, json, base64, time, mimetypes
from urllib.parse import quote, unquote, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request

PROXY = 'https://images.weserv.nl/?url='

def collect(posts):
    urls = {}
    for p in posts:
        if p['status'] != 'publish' or p['type'] not in ('post', 'page'):
            continue
        for m in re.finditer(r'<img[^>]+src="([^"]+)"', p['content']):
            u = m.group(1)
            if u.startswith('data:'):
                continue
            urls.setdefault(u, []).append(p['id'])
    return urls

def to_rel_path(url):
    pr = urlparse(url)
    path = pr.path if pr.scheme else url
    path = unquote(path)
    if '/wp-content/uploads/' in path:
        return path.split('/wp-content/uploads/', 1)[1]
    return 'misc/' + path.strip('/')

def fetch(url, dest, retries=4):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return 'cached', os.path.getsize(dest)
    rel = url.split('/wp-content/uploads/', 1)[-1]
    proxied = PROXY + quote('wangbiger.com/wp-content/uploads/' + rel, safe='')
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(proxied, headers={'User-Agent': 'Mozilla/5.0 (compatible; site-rebuild/1.0)'})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                ctype = r.headers.get('Content-Type', '')
            if len(data) < 100 or 'image' not in ctype:
                raise ValueError(f'bad response {ctype} {len(data)}')
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'wb') as f:
                f.write(data)
            return 'ok', len(data)
        except Exception as e:
            last = str(e)
            time.sleep(1.5 * (i + 1))
    return 'fail: ' + str(last), 0

def main(posts_json, outroot):
    posts = json.load(open(posts_json, encoding='utf-8'))
    urls = collect(posts)
    print(f'unique images in published content: {len(urls)}')
    tasks = []
    for u in urls:
        rel = to_rel_path(u)
        dest = os.path.join(outroot, rel)
        tasks.append((u, dest))
    results = {}
    fails = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(fetch, u, d): (u, d) for u, d in tasks}
        for n, fut in enumerate(as_completed(futs), 1):
            u, d = futs[fut]
            status, size = fut.result()
            results[u] = {'status': status, 'size': size, 'dest': d}
            if status.startswith('fail'):
                fails.append((u, status))
            print(f'[{n}/{len(tasks)}] {status[:60]} {size:>9} {unquote(u)[-70:]}')
    # fallback: strip -WxH suffix and use original
    for u, status in list(fails):
        if re.search(r'-\d+x\d+(\.[a-zA-Z]+)$', u):
            orig = re.sub(r'-\d+x\d+(\.[a-zA-Z]+)$', r'\1', u)
            if orig in urls:
                src_dest = os.path.join(outroot, to_rel_path(orig))
                dst_dest = os.path.join(outroot, to_rel_path(u))
                if os.path.exists(src_dest):
                    os.makedirs(os.path.dirname(dst_dest), exist_ok=True)
                    open(dst_dest, 'wb').write(open(src_dest, 'rb').read())
                    results[u] = {'status': 'fallback-original', 'size': os.path.getsize(dst_dest), 'dest': dst_dest}
                    fails.remove((u, status))
    # embedded base64 images
    emb = []
    for p in posts:
        if p['status'] != 'publish':
            continue
        for i, m in enumerate(re.finditer(r'src="data:image/([a-zA-Z]+);base64,([^"]+)"', p['content'])):
            data = base64.b64decode(m.group(2))
            ext = 'jpg' if m.group(1) == 'jpeg' else m.group(1)
            rel = f'embedded/post-{p["id"]}-{i+1}.{ext}'
            dest = os.path.join(outroot, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, 'wb').write(data)
            emb.append({'source_url': f'/wp-content/uploads/{rel}', 'post': p['id'], 'size': len(data)})
    manifest = {'images': results, 'embedded': emb, 'failed': [u for u, _ in fails]}
    manifest_path = os.path.join(os.path.dirname(os.path.abspath(posts_json)), 'asset-manifest.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print('failed:', len(fails))
    for u, s in fails:
        print('  FAIL', unquote(u), '->', s[:100])

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
