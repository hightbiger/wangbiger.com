"""HTML cleaning and text helpers for the static rebuild."""
import re
import html
import os
from urllib.parse import urlparse, quote

WP_COMMENT = re.compile(r'<!--\s*/?wp:.*?-->\s*', re.S)
SHORTCODE = re.compile(r'\[/?(?:vip|erphpdown|wppay|hide|login|member|pay|download|crypto_content)\b[^\]]*\]', re.I)
EMPTY_P = re.compile(r'<p(?:\s[^>]*)?>\s*(?:&nbsp;|\u00a0)?\s*</p>\s*', re.I)
IMG_TAG = re.compile(r'<img\b[^>]*>', re.I)
TAG_RE = re.compile(r'<[^>]+>')
SPACE_RE = re.compile(r'[ \t\r\f\v]+')
NL_RE = re.compile(r'\n\s*\n+')

SITE_HOST = 'wangbiger.com'


def strip_tags(s):
    s = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', s, flags=re.S | re.I)
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    s = re.sub(r'</(p|div|li|h[1-6]|tr|blockquote|figure)>', '\n', s, flags=re.I)
    s = TAG_RE.sub('', s)
    s = html.unescape(s).replace('\u00a0', ' ')
    s = SPACE_RE.sub(' ', s)
    s = re.sub(r' *\n *', '\n', s)
    return NL_RE.sub('\n\n', s).strip()


def first_paragraph(content_html):
    m = re.search(r'<p[^>]*>(.*?)</p>', content_html, re.S | re.I)
    if m:
        return strip_tags(m.group(1))
    return strip_tags(content_html)


def make_excerpt(content_html, given='', limit=140):
    text = (given or '').strip()
    if not text:
        m = re.search(r'<h2\b', content_html, re.I)
        head = content_html[:m.start()] if m else content_html
        text = strip_tags(head)
        if len(text) < 30:
            text = strip_tags(content_html)
    text = re.sub(r'^(?:A|答)\s*[：:]\s*', '', text)
    text = re.sub(r'\s+', ' ', strip_tags(text)).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # prefer ending at sentence punctuation
    for mark in ('。', '！', '？', '；'):
        idx = cut.rfind(mark)
        if idx > limit * 0.55:
            return cut[: idx + 1]
    return cut.rstrip('，、,;；:：') + '…'


def reading_time(content_html):
    text = strip_tags(content_html)
    cjk = len(re.findall(r'[\u4e00-\u9fff]', text))
    words = len(re.findall(r'[A-Za-z0-9]+', text))
    minutes = max(1, round(cjk / 400 + words / 200))
    return minutes


def word_count(content_html):
    text = strip_tags(content_html)
    cjk = len(re.findall(r'[\u4e00-\u9fff]', text))
    words = len(re.findall(r'[A-Za-z0-9]+', text))
    return cjk + words


def img_dims(path):
    try:
        with open(path, 'rb') as f:
            head = f.read(32)
            if head[:8] == b'\x89PNG\r\n\x1a\n':
                import struct
                w, h = struct.unpack('>II', head[16:24])
                return w, h
            if head[:6] in (b'GIF87a', b'GIF89a'):
                import struct
                w, h = struct.unpack('<HH', head[6:10])
                return w, h
            if head[:2] == b'\xff\xd8':
                f.seek(2)
                while True:
                    b = f.read(1)
                    while b and b != b'\xff':
                        b = f.read(1)
                    marker = f.read(1)
                    while marker == b'\xff':
                        marker = f.read(1)
                    if not marker:
                        break
                    if marker[0] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        f.read(3)
                        h = int.from_bytes(f.read(2), 'big')
                        w = int.from_bytes(f.read(2), 'big')
                        return w, h
                    seg = int.from_bytes(f.read(2), 'big')
                    f.seek(seg - 2, 1)
            if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
                import struct
                f.seek(12)
                chunk = f.read(16)
                if chunk[:4] == b'VP8 ':
                    w = int.from_bytes(chunk[6:8], 'little') & 0x3fff
                    h = int.from_bytes(chunk[8:10], 'little') & 0x3fff
                    return w, h
                if chunk[:4] == b'VP8L':
                    bits = int.from_bytes(chunk[5:9], 'little')
                    w = (bits & 0x3fff) + 1
                    h = ((bits >> 14) & 0x3fff) + 1
                    return w, h
    except Exception:
        pass
    return None


