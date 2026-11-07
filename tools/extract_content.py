import sys, json, re, html, xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse

NS = {
    'wp': 'http://wordpress.org/export/1.2/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
}

CAT_SLUGS = {
    '个人随笔': 'essays',
    '周期性分享': 'periodic-analysis-sharing',
    '我的投资列表': 'my-investment-list',
    '搭建自己的博客': 'blog-building',
    '日分析报告': 'daily-research-report',
    '未分类': 'uncategorized',
    '每日新闻': 'news',
    '金融认知提升': 'financial-mindset',
    '钱包安全性': 'wallet-security',
    '周分析报告': 'weekly-analysis-report',
    '基础书籍推荐': 'recommended-basic-books',
    '技术笔记': 'tech-notes',
}
TAG_SLUGS = {
    '比特币': 'bitcoin',
    '走势分析': 'market-analysis',
    'K线技术': 'kline-technique',
    '金融认知': 'financial-cognition',
    '私钥': 'private-key',
    '比特币私钥': 'bitcoin-private-key',
    '破解器': 'collision-tool',
    '私钥破解': 'private-key-cracking',
    'trx钱包安全': 'trx-wallet-security',
    '加密交易所返佣': 'exchange-rebate',
    'Binance手续费': 'binance-fees',
    'Bitget返佣': 'bitget-rebate',
    'OKX返佣': 'okx-rebate',
    '个人知识付费博客搭建和运营笔记': 'blog-notes',
    '加密交易所返佣、Bitget返佣、Binance手续费、OKX返佣、2026最佳交易所': 'exchange-rebate',
}

def parse_php_sizes(raw):
    """Extract filename->(w,h) from WordPress _wp_attachment_metadata serialized string."""
    out = {}
    if not raw:
        return out
    # primary file
    m = re.search(r's:4:"file";s:\d+:"([^"]+)";s:8:"filesize";i:\d+;', raw)
    if m:
        f = m.group(1)
        mw = re.search(re.escape(f) + r'";s:5:"width";i:(\d+);s:6:"height";i:(\d+);', raw)
        if mw:
            out[f.split('/')[-1]] = (int(mw.group(1)), int(mw.group(2)))
    for m in re.finditer(r's:4:"file";s:\d+:"([^"]+)";s:5:"width";i:(\d+);s:6:"height";i:(\d+);', raw):
        out[m.group(1).split('/')[-1]] = (int(m.group(2)), int(m.group(3)))
    return out

def main(src, outdir):
    tree = ET.parse(src)
    ch = tree.getroot().find('channel')
    site = {
        'title': ch.findtext('title'),
        'link': ch.findtext('link'),
        'description': ch.findtext('description'),
        'language': ch.findtext('language'),
        'base_url': ch.findtext('wp:base_site_url', namespaces=NS),
    }
    cats = []
    for c in ch.findall('wp:category', NS):
        name = c.findtext('wp:cat_name', namespaces=NS)
        cats.append({
            'name': name,
            'slug': CAT_SLUGS.get(name, unquote(c.findtext('wp:category_nicename', namespaces=NS) or '')),
            'description': c.findtext('wp:category_description', namespaces=NS) or '',
        })
    tags = []
    for t in ch.findall('wp:tag', NS):
        name = t.findtext('wp:tag_name', namespaces=NS)
        tags.append({
            'name': name,
            'slug': TAG_SLUGS.get(name, unquote(t.findtext('wp:tag_slug', namespaces=NS) or '')),
            'description': t.findtext('wp:tag_description', namespaces=NS) or '',
        })

    posts, attachments = [], []
    for it in ch.findall('item'):
        ptype = it.findtext('wp:post_type', namespaces=NS)
        content = it.findtext('content:encoded', namespaces=NS) or ''
        rec = {
            'id': int(it.findtext('wp:post_id', namespaces=NS)),
            'type': ptype,
            'title': html.unescape(it.findtext('title') or ''),
            'status': it.findtext('wp:status', namespaces=NS),
            'date': it.findtext('wp:post_date', namespaces=NS),
            'date_gmt': it.findtext('wp:post_date_gmt', namespaces=NS),
            'modified': it.findtext('wp:post_modified', namespaces=NS),
            'modified_gmt': it.findtext('wp:post_modified_gmt', namespaces=NS),
            'slug': unquote(it.findtext('wp:post_name', namespaces=NS) or ''),
            'link': it.findtext('link'),
            'author': it.findtext('dc:creator', namespaces=NS) or '',
            'content': content,
            'excerpt': it.findtext('excerpt:encoded', namespaces=NS) or '',
            'categories': [c.text for c in it.findall('category') if c.get('domain') == 'category'],
            'tags': [c.text for c in it.findall('category') if c.get('domain') == 'post_tag'],
            'parent': it.findtext('wp:post_parent', namespaces=NS),
            'menu_order': it.findtext('wp:menu_order', namespaces=NS),
            'attachment_url': it.findtext('wp:attachment_url', namespaces=NS),
        }
        meta = {}
        for pm in it.findall('wp:postmeta', NS):
            k = pm.findtext('wp:meta_key', namespaces=NS)
            v = pm.findtext('wp:meta_value', namespaces=NS)
            meta[k] = v
        rec['meta'] = {k: v for k, v in meta.items() if k in ('_thumbnail_id', '_wp_attached_file', '_wp_attachment_metadata')}
        if ptype == 'attachment':
            rec['sizes'] = parse_php_sizes(meta.get('_wp_attachment_metadata', ''))
            attachments.append(rec)
        else:
            posts.append(rec)

    import os
    os.makedirs(outdir, exist_ok=True)
    def dump(name, obj):
        with open(os.path.join(outdir, name), 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
    dump('site.json', site)
    dump('categories.json', cats)
    dump('tags.json', tags)
    dump('posts.json', posts)
    dump('attachments.json', attachments)

    # report
    pub = [p for p in posts if p['status'] == 'publish' and p['type'] == 'post']
    drafts = [p for p in posts if p['status'] != 'publish']
    print(f'posts published: {len(pub)}  drafts/other: {len(drafts)}  attachments: {len(attachments)}')
    print('duplicate slugs:', len(pub) - len({p["slug"] for p in pub}))
    print('empty slug published:', [p['id'] for p in pub if not p['slug']])

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