def _rewrite_link(href):
    pr = urlparse(href)
    if pr.netloc in (SITE_HOST, 'www.' + SITE_HOST):
        path = pr.path or '/'
        return path + (('?' + pr.query) if pr.query else '')
    return href


def _process_img(match, docs_root, fallback_alt=''):
    tag = match.group(0)
    src_m = re.search(r'\bsrc="([^"]+)"', tag, re.I)
    if not src_m:
        return tag
    src = html.unescape(src_m.group(1))
    if src.startswith('data:'):
        return tag
    pr = urlparse(src)
    if pr.netloc in (SITE_HOST, 'www.' + SITE_HOST):
        local = pr.path
    elif pr.scheme in ('http', 'https'):
        local = src  # external, leave
    else:
        local = src if src.startswith('/') else '/' + src

    attrs = {'src': local, 'loading': 'lazy', 'decoding': 'async'}
    alt_m = re.search(r'\balt="([^"]*)"', tag, re.I)
    alt = html.unescape(alt_m.group(1)) if alt_m else ''
    attrs['alt'] = alt.strip() or fallback_alt
    cls_m = re.search(r'\bclass="([^"]*)"', tag, re.I)
    if cls_m:
        keep = [c for c in cls_m.group(1).split() if not c.startswith('wp-image')]
        if keep:
            attrs['class'] = ' '.join(keep)

    # dimensions from explicit attributes, filename, or file header
    w = h = None
    wm = re.search(r'\bwidth="(\d+)"', tag, re.I)
    hm = re.search(r'\bheight="(\d+)"', tag, re.I)
    if wm:
        w = int(wm.group(1))
    if hm:
        h = int(hm.group(1))
    fname = os.path.basename(pr.path if pr.scheme else local)
    fm = re.search(r'-(\d+)x(\d+)\.[A-Za-z]+$', fname)
    if fm:
        w, h = int(fm.group(1)), int(fm.group(2))
    if not (w and h) and local.startswith('/'):
        rel = local.split('/wp-content/uploads/', 1)[-1].lstrip('/')
        fp = os.path.join(docs_root, rel)
        d = img_dims(fp)
        if d:
            w, h = d
    if w and h:
        attrs['width'] = str(w)
        attrs['height'] = str(h)

    order = ['src', 'alt', 'width', 'height', 'loading', 'decoding', 'class']
    parts = [f'{k}="{html.escape(str(attrs[k]), quote=True)}"' for k in order if k in attrs]
    return '<img ' + ' '.join(parts) + '>'


def add_heading_ids(content):
    headings = []
    counter = {'n': 0}

    def repl(m):
        level = m.group(1)
        attrs = m.group(2) or ''
        inner = m.group(3)
        text = strip_tags(inner).strip()
        if not text:
            return m.group(0)
        counter['n'] += 1
        hid = f'section-{counter["n"]}'
        headings.append({'level': int(level), 'id': hid, 'text': text})
        attrs = re.sub(r'\bid="[^"]*"', '', attrs)
        return f'<h{level}{attrs} id="{hid}">{inner}<a class="anchor" href="#{hid}" aria-hidden="true" tabindex="-1"></a></h{level}>'

    return re.sub(r'<h([2-4])([^>]*)>(.*?)</h\1>', repl, content, flags=re.S | re.I), headings


def convert_faq(content):
    """Turn the 'Q1：... / A：...' pattern into semantic FAQ markup (only when present)."""
    items = []

    def repl(m):
        q = strip_tags(m.group(1)).strip()
        a = strip_tags(m.group(2)).strip()
        a = re.sub(r'^A\s*[：:]\s*', '', a).strip()
        if not q or not a:
            return m.group(0)
        items.append((q, a))
        return (f'<div class="faq-item"><h3 class="faq-q">{html.escape(q)}</h3>'
                f'<p class="faq-a">{html.escape(a)}</p></div>')

    pattern = re.compile(r'<strong>\s*Q\d*\s*[：:](.*?)</strong>\s*(?:<br\s*/?>\s*)?A\s*[：:]\s*([^<\n]+)', re.S | re.I)
    new = pattern.sub(repl, content)
    return new, items


PAYWALL_P_MARKERS = (
    '喝杯奶茶查看以下内容',
    '注册blog会员',
    '留下你的邮箱，不错过',
    '付费内容仅为网盘',
)


def _clean_paywall(s):
    """Remove paywall prompts and duplicate VIP copies now that all content is public."""
    if '[wppay]' in s.lower():
        s = re.sub(r'\[vip\].*?\[/vip\]', '', s, flags=re.S | re.I)
    s = re.sub(r'vip专享内容[^<。;；]*[。;；]?', '', s, flags=re.I)
    s = re.sub(r'[！!]?\s*VIP内容与上方付费内容(?:相同|一致)[^<。;；]*[。;；]?', '', s, flags=re.I)
    s = re.sub(r'感谢你为知识付费做的贡献[~～!！。]*\s*', '', s)
    s = re.sub(r'谢谢你的奶茶，', '', s)
    s = re.sub(r'下面请支持付费阅读[。.]?', '', s)
    s = re.sub(r'<strong>\s*下面付费内容[^<]*</strong>\s*', '', s)
    s = re.sub(r'你可以领取下方[^<。]*?进行支付\s*', '', s)
    s = re.sub(r'<strong>\s*（如果出现无法支付.*?</strong>\s*', '', s, flags=re.S)

    def repl(m):
        text = strip_tags(m.group(2)).lower()
        if any(k.lower() in text for k in PAYWALL_P_MARKERS):
            return ''
        return m.group(0)

    return re.sub(r'<p\b([^>]*)>(.*?)</p>', repl, s, flags=re.S | re.I)


def clean_html(content, docs_root, post_title='', post_id=None):
    """WordPress block/HTML content -> clean semantic HTML."""
    s = content or ''
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    s = _clean_paywall(s)
    # embedded base64 images were extracted to files during asset download
    emb_idx = {'n': 0}

    def emb_repl(m):
        emb_idx['n'] += 1
        ext = 'jpg' if m.group(1) == 'jpeg' else m.group(1)
        return f'src="/wp-content/uploads/embedded/post-{post_id}-{emb_idx["n"]}.{ext}"'

    s = re.sub(r'src="data:image/([a-zA-Z]+);base64,[^"]+"', emb_repl, s)
    s = WP_COMMENT.sub('', s)
    s = SHORTCODE.sub('', s)
    s = re.sub(r'<code>\s*</code>', '', s)
    s = re.sub(r'(?:下面|下方)\s*(?:请)?支持付费阅读[。.]?', '', s)
    s = re.sub(r'<h1([^>]*)>(.*?)</h1>', r'<h2\1>\2</h2>', s, flags=re.S | re.I)
    # drop a leading H2 that merely repeats the post title
    m = re.match(r'\s*<h2[^>]*>(.*?)</h2>\s*', s, flags=re.S | re.I)
    if m and post_title and strip_tags(m.group(1)).strip() == post_title.strip():
        s = s[m.end():]
    s = re.sub(r'<img\b[^>]*>', lambda m: _process_img(m, docs_root, post_title), s, flags=re.I)
    # links
    def link_repl(m):
        href = html.unescape(m.group(1))
        new = _rewrite_link(href)
        extra = ' target="_blank" rel="noopener noreferrer"' if urlparse(new).scheme in ('http', 'https') else ''
        return f'<a href="{html.escape(new, quote=True)}"{extra}>{m.group(2)}</a>'
    s = re.sub(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a>', link_repl, s, flags=re.S | re.I)
    s = re.sub(r'<p[^>]*>\s*[=\-—_]{5,}\s*</p>', '<hr>', s, flags=re.I)
    s = EMPTY_P.sub('', s)
    # tables readable on mobile
    s = re.sub(r'(<table\b.*?</table>)', r'<div class="table-scroll">\1</div>', s, flags=re.S | re.I)
    # strip leftover WP-only classes
    s = re.sub(r'\sclass="(?:wp-block-[^"]*|has-[^"]*|is-style-[^"]*)"', '', s)
    s, faq_items = convert_faq(s)
    s, headings = add_heading_ids(s)
    return s.strip(), headings, faq_items


def html_to_markdown(s):
    """Reasonably faithful HTML -> Markdown for llms-full.txt."""
    s = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', s, flags=re.S | re.I)

    def table_repl(m):
        t = m.group(0)
        rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', t, re.S | re.I)
        out = []
        for i, row in enumerate(rows):
            cells = re.findall(r'<t[hd]\b[^>]*>(.*?)</t[hd]>', row, re.S | re.I)
            cells = [strip_tags(c).replace('|', '\\|').replace('\n', ' ').strip() for c in cells]
            if not cells:
                continue
            out.append('| ' + ' | '.join(cells) + ' |')
            if i == 0:
                out.append('| ' + ' | '.join(['---'] * len(cells)) + ' |')
        return '\n' + '\n'.join(out) + '\n'

    s = re.sub(r'<table\b.*?</table>', table_repl, s, flags=re.S | re.I)
    s = re.sub(r'<h([1-6])[^>]*>(.*?)</h\1>', lambda m: '\n' + '#' * int(m.group(1)) + ' ' + strip_tags(m.group(2)) + '\n', s, flags=re.S | re.I)
    s = re.sub(r'<li[^>]*>(.*?)</li>', lambda m: '\n- ' + strip_tags(m.group(1)) + '\n', s, flags=re.S | re.I)
    s = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', lambda m: '\n> ' + strip_tags(m.group(1)).replace('\n', '\n> ') + '\n', s, flags=re.S | re.I)
    s = re.sub(r'<pre[^>]*>(.*?)</pre>', lambda m: '\n```\n' + strip_tags(m.group(1)) + '\n```\n', s, flags=re.S | re.I)
    s = re.sub(r'<img\b[^>]*alt="([^"]*)"[^>]*src="([^"]+)"[^>]*>', r'![\1](\2)', s, flags=re.I)
    s = re.sub(r'<img\b[^>]*src="([^"]+)"[^>]*>', r'![](\1)', s, flags=re.I)
    s = re.sub(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', lambda m: '[' + strip_tags(m.group(2)) + '](' + m.group(1) + ')', s, flags=re.S | re.I)
    s = re.sub(r'</?(strong|b)>', '**', s, flags=re.I)
    s = re.sub(r'</?(em|i)>', '*', s, flags=re.I)
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    s = re.sub(r'</p>', '\n\n', s, flags=re.I)
    s = re.sub(r'</div>', '\n', s, flags=re.I)
    s = re.sub(r'<hr[^>]*>', '\n---\n', s, flags=re.I)
    s = TAG_RE.sub('', s)
    s = html.unescape(s).replace('\u00a0', ' ')
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    lines = [ln.strip() for ln in s.split('\n')]
    out = []
    for ln in lines:
        if ln or (out and out[-1]):
            out.append(ln)
    return '\n'.join(out).strip()
