#!/usr/bin/env python3
"""Static site generator for the rebuilt hightbiger blog.

Source data lives in ../content (sanitized WordPress WXR extract).
Output is written to ../docs, which is what GitHub Pages serves.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build'
CONTENT = ROOT / 'content'
DOCS = ROOT / 'docs'
UPLOADS_SRC = BUILD / 'uploads'
STATIC = BUILD / 'static'

SITE_URL = 'https://wangbiger.com'
SITE_NAME = 'hightbiger'
SITE_TITLE = 'hightbiger 币圈博客'
SITE_DESC = '寻找和分享适合自己的个人金融理财和价值变现解决方案'
SITE_DESC_LONG = ('记录比特币周期走势分析、交易所手续费与返佣对比、钱包安全实践，'
                  '以及个人的投资与金融认知笔记。')
AUTHOR_NAME = 'hightbiger'
AUTHOR_BIO = ('2011 年开始创业，2015 年开始系统学习 K 线与金融知识，2017 年进入币圈，'
              '经历多轮牛熊周期。持续记录比特币周期走势、交易成本优化与加密资产安全。')
AUTHOR_SHORT = '个人投资者与内容创作者'
CST = timezone(timedelta(hours=8))
BUILD_DATE = datetime(2026, 11, 7, tzinfo=CST)
CSS_VER = '20261107'
DISCLAIMER = ('风险提示：本站内容为个人研究、记录与观点分享，不构成任何投资建议。'
              '加密货币价格波动剧烈，交易与投资风险极高，请独立判断并自行承担风险。')

SOCIAL = [
    ('Twitter / X', 'https://twitter.com/hightbiger'),
    ('YouTube', 'https://www.youtube.com/channel/UCS6f79bKHQoYjD0sz4nOMog/'),
    ('Telegram', 'https://t.me/joinchat/HG8JJBd_fMJDBwQolSs_Kg'),
    ('Discord', 'https://discord.gg/Cz6pxttuBQ'),
    ('Linktree', 'https://linktr.ee/hightbiger'),
]

CAT_ORDER = [
    'periodic-analysis-sharing', 'exchange-and-tools', 'financial-mindset', 'wallet-security',
    'tech-notes', 'my-investment-list', 'news', 'recommended-basic-books',
    'essays', 'blog-building', 'weekly-analysis-report', 'daily-research-report',
    'uncategorized',
]
EXTRA_CATEGORIES = [{
    'name': '交易所与工具',
    'slug': 'exchange-and-tools',
    'description': '交易所手续费与返佣、出入金工具、预测市场等实用主题。',
}]
CATEGORY_OVERRIDES = {
    291: ['技术笔记'],
    352: ['周分析报告'],
    367: ['金融认知提升'],
    379: ['交易所与工具'],
    388: ['技术笔记'],
    401: ['技术笔记'],
    419: ['交易所与工具'],
    447: ['交易所与工具'],
    452: ['交易所与工具'],
}
CAT_FALLBACK_DESC = {
    '个人随笔': '个人经历、阶段复盘与日常想法记录。',
    '搭建自己的博客': '个人博客与内容平台的搭建、运营及工具经验。',
    '钱包安全性': '加密钱包的安全设置、私钥管理与多签实践。',
    '技术笔记': '交易工具、数据分析与技术原理的学习笔记。',
    '每日新闻': '币圈每日热点与市场信息摘录。',
    '交易所与工具': '交易所手续费与返佣、出入金工具、预测市场等实用主题。',
    '周期性分享': '周期性走势分析报告，包括月报、周报与日报。',
    '我的投资列表': '个人投资币种清单与仓位记录，仅供交流参考。',
    '金融认知提升': '金融认知、复利与个人理财相关的思考。',
    '基础书籍推荐': '有学习价值的金融与交易书籍笔记。',
    '周分析报告': '周线级别的行情观察与操作思路。',
    '日分析报告': '当日出现明显走势或想法时的记录。',
    '未分类': '尚未归档的其他记录。',
}
SLUG_OVERRIDES = {
    7: 'weekly-opportunity-2023-08-15',
    75: 'crypto-cycle-history',
    133: 'bitcoin-historical-max-drawdown',
    173: 'compound-interest',
    188: 'japanese-candlestick-basics',
    235: 'crypto-news-2023-08-29',
    236: 'trx-multisig-wallet-guide',
    247: 'crypto-news-2023-08-31',
    262: 'my-investment-list',
    279: '2023-09-03-bitcoin-trend-analysis',
    291: 'bitcoin-private-key-bruteforce',
    303: '2023-09-10-bitcoin-trend-analysis',
    310: '2023-09-17-bitcoin-trend-analysis',
    321: '2023-09-24-bitcoin-trend-analysis',
    329: '2023-10-27-bitcoin-trend-analysis',
    343: '2024-01-24-bitcoin-trend-analysis',
    352: '2024-01-24-bitcoin-cycle-indicator',
    367: 'bull-market-stable-yield',
    373: 'twitter-algorithm-10-takeaways',
    379: 'bybit-u-card-guide',
    401: 'trx-private-key-collision-tool',
    419: '2026-exchange-rebate-comparison',
    447: 'world-cup-prediction-market',
}
# 428: paywall test post; 221: duplicate copy of post 7 (full text kept in 7).
EXCLUDE_IDS = {221, 428}
# legacy IDs / drafts that should not exist as pages but still need a target
ID_REDIRECTS = {
    221: '/posts/weekly-opportunity-2023-08-15/',
    249: '/posts/my-investment-list/',   # draft page, duplicate of post 262
    428: '/',
}
TITLE_OVERRIDES = {
    1: '关于 hightbiger',
    452: '工具箱：常用链接与交易工具',
}
EXCERPT_OVERRIDES = {
    7: '2023 年 8 月 15 日周线级别操作机会：比特币中轨支撑反弹下的多单止损 28708、止盈 29879 思路，以及强势币种选择与低倍空单的复盘。',
    419: '2026 年主流加密交易所手续费与返佣实测对比，涵盖 Binance、OKX、Bitget、Huobi 的现货与合约费率、注册优惠和选择建议。',
}

TAG_CANON = {
    'exchange-rebate': ('加密交易所返佣', '交易所手续费、返佣与注册优惠相关文章。'),
}
TAG_FALLBACK_DESC = {
    'bitcoin': '与比特币价格、周期和长期逻辑相关的文章。',
    'market-analysis': '行情走势与关键位置的观察分析。',
    'kline-technique': 'K 线形态与技术分析基础。',
    'financial-cognition': '金融认知与个人理财思路。',
    'private-key': '私钥、地址与资产自托管相关话题。',
    'bitcoin-private-key': '比特币私钥原理与安全相关文章。',
    'private-key-cracking': '私钥碰撞、暴力枚举的原理与风险讨论。',
    'collision-tool': '私钥碰撞工具的原理说明与技术记录。',
    'trx-wallet-security': 'TRX 钱包多签与安全设置。',
    'exchange-rebate': TAG_CANON['exchange-rebate'][1],
    'binance-fees': '币安手续费与返佣相关内容。',
    'bitget-rebate': 'Bitget 手续费与返佣相关内容。',
    'okx-rebate': 'OKX 手续费与返佣相关内容。',
    'blog-notes': '个人知识付费博客的搭建与运营笔记。',
}

esc = html.escape


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def load_json(name):
    with open(CONTENT / name, encoding='utf-8') as f:
        return json.load(f)


def parse_dt(s, fallback=None):
    if not s:
        return fallback
    try:
        return datetime.strptime(s.strip(), '%Y-%m-%d %H:%M:%S').replace(tzinfo=CST)
    except ValueError:
        return fallback


def abs_url(path):
    return SITE_URL + quote(path, safe='/')


def page_file(path):
    p = DOCS / path.strip('/')
    return p / 'index.html'


def write(path, text):
    fp = page_file(path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(text, encoding='utf-8')


def write_raw(rel, text):
    fp = DOCS / rel
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(text, encoding='utf-8')


def date_display(dt):
    return f'{dt.year}年{dt.month}月{dt.day}日'


def jsonld(graph):
    data = {'@context': 'https://schema.org', '@graph': graph}
    return json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def cdata(s):
    return '<![CDATA[' + (s or '').replace(']]>', ']]]]><![CDATA[>') + ']]>'


def xml_escape(s):
    return esc(s or '', quote=True)


def first_image(html_text):
    m = re.search(r'<img[^>]+src="([^"]+)"', html_text or '')
    if not m:
        return None
    src = html.unescape(m.group(1))
    if src.startswith('http'):
        return src
    return SITE_URL + quote(src, safe='/')


# --------------------------------------------------------------------------
# content model
# --------------------------------------------------------------------------
site = load_json('site.json')
categories = load_json('categories.json')
tags = load_json('tags.json')
posts_raw = load_json('posts.json')

for extra in EXTRA_CATEGORIES:
    if not any(c['slug'] == extra['slug'] for c in categories):
        categories.append(extra)

cat_by_name = {c['name']: c for c in categories}
cat_by_slug = {c['slug']: c for c in categories}
tag_by_name = {}
for t in tags:
    tag_by_name.setdefault(t['name'], t)


def special_path(pid, slug, ptype):
    if pid == 1:
        return '/about/'
    if pid == 452:
        return '/tools/'
    if ptype == 'page' and slug == 'privacy-policy':
        return '/privacy-policy/'
    return None


OLD_TO_NEW = {}
for _p in posts_raw:
    if not _p.get('link'):
        continue
    _old = urlparse(_p['link']).path
    _new = ID_REDIRECTS.get(_p['id'])
    if not _new:
        if _p['status'] != 'publish' or _p['id'] in EXCLUDE_IDS:
            continue
        _new = special_path(_p['id'], _p['slug'], _p['type']) or \
            f"/posts/{SLUG_OVERRIDES.get(_p['id'], _p['slug'])}/"
    if _old and _old != '/':
        OLD_TO_NEW[_old] = _new
        OLD_TO_NEW[unquote(_old)] = _new


def remap_internal_links(s):
    def repl(m):
        href = html.unescape(m.group(1))
        new = OLD_TO_NEW.get(href) or OLD_TO_NEW.get(unquote(href))
        return f'href="{esc(new, quote=True)}"' if new else m.group(0)
    return re.sub(r'href="([^"]+)"', repl, s)


def build_post(p):
    dt = parse_dt(p['date'], BUILD_DATE)
    mod = parse_dt(p['modified'], dt) or dt
    title = TITLE_OVERRIDES.get(p['id'], p['title'])
    cleaned, headings, faq = render.clean_html(
        p['content'], str(UPLOADS_SRC), post_title=p['title'], post_id=p['id'])
    cleaned = remap_internal_links(cleaned)
    if p['id'] == 1:
        cleaned = cleaned.replace('注册这个blog留下你的邮箱', '收藏这个博客')
    given = (p.get('excerpt') or '').strip()
    if given == p['title']:
        given = ''
    summary = EXCERPT_OVERRIDES.get(p['id']) or render.make_excerpt(cleaned, given)
    cat_names = CATEGORY_OVERRIDES.get(p['id'], p['categories'])
    cat_list, seen = [], set()
    for name in cat_names:
        c = cat_by_name.get(name)
        if not c or c['slug'] in seen:
            continue
        seen.add(c['slug'])
        cat_list.append({'name': c['name'], 'slug': c['slug']})
    primary = next((c for c in cat_list if c['slug'] != 'uncategorized'), cat_list[0] if cat_list else None)
    tag_list, seen = [], set()
    for name in p['tags']:
        t = tag_by_name.get(name)
        if not t:
            continue
        slug = t['slug']
        if slug in seen:
            continue
        seen.add(slug)
        disp = TAG_CANON.get(slug, (t['name'], ''))[0]
        tag_list.append({'name': disp, 'slug': slug})
    special = special_path(p['id'], p['slug'], p['type'])
    slug = SLUG_OVERRIDES.get(p['id'], p['slug'])
    path = special or f"/posts/{slug}/"
    return {
        'id': p['id'],
        'type': p['type'],
        'title': title,
        'slug': slug,
        'path': path,
        'url': abs_url(path),
        'date': dt,
        'modified': mod,
        'date_iso': dt.isoformat(),
        'modified_iso': mod.isoformat(),
        'date_display': date_display(dt),
        'author': AUTHOR_NAME,
        'summary': summary,
        'html': cleaned,
        'headings': headings,
        'faq': faq,
        'words': render.word_count(cleaned),
        'minutes': render.reading_time(cleaned),
        'categories': cat_list,
        'primary_category': primary,
        'tags': tag_list,
        'image': first_image(cleaned),
        'old_path': urlparse(p['link']).path if p.get('link') else None,
        'is_page': p['type'] == 'page',
    }


published = []
for p in posts_raw:
    if p['status'] != 'publish':
        continue
    if p['type'] not in ('post', 'page'):
        continue
    if not p['slug'] or p['id'] in EXCLUDE_IDS:
        continue
    published.append(build_post(p))

privacy_raw = next((p for p in published if p['path'] == '/privacy-policy/'), None)
articles = [p for p in published if p['path'].startswith('/posts/')]
articles.sort(key=lambda x: x['date'], reverse=True)
all_pages = sorted(published, key=lambda x: x['date'], reverse=True)
by_id = {p['id']: p for p in published}

# category aggregation
cat_posts = {}
for p in articles:
    for c in p['categories']:
        cat_posts.setdefault(c['slug'], []).append(p)

active_cats = []
for slug in CAT_ORDER:
    c = cat_by_slug.get(slug)
    if not c or not cat_posts.get(slug):
        continue
    active_cats.append({
        'name': c['name'],
        'slug': slug,
        'path': f'/categories/{slug}/',
        'description': c['description'] or CAT_FALLBACK_DESC.get(c['name'], f'收录与「{c["name"]}」相关的文章。'),
        'posts': cat_posts[slug],
    })
# any categories not in the fixed order
for slug, plist in cat_posts.items():
    if slug in {c['slug'] for c in active_cats}:
        continue
    c = cat_by_slug.get(slug, {'name': slug, 'slug': slug, 'description': ''})
    active_cats.append({
        'name': c['name'], 'slug': slug, 'path': f'/categories/{slug}/',
        'description': c['description'] or CAT_FALLBACK_DESC.get(c['name'], f'收录与「{c["name"]}」相关的文章。'),
        'posts': plist,
    })

# tag aggregation
tag_posts = {}
tag_meta = {}
for p in articles:
    for t in p['tags']:
        tag_posts.setdefault(t['slug'], []).append(p)
        tag_meta.setdefault(t['slug'], t['name'])
active_tags = []
for slug, plist in tag_posts.items():
    name = TAG_CANON.get(slug, (tag_meta[slug], ''))[0]
    desc = TAG_CANON.get(slug, ('', ''))[1] or TAG_FALLBACK_DESC.get(slug, f'与「{name}」相关的文章。')
    plist.sort(key=lambda x: x['date'], reverse=True)
    active_tags.append({'name': name, 'slug': slug, 'path': f'/tags/{slug}/', 'description': desc, 'posts': plist})
active_tags.sort(key=lambda x: (-len(x['posts']), x['name']))

latest_date = max((p['modified'] for p in published), default=BUILD_DATE)


def posts_by_date_desc(plist):
    return sorted(plist, key=lambda x: (x['date'], x['id']), reverse=True)


# --------------------------------------------------------------------------
# shared chrome
# --------------------------------------------------------------------------
def nav_html(active):
    items = [
        ('首页', '/', 'home'),
        ('文章', '/archive/', 'archive'),
        ('分类', '/categories/', 'categories'),
        ('工具箱', '/tools/', 'tools'),
        ('关于', '/about/', 'about'),
    ]
    out = []
    for label, path, key in items:
        cur = ' aria-current="page"' if key == active else ''
        out.append(f'<a href="{path}"{cur}>{label}</a>')
    return ''.join(out)


def footer_html():
    cat_links = ''.join(
        f'<li><a href="{c["path"]}">{esc(c["name"])} <span class="n">{len(c["posts"])}</span></a></li>'
        for c in active_cats[:4]
    )
    social = ''.join(
        f'<li><a href="{url}" target="_blank" rel="noopener noreferrer">{name}</a></li>'
        for name, url in SOCIAL
    )
    return f'''
<footer class="site-footer">
  <div class="wrap">
    <div class="footer-main">
      <div class="footer-brand">
        <b>hightbiger</b>
        <p>{esc(SITE_DESC)}。{esc(SITE_DESC_LONG)}</p>
      </div>
      <div class="footer-col">
        <h3>浏览</h3>
        <ul>
          <li><a href="/">首页</a></li>
          <li><a href="/archive/">文章归档</a></li>
          <li><a href="/categories/">全部分类</a></li>
          <li><a href="/tags/">全部标签</a></li>
          <li><a href="/search/">搜索</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h3>分类</h3>
        <ul>{cat_links}</ul>
      </div>
      <div class="footer-col">
        <h3>联系与订阅</h3>
        <ul>{social}<li><a href="/feed.xml">RSS 订阅</a></li></ul>
      </div>
    </div>
    <p class="disclaimer">{esc(DISCLAIMER)}</p>
    <div class="footer-bottom">
      <span>© 2023–2026 hightbiger · 内容版权归作者所有</span>
      <span>由 WordPress 备份静态重建 · GitHub Pages 托管</span>
    </div>
  </div>
</footer>'''


def head_common(title, desc, canonical, og_type='website', og_image=None, jsonld_graph=None,
                extra_head='', noindex=False, active=''):
    robots = ('noindex, follow' if noindex else
              'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1')
    og_img = ''
    if og_image:
        og_img = (f'\n<meta property="og:image" content="{esc(og_image, quote=True)}">'
                  f'\n<meta name="twitter:image" content="{esc(og_image, quote=True)}">')
    ld = ''
    if jsonld_graph:
        ld = f'\n<script type="application/ld+json">{jsonld(jsonld_graph)}</script>'
    return f'''<!doctype html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc, quote=True)}">
<link rel="canonical" href="{esc(canonical, quote=True)}">
<meta name="robots" content="{robots}">
<meta name="author" content="hightbiger">
<meta name="theme-color" content="#121110" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f7f5f0" media="(prefers-color-scheme: light)">
<meta property="og:site_name" content="{esc(SITE_TITLE)}">
<meta property="og:locale" content="zh_CN">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title, quote=True)}">
<meta property="og:description" content="{esc(desc, quote=True)}">
<meta property="og:url" content="{esc(canonical, quote=True)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@hightbiger">
<meta name="twitter:creator" content="@hightbiger">
<meta name="twitter:title" content="{esc(title, quote=True)}">
<meta name="twitter:description" content="{esc(desc, quote=True)}">{og_img}
<link rel="alternate" hreflang="zh-CN" href="{esc(canonical, quote=True)}">
<link rel="alternate" hreflang="x-default" href="{esc(canonical, quote=True)}">
<link rel="alternate" type="application/rss+xml" title="{esc(SITE_TITLE)}" href="/feed.xml">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="stylesheet" href="/assets/style.css?v={CSS_VER}">
{extra_head}{ld}
<script>(function(){{try{{var t=localStorage.getItem('theme');if(t==='dark'||(!t&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches)){{document.documentElement.setAttribute('data-theme','dark');}}}}catch(e){{}}}})();</script>
</head>
<body>
<a class="skip" href="#main">跳到正文</a>
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="/" aria-label="hightbiger 币圈博客首页">
      <span class="brand-mark">hightbiger</span>
      <span class="brand-sub">币圈博客</span>
    </a>
    <nav class="nav" id="site-nav" aria-label="主导航">{nav_html(active)}</nav>
    <div class="header-tools">
      <a class="icon-btn" href="/search/" aria-label="搜索文章" title="搜索文章">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/></svg>
      </a>
      <button class="icon-btn" type="button" data-theme-toggle aria-label="切换深色模式"></button>
      <button class="icon-btn nav-toggle" type="button" data-nav-toggle aria-expanded="false" aria-controls="site-nav" aria-label="打开导航">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
      </button>
    </div>
  </div>
</header>'''


def page_document(title, desc, canonical, body, active='', og_type='website', og_image=None,
                  jsonld_graph=None, extra_head='', noindex=False):
    return (head_common(title, desc, canonical, og_type, og_image, jsonld_graph, extra_head, noindex, active)
            + '\n<main id="main">' + body + '</main>\n' + footer_html() +
            f'\n<script src="/assets/app.js?v={CSS_VER}" defer></script>\n</body>\n</html>\n')


def website_node():
    return {
        '@type': 'WebSite',
        '@id': SITE_URL + '/#website',
        'url': SITE_URL + '/',
        'name': SITE_TITLE,
        'alternateName': ['hightbiger 博客', 'hightbiger'],
        'description': SITE_DESC,
        'inLanguage': 'zh-CN',
        'publisher': {'@id': SITE_URL + '/#organization'},
    }


def org_node():
    return {
        '@type': 'Organization',
        '@id': SITE_URL + '/#organization',
        'name': SITE_TITLE,
        'url': SITE_URL + '/',
        'description': SITE_DESC,
        'logo': {'@type': 'ImageObject', 'url': SITE_URL + '/assets/favicon.svg'},
    }


def person_node():
    return {
        '@type': 'Person',
        '@id': SITE_URL + '/#person',
        'name': AUTHOR_NAME,
        'url': abs_url('/about/'),
        'description': AUTHOR_BIO,
        'jobTitle': AUTHOR_SHORT,
        'knowsAbout': ['比特币', '加密货币周期', 'K线技术', '交易所手续费与返佣', '加密钱包安全', '个人理财'],
        'sameAs': [u for _, u in SOCIAL],
    }


def breadcrumb_node(items):
    return {
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': i + 1, 'name': name, 'item': abs_url(path)}
            for i, (name, path) in enumerate(items)
        ],
    }


def breadcrumb_html(items):
    lis = []
    for i, (name, path) in enumerate(items):
        if i == len(items) - 1:
            lis.append(f'<li aria-current="page">{esc(name)}</li>')
        else:
            lis.append(f'<li><a href="{path}">{esc(name)}</a></li>')
    return f'<nav class="breadcrumb" aria-label="面包屑"><div class="wrap"><ol>{"".join(lis)}</ol></div></nav>'


def post_card(p, show_author=False):
    cat = p['primary_category']
    cat_html = f'<a class="chip" href="/categories/{cat["slug"]}/">{esc(cat["name"])}</a>' if cat else ''
    foot = esc(p['author']) if show_author else f'{p["minutes"]} 分钟阅读'
    return f'''<article class="post-card">
  <div class="card-meta">{cat_html}<time datetime="{p['date_iso'][:10]}">{p['date_display']}</time></div>
  <h3><a href="{p['path']}">{esc(p['title'])}</a></h3>
  <p class="card-summary">{esc(p['summary'])}</p>
  <div class="card-foot"><span>{foot}</span><span class="read-more">阅读 →</span></div>
</article>'''


def category_card(c):
    return f'''<a class="category-card" href="{c['path']}">
  <b>{esc(c['name'])}</b>
  <span>{esc(c['description'])}</span>
  <em>{len(c['posts'])} 篇文章</em>
</a>'''


def author_card(name=AUTHOR_NAME):
    links = ' · '.join(f'<a href="{u}" target="_blank" rel="noopener noreferrer">{esc(n)}</a>' for n, u in SOCIAL[:3])
    if name != AUTHOR_NAME:
        return f'''<div class="author-card">
  <div class="avatar" aria-hidden="true">{esc(name[:1])}</div>
  <div>
    <b>{esc(name)}</b>
    <p>本站文章作者。</p>
    <div class="links"><a href="/about/">关于本站 →</a></div>
  </div>
</div>'''
    return f'''<div class="author-card">
  <div class="avatar" aria-hidden="true">h</div>
  <div>
    <b>hightbiger</b>
    <p>{esc(AUTHOR_BIO)}</p>
    <div class="links">{links} · <a href="/about/">关于作者 →</a></div>
  </div>
</div>'''


def risk_note():
    return f'<div class="notice" style="margin-top:22px">{esc(DISCLAIMER)}</div>'


def toc_html(headings):
    items = [h for h in headings if h['level'] in (2, 3)]
    if len(items) < 3:
        return ''
    lis = ''.join(
        f'<li class="lvl-{h["level"]}"><a href="#{h["id"]}">{esc(h["text"])}</a></li>' for h in items)
    return f'<nav class="toc" aria-label="本文目录"><p class="toc-title">本文目录</p><ol>{lis}</ol></nav>'


def related_posts(p, limit=3):
    scores = []
    p_tags = {t['slug'] for t in p['tags']}
    p_cat = p['primary_category']['slug'] if p['primary_category'] else None
    for q in articles:
        if q['id'] == p['id']:
            continue
        score = len(p_tags & {t['slug'] for t in q['tags']}) * 2
        if p_cat and q['primary_category'] and q['primary_category']['slug'] == p_cat:
            score += 2
        if score:
            scores.append((score, q['date'], q))
    scores.sort(key=lambda x: (x[0], x[1]), reverse=True)
    picks = [q for _, _, q in scores[:limit]]
    if len(picks) < limit:
        for q in articles:
            if q['id'] != p['id'] and q not in picks:
                picks.append(q)
            if len(picks) >= limit:
                break
    return picks[:limit]


# --------------------------------------------------------------------------
# article page
# --------------------------------------------------------------------------
def render_article(p):
    cat = p['primary_category']
    crumb_items = [('首页', '/')]
    if cat:
        crumb_items.append((cat['name'], f'/categories/{cat["slug"]}/'))
    crumb_items.append((p['title'], p['path']))
    graph = [
        website_node(), org_node(), person_node(),
        {
            '@type': 'BlogPosting',
            '@id': p['url'] + '#article',
            'headline': p['title'],
            'description': p['summary'],
            'datePublished': p['date_iso'],
            'dateModified': p['modified_iso'],
            'author': ({'@id': SITE_URL + '/#person'} if p['author'] == AUTHOR_NAME
                       else {'@type': 'Person', 'name': p['author']}),
            'publisher': {'@id': SITE_URL + '/#organization'},
            'mainEntityOfPage': {'@id': p['url']},
            'isPartOf': {'@id': SITE_URL + '/#website'},
            'inLanguage': 'zh-CN',
            'isAccessibleForFree': True,
            'wordCount': p['words'],
            'timeRequired': f'PT{p["minutes"]}M',
            'articleSection': cat['name'] if cat else '币圈笔记',
            'keywords': [t['name'] for t in p['tags']],
            'about': [{'@type': 'Thing', 'name': t['name']} for t in p['tags']],
            'speakable': {'@type': 'SpeakableSpecification', 'cssSelector': ['.article-header h1', '.article-body > p:first-of-type']},
        },
        breadcrumb_node(crumb_items),
    ]
    if p['image']:
        graph[3]['image'] = [p['image']]
    if p['faq']:
        graph.append({
            '@type': 'FAQPage',
            '@id': p['url'] + '#faq',
            'isPartOf': {'@id': p['url'] + '#article'},
            'mainEntity': [
                {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}}
                for q, a in p['faq']
            ],
        })

    idx = next((i for i, x in enumerate(articles) if x['id'] == p['id']), None)
    prev_p = articles[idx + 1] if idx is not None and idx + 1 < len(articles) else None
    next_p = articles[idx - 1] if idx is not None and idx > 0 else None
    pn = ''
    if prev_p or next_p:
        parts = []
        if prev_p:
            parts.append(f'<a href="{prev_p["path"]}"><span>← 上一篇</span><b>{esc(prev_p["title"])}</b></a>')
        if next_p:
            parts.append(f'<a class="next" href="{next_p["path"]}"><span>下一篇 →</span><b>{esc(next_p["title"])}</b></a>')
        pn = f'<nav class="prev-next" aria-label="上一篇与下一篇">{"".join(parts)}</nav>'

    rel = related_posts(p)
    rel_html = ''
    if rel:
        cards = ''.join(
            f'<a href="{q["path"]}">{esc(q["title"])}<time datetime="{q["date_iso"][:10]}">{q["date_display"]}</time></a>'
            for q in rel)
        rel_html = f'<section class="related"><h2>相关阅读</h2><div class="related-grid">{cards}</div></section>'

    tags_html = ''
    if p['tags']:
        tags_html = ('<ul class="tag-list">' + ''.join(
            (f'<li><a href="/tags/{t["slug"]}/">{esc(t["name"])}</a></li>' if len(tag_posts.get(t['slug'], [])) >= 2
             else f'<li><span>{esc(t["name"])}</span></li>')
            for t in p['tags']) + '</ul>')

    cat_chip = f'<a class="chip" href="/categories/{cat["slug"]}/">{esc(cat["name"])}</a>' if cat else ''
    extra_head = f'''
<meta property="article:published_time" content="{p['date_iso']}">
<meta property="article:modified_time" content="{p['modified_iso']}">
<meta property="article:author" content="hightbiger">
<meta property="article:section" content="{esc(cat['name'] if cat else '币圈笔记', quote=True)}">
{''.join(f'<meta property="article:tag" content="{esc(t["name"], quote=True)}">' for t in p['tags'])}'''

    body = breadcrumb_html(crumb_items) + f'''
<div class="wrap">
  <div class="article-layout">
    <article class="article-main">
      <header class="article-header">
        <div class="article-meta">{cat_chip}<time datetime="{p['date_iso'][:10]}">{p['date_display']}</time><span>{p['minutes']} 分钟阅读</span><span>约 {p['words']} 字</span></div>
        <h1>{esc(p['title'])}</h1>
        <div class="article-meta"><span>作者 {f'<a class="author" href="/about/">{esc(p["author"])}</a>' if p['author'] == AUTHOR_NAME else esc(p['author'])}</span><span>更新于 <time datetime="{p['modified_iso'][:10]}">{date_display(p['modified'])}</time></span></div>
      </header>
      <div class="article-body">{p['html']}</div>
      <footer class="article-foot">
        {tags_html}
        {author_card(p['author'])}
        {risk_note()}
        {pn}
        {rel_html}
      </footer>
    </article>
    <aside class="article-side">{toc_html(p['headings'])}</aside>
  </div>
</div>'''

    title = f'{p["title"]}｜{SITE_TITLE}'
    return page_document(title, p['summary'], p['url'], body, active='', og_type='article',
                         og_image=p['image'], jsonld_graph=graph, extra_head=extra_head)


# --------------------------------------------------------------------------
# standalone pages (about / tools / privacy)
# --------------------------------------------------------------------------
def render_standalone(p, page_type, active, extra_body='', extra_graph=None, desc=None, noindex=False):
    crumb = [('首页', '/'), (p['title'], p['path'])]
    graph = [website_node(), org_node(), person_node(),
             {
                 '@type': page_type,
                 '@id': p['url'],
                 'url': p['url'],
                 'name': p['title'],
                 'description': desc or p['summary'],
                 'inLanguage': 'zh-CN',
                 'dateModified': p['modified_iso'],
                 'isPartOf': {'@id': SITE_URL + '/#website'},
                 'author': {'@id': SITE_URL + '/#person'},
             },
             breadcrumb_node(crumb)]
    if extra_graph:
        graph.extend(extra_graph)
    body = breadcrumb_html(crumb) + f'''
<div class="wrap">
  <div class="article-layout">
    <article class="article-main">
      <header class="article-header">
        <p class="eyebrow">{esc(SITE_NAME)} · {esc(p['title'])}</p>
        <h1>{esc(p['title'])}</h1>
        <div class="article-meta"><span>作者 <a class="author" href="/about/">hightbiger</a></span><span>更新于 <time datetime="{p['modified_iso'][:10]}">{date_display(p['modified'])}</time></span></div>
      </header>
      {extra_body}
      <div class="article-body">{p['html']}</div>
      <footer class="article-foot">{author_card()}{risk_note()}</footer>
    </article>
    <aside class="article-side">{toc_html(p['headings'])}</aside>
  </div>
</div>'''
    title = f'{p["title"]}｜{SITE_TITLE}'
    return page_document(title, desc or p['summary'], p['url'], body, active=active,
                         jsonld_graph=graph, noindex=noindex)


# --------------------------------------------------------------------------
# home
# --------------------------------------------------------------------------
def render_home():
    featured = articles[:9]
    cards = ''.join(post_card(p) for p in featured)
    cat_cards = ''.join(category_card(c) for c in active_cats[:8])
    picks = [p for p in articles if p['id'] in (75, 419, 262)]
    pick_main = picks[0] if picks else articles[0]
    side = [by_id[i] for i in (452, 262, 75) if i in by_id and i != pick_main['id']]
    side_html = ''.join(
        f'<a href="{p["path"]}"><b>{esc(p["title"])}</b><span>{esc(p["summary"][:52])}</span></a>' for p in side)
    latest = articles[0] if articles else None
    home_image = next((p['image'] for p in articles if p['image']), None)
    graph = [website_node(), org_node(), person_node(), {
        '@type': 'Blog',
        '@id': SITE_URL + '/#blog',
        'name': SITE_TITLE,
        'url': SITE_URL + '/',
        'description': SITE_DESC_LONG,
        'inLanguage': 'zh-CN',
        'publisher': {'@id': SITE_URL + '/#organization'},
        'blogPost': [
            {'@type': 'BlogPosting', 'headline': p['title'], 'url': p['url'],
             'datePublished': p['date_iso'], 'dateModified': p['modified_iso']}
            for p in articles[:9]
        ],
    }]
    graph.append({
        '@type': 'ItemList',
        'name': '最新文章',
        'itemListElement': [
            {'@type': 'ListItem', 'position': i + 1, 'url': p['url'], 'name': p['title']}
            for i, p in enumerate(featured)
        ],
    })
    body = f'''
<section class="hero">
  <div class="wrap hero-inner">
    <p class="eyebrow">hightbiger · 币圈博客</p>
    <h1>看懂周期，<span class="accent">管好成本</span>，守住资产</h1>
    <p class="lede">{esc(SITE_DESC)}。{esc(SITE_DESC_LONG)}</p>
    <div class="hero-actions">
      <a class="btn" href="#latest">阅读最新文章</a>
      <a class="btn btn-ghost" href="/tools/">打开工具箱</a>
    </div>
    <div class="hero-stats">
      <div class="stat"><b>{len(articles)}</b><span>篇文章</span></div>
      <div class="stat"><b>{len(active_cats)}</b><span>个分类</span></div>
      <div class="stat"><b>{latest_date.year}</b><span>最近更新</span></div>
      <div class="stat"><b>2023</b><span>开始记录</span></div>
    </div>
  </div>
</section>
<section class="section" id="latest">
  <div class="wrap">
    <div class="section-head"><div><h2>最新文章</h2><p>行情分析、交易成本与钱包安全的长期记录</p></div><a class="section-link" href="/archive/">查看全部</a></div>
    <div class="post-grid">{cards}</div>
  </div>
</section>
<section class="section">
  <div class="wrap">
    <div class="section-head"><div><h2>按分类浏览</h2><p>从周期分析到钱包安全，找到你关心的主题</p></div><a class="section-link" href="/categories/">全部分类</a></div>
    <div class="category-grid">{cat_cards}</div>
  </div>
</section>
<section class="section">
  <div class="wrap">
    <div class="section-head"><div><h2>精选与工具</h2><p>长期主义者的常用资源与深度记录</p></div></div>
    <div class="picks">
      <a class="pick-main" href="{pick_main['path']}">
        <span class="chip">{esc(pick_main['primary_category']['name'] if pick_main['primary_category'] else '精选')}</span>
        <h3>{esc(pick_main['title'])}</h3>
        <p>{esc(pick_main['summary'])}</p>
        <span class="read-more">阅读全文 →</span>
      </a>
      <div class="pick-side">{side_html}</div>
    </div>
  </div>
</section>
<section class="section">
  <div class="wrap">
    <div class="section-head"><div><h2>关于本站</h2><p>一个经历过多次牛熊的个人投资者记录</p></div><a class="section-link" href="/about/">关于 hightbiger</a></div>
    <div class="notice" style="font-size:.95rem;line-height:1.9">{esc(AUTHOR_BIO)}<br><br>本站持续记录比特币周线级别的走势判断、交易所手续费与返佣对比、钱包安全实践，以及金融认知相关书籍的学习笔记。欢迎通过 <a href="https://twitter.com/hightbiger" target="_blank" rel="noopener noreferrer">Twitter</a> 或 <a href="/feed.xml">RSS</a> 关注更新。</div>
  </div>
</section>'''
    return page_document(
        'hightbiger 币圈博客｜比特币周期分析、交易所返佣与钱包安全',
        f'{SITE_DESC}。{SITE_DESC_LONG}',
        SITE_URL + '/', body, active='home', og_image=home_image,
        jsonld_graph=graph)


# --------------------------------------------------------------------------
# listing pages
# --------------------------------------------------------------------------
def render_listing(path, title, heading, intro, plist, active, page_type='CollectionPage',
                   extra_graph=None, noindex=False):
    list_items = ''.join(f'''<li>
  <time datetime="{p['date_iso'][:10]}">{p['date_display']}</time>
  <div>
    <h2><a href="{p['path']}">{esc(p['title'])}</a></h2>
    <p>{esc(p['summary'])}</p>
    <div class="meta">{''.join(f'<a class="chip" href="/categories/{c["slug"]}/">{esc(c["name"])}</a>' for c in p['categories'][:2])}<span>{p['minutes']} 分钟阅读</span></div>
  </div>
</li>''' for p in plist)
    if not list_items:
        list_items = '<li class="empty">暂无文章</li>'
    graph = [website_node(), org_node(), person_node(),
             {
                 '@type': page_type,
                 '@id': abs_url(path),
                 'url': abs_url(path),
                 'name': heading,
                 'description': intro,
                 'inLanguage': 'zh-CN',
                 'isPartOf': {'@id': SITE_URL + '/#website'},
                 'mainEntity': {
                     '@type': 'ItemList',
                     'numberOfItems': len(plist),
                     'itemListElement': [
                         {'@type': 'ListItem', 'position': i + 1, 'url': p['url'], 'name': p['title']}
                         for i, p in enumerate(plist)
                     ],
                 },
             },
             breadcrumb_node([('首页', '/'), (heading, path)])]
    if extra_graph:
        graph.extend(extra_graph)
    body = f'''
<header class="page-head"><div class="wrap">
  <p class="eyebrow">hightbiger · 币圈博客</p>
  <h1>{esc(heading)}</h1>
  <p>{esc(intro)}</p>
  <span class="count">{len(plist)} 篇文章</span>
</div></header>
<div class="wrap"><ul class="post-list">{list_items}</ul></div>'''
    if path.startswith('/categories/'):
        suffix = '分类'
    elif path.startswith('/tags/'):
        suffix = '标签'
    else:
        suffix = ''
    title_full = f'{heading}{" · " + suffix if suffix else ""}｜{SITE_TITLE}'
    return page_document(title_full, intro, abs_url(path), body, active=active,
                         jsonld_graph=graph, noindex=noindex)


def render_categories():
    cards = ''.join(category_card(c) for c in active_cats)
    tags_html = ''.join(
        f'<a href="{t["path"]}">{esc(t["name"])}<span class="n">{len(t["posts"])}</span></a>'
        for t in active_tags)
    body = f'''
<header class="page-head"><div class="wrap">
  <p class="eyebrow">hightbiger · 币圈博客</p>
  <h1>文章分类</h1>
  <p>按主题浏览站内文章：比特币周期分析、交易所成本、钱包安全、金融认知与个人记录。</p>
  <span class="count">{len(active_cats)} 个分类 · {len(articles)} 篇文章</span>
</div></header>
<section class="section"><div class="wrap"><div class="category-grid">{cards}</div></div></section>
<section class="section"><div class="wrap">
  <div class="section-head"><div><h2>标签</h2><p>更细粒度的话题索引</p></div></div>
  <div class="tag-cloud">{tags_html}</div>
</div></section>'''
    graph = [website_node(), org_node(), person_node(), {
        '@type': 'CollectionPage', '@id': abs_url('/categories/'), 'url': abs_url('/categories/'),
        'name': '文章分类', 'inLanguage': 'zh-CN', 'isPartOf': {'@id': SITE_URL + '/#website'},
    }, breadcrumb_node([('首页', '/'), ('文章分类', '/categories/')])]
    return page_document('文章分类｜' + SITE_TITLE,
                         '按主题浏览 hightbiger 币圈博客的全部文章分类，包括周期分析、金融认知、钱包安全与技术笔记。',
                         abs_url('/categories/'), body, active='categories', jsonld_graph=graph)


def render_tags():
    tags_html = ''.join(
        f'<a href="{t["path"]}">{esc(t["name"])}<span class="n">{len(t["posts"])}</span></a>'
        for t in active_tags)
    body = f'''
<header class="page-head"><div class="wrap">
  <p class="eyebrow">hightbiger · 币圈博客</p>
  <h1>全部标签</h1>
  <p>站内文章涉及的主题关键词，按文章数量排序。</p>
  <span class="count">{len(active_tags)} 个标签</span>
</div></header>
<section class="section"><div class="wrap"><div class="tag-cloud">{tags_html}</div></div></section>'''
    graph = [website_node(), org_node(), person_node(), {
        '@type': 'CollectionPage', '@id': abs_url('/tags/'), 'url': abs_url('/tags/'),
        'name': '全部标签', 'inLanguage': 'zh-CN', 'isPartOf': {'@id': SITE_URL + '/#website'},
    }, breadcrumb_node([('首页', '/'), ('全部标签', '/tags/')])]
    return page_document('全部标签｜' + SITE_TITLE,
                         'hightbiger 币圈博客的全部文章标签，涵盖比特币、走势分析、K线技术、钱包安全与交易所返佣等主题。',
                         abs_url('/tags/'), body, active='', jsonld_graph=graph)


def render_archive():
    years = {}
    for p in articles:
        years.setdefault(p['date'].year, []).append(p)
    groups = []
    for year in sorted(years, reverse=True):
        items = ''.join(f'''<li>
  <time datetime="{p['date_iso'][:10]}">{p['date_display']}</time>
  <div><h2><a href="{p['path']}">{esc(p['title'])}</a></h2><p>{esc(p['summary'])}</p></div>
</li>''' for p in posts_by_date_desc(years[year]))
        groups.append(f'<section class="year-group"><h2>{year}</h2><ul class="post-list">{items}</ul></section>')
    body = f'''
<header class="page-head"><div class="wrap">
  <p class="eyebrow">hightbiger · 币圈博客</p>
  <h1>文章归档</h1>
  <p>自 2023 年以来的全部公开文章，按年份倒序排列。</p>
  <span class="count">{len(articles)} 篇文章</span>
</div></header>
<div class="wrap">{''.join(groups)}</div>'''
    graph = [website_node(), org_node(), person_node(), {
        '@type': 'CollectionPage', '@id': abs_url('/archive/'), 'url': abs_url('/archive/'),
        'name': '文章归档', 'inLanguage': 'zh-CN', 'isPartOf': {'@id': SITE_URL + '/#website'},
        'mainEntity': {
            '@type': 'ItemList', 'numberOfItems': len(articles),
            'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'url': p['url'], 'name': p['title']}
                                for i, p in enumerate(articles)],
        },
    }, breadcrumb_node([('首页', '/'), ('文章归档', '/archive/')])]
    return page_document('文章归档｜' + SITE_TITLE, f'hightbiger 币圈博客全部文章归档，共 {len(articles)} 篇。',
                         abs_url('/archive/'), body, active='archive', jsonld_graph=graph)


def render_search():
    body = '''
<header class="page-head"><div class="wrap">
  <p class="eyebrow">hightbiger · 币圈博客</p>
  <h1>搜索文章</h1>
  <p>输入关键词，搜索标题、摘要与标签。</p>
</div></header>
<div class="wrap" data-search>
  <form class="search-box" role="search" onsubmit="return false">
    <input type="search" name="q" placeholder="搜索：比特币 / 钱包安全 / 返佣…" aria-label="搜索关键词" autocomplete="off">
  </form>
  <div class="search-results" data-results><p class="hint">加载搜索索引中…</p></div>
</div>'''
    graph = [website_node(), org_node(), person_node(), {
        '@type': 'SearchResultsPage', '@id': abs_url('/search/'), 'url': abs_url('/search/'),
        'name': '搜索文章', 'inLanguage': 'zh-CN', 'isPartOf': {'@id': SITE_URL + '/#website'},
    }]
    return page_document('搜索文章｜' + SITE_TITLE, '搜索 hightbiger 币圈博客的文章。',
                         abs_url('/search/'), body, active='', jsonld_graph=graph, noindex=True)


# --------------------------------------------------------------------------
# privacy policy (rewritten for the static site)
# --------------------------------------------------------------------------
def render_privacy():
    p = privacy_raw
    html_body = f'''
<h2 id="section-1">本站收集哪些数据</h2>
<p>本站是一个静态网站，不提供评论、登录或会员注册功能，因此不会主动收集访客的姓名、邮箱、IP 地址或其他个人身份信息。</p>
<h2 id="section-2">本地存储</h2>
<p>本站仅在浏览器本地保存一项偏好设置：浅色 / 深色主题的选择（localStorage 键名 <code>theme</code>）。该信息不会上传到服务器，清除浏览器数据即可移除。</p>
<h2 id="section-3">托管与访问日志</h2>
<p>本站通过 GitHub Pages 托管，页面与图片由 GitHub 的服务器提供。GitHub 可能按其隐私政策记录访问日志（例如 IP 地址、浏览器类型与访问时间），本站无法访问或控制这些日志。详见 <a href="https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement" target="_blank" rel="noopener noreferrer">GitHub 隐私声明</a>。</p>
<h2 id="section-4">外部链接与返佣链接</h2>
<p>文章中的交易所、社群与工具链接可能包含返佣参数。点击这些链接后，你将离开本站并受目标网站自己的隐私政策与条款约束。本站无法控制第三方网站的数据处理行为。</p>
<h2 id="section-5">图片资源</h2>
<p>文章图片随站点一起托管，不依赖第三方图床，也不会通过图片请求向第三方传递访客信息。</p>
<h2 id="section-6">政策更新</h2>
<p>如本站功能发生变化（例如未来增加评论或邮件订阅），本政策会相应更新。最后更新日期：2026 年 11 月 7 日。</p>
<h2 id="section-7">联系方式</h2>
<p>如对隐私政策有疑问，可通过 <a href="https://twitter.com/hightbiger" target="_blank" rel="noopener noreferrer">Twitter / X</a> 或 <a href="https://t.me/joinchat/HG8JJBd_fMJDBwQolSs_Kg" target="_blank" rel="noopener noreferrer">Telegram</a> 联系作者。</p>'''
    desc = '了解 hightbiger 币圈博客如何处理访客数据：本站为静态站点，不收集个人信息，仅使用本地主题偏好与 GitHub Pages 托管日志。'
    graph = [website_node(), org_node(), person_node(), {
        '@type': 'WebPage', '@id': p['url'], 'url': p['url'], 'name': '隐私政策',
        'description': desc, 'inLanguage': 'zh-CN', 'dateModified': '2026-11-07T00:00:00+08:00',
        'isPartOf': {'@id': SITE_URL + '/#website'},
    }, breadcrumb_node([('首页', '/'), ('隐私政策', '/privacy-policy/')])]
    body = breadcrumb_html([('首页', '/'), ('隐私政策', '/privacy-policy/')]) + f'''
<div class="wrap"><div class="article-layout"><article class="article-main">
  <header class="article-header">
    <p class="eyebrow">hightbiger · 站务</p>
    <h1>隐私政策</h1>
    <div class="article-meta"><span>更新于 <time datetime="2026-11-07">2026年11月7日</time></span></div>
  </header>
  <div class="article-body">{html_body}</div>
</article><aside class="article-side"></aside></div></div>'''
    return page_document('隐私政策｜' + SITE_TITLE, desc, p['url'], body, active='', jsonld_graph=graph)


# --------------------------------------------------------------------------
# feeds / sitemap / llms / misc
# --------------------------------------------------------------------------
def absolute_html(s):
    s = s.replace('src="/', 'src="' + SITE_URL + '/')
    s = s.replace('href="/', 'href="' + SITE_URL + '/')
    return s


def render_feed():
    items = []
    for p in articles[:30]:
        items.append(f'''<item>
  <title>{cdata(p['title'])}</title>
  <link>{xml_escape(p['url'])}</link>
  <guid isPermaLink="true">{xml_escape(p['url'])}</guid>
  <pubDate>{format_datetime(p['date'])}</pubDate>
  <dc:creator>{cdata(p['author'])}</dc:creator>
  <category>{cdata(p['primary_category']['name'] if p['primary_category'] else '币圈笔记')}</category>
  <description>{cdata(p['summary'])}</description>
  <content:encoded>{cdata(absolute_html(p['html']))}</content:encoded>
</item>''')
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel>
  <title>{cdata(SITE_TITLE)}</title>
  <link>{SITE_URL}/</link>
  <description>{cdata(SITE_DESC + '。' + SITE_DESC_LONG)}</description>
  <language>zh-CN</language>
  <lastBuildDate>{format_datetime(latest_date)}</lastBuildDate>
  <generator>hightbiger static build</generator>
{''.join(items)}
</channel>
</rss>
'''


def render_sitemap():
    urls = []

    def add(path, lastmod, priority, images=None):
        imgs = ''
        if images:
            for im in images[:3]:
                imgs += f'<image:image><image:loc>{xml_escape(im)}</image:loc></image:image>'
        urls.append(f'''<url>
  <loc>{xml_escape(abs_url(path))}</loc>
  <lastmod>{lastmod[:10]}</lastmod>
  <changefreq>{'weekly' if path in ('/', '/archive/') else 'monthly'}</changefreq>
  <priority>{priority}</priority>{imgs}
</url>''')

    add('/', latest_date.isoformat(), '1.0', [articles[0]['image']] if articles and articles[0]['image'] else None)
    add('/archive/', latest_date.isoformat(), '0.6')
    add('/categories/', latest_date.isoformat(), '0.5')
    add('/tags/', latest_date.isoformat(), '0.4')
    for c in active_cats:
        c_date = max(p['modified'] for p in c['posts'])
        add(c['path'], c_date.isoformat(), '0.7')
    for t in active_tags:
        if len(t['posts']) < 2:
            continue
        t_date = max(p['modified'] for p in t['posts'])
        add(t['path'], t_date.isoformat(), '0.5')
    for p in articles:
        add(p['path'], p['modified_iso'], '0.8', [p['image']] if p['image'] else None)
    for pid in (1, 452):
        if pid in by_id:
            p = by_id[pid]
            add(p['path'], p['modified_iso'], '0.7')
    if privacy_raw:
        add(privacy_raw['path'], '2026-11-07T00:00:00+08:00', '0.3')
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
{''.join(urls)}
</urlset>
'''


def render_robots():
    bots = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-Web', 'anthropic-ai',
            'PerplexityBot', 'Perplexity-User', 'Google-Extended', 'Applebot-Extended',
            'CCBot', 'meta-externalagent', 'cohere-ai', 'YouBot', 'DuckAssistBot',
            'Bytespider', 'Amazonbot', 'Bingbot']
    allow = ''.join(f'\nUser-agent: {b}\nAllow: /\n' for b in bots)
    return f'''# hightbiger 币圈博客
User-agent: *
Allow: /
Disallow: /search/
Disallow: /404.html
{allow}
Sitemap: {SITE_URL}/sitemap.xml
'''


def render_llms():
    cats = '\n'.join(f'- [{c["name"]}]({abs_url(c["path"])}): {c["description"]}（{len(c["posts"])} 篇）'
                     for c in active_cats)
    posts = '\n'.join(f'- [{p["title"]}]({p["url"]}): {p["summary"]}（{p["date_iso"][:10]}）'
                      for p in articles)
    return f'''# hightbiger 币圈博客

> {SITE_DESC}。{SITE_DESC_LONG}
> 作者：hightbiger，{AUTHOR_SHORT}。{AUTHOR_BIO}

本站是一个中文个人博客，长期记录比特币周期走势、加密交易所手续费与返佣、钱包安全、金融认知与个人投资复盘。内容面向人类读者，也便于大语言模型与生成式搜索引擎检索和引用。

## 核心页面
- [关于作者]({abs_url('/about/')}): hightbiger 的经历、投资背景与写作方向
- [工具箱]({abs_url('/tools/')}): 常用交易所、看盘工具与社群链接
- [文章归档]({abs_url('/archive/')}): 全部 {len(articles)} 篇文章，按年份排列
- [文章分类]({abs_url('/categories/')}): 按主题浏览
- [RSS 订阅]({SITE_URL}/feed.xml)

## 分类
{cats}

## 全部文章
{posts}

## 引用说明
- 引用或转述本站内容时，请注明作者 hightbiger 并链接到原文。
- 本站内容为个人研究记录，不构成投资建议。
- 机器可读全文见 {SITE_URL}/llms-full.txt 。
'''


def render_llms_full():
    parts = [f'''# hightbiger 币圈博客 — 全文

> {SITE_DESC}。{SITE_DESC_LONG}
> 作者：hightbiger（{abs_url('/about/')}）
> 本文件包含站内全部 {len(articles)} 篇公开文章的正文，供大语言模型与生成式搜索引擎读取。引用请注明来源与原文链接。

''']
    for p in articles:
        md = render.html_to_markdown(p['html'])
        md = md.replace('](/wp-content/', f']({SITE_URL}/wp-content/')
        cat = p['primary_category']['name'] if p['primary_category'] else ''
        tags = '、'.join(t['name'] for t in p['tags'])
        parts.append(f'''---

## {p['title']}

- URL: {p['url']}
- 发布日期: {p['date_iso'][:10]}
- 最后更新: {p['modified_iso'][:10]}
- 分类: {cat}
- 标签: {tags}
- 摘要: {p['summary']}

{md}

''')
    return ''.join(parts)


def render_manifest():
    return json.dumps({
        'name': SITE_TITLE,
        'short_name': 'hightbiger',
        'description': SITE_DESC,
        'start_url': '/',
        'display': 'standalone',
        'background_color': '#f7f5f0',
        'theme_color': '#121110',
        'lang': 'zh-CN',
        'icons': [
            {'src': '/assets/favicon.svg', 'sizes': 'any', 'type': 'image/svg+xml', 'purpose': 'any'},
        ],
    }, ensure_ascii=False, indent=1)


def render_search_index():
    data = []
    for p in articles:
        data.append({
            'title': p['title'],
            'url': p['path'],
            'summary': p['summary'],
            'date': p['date_iso'][:10],
            'category': p['primary_category']['name'] if p['primary_category'] else '',
            'tags': [t['name'] for t in p['tags']],
        })
    for pid in (1, 452):
        p = by_id.get(pid)
        if p:
            data.append({'title': p['title'], 'url': p['path'], 'summary': p['summary'],
                         'date': p['date_iso'][:10], 'category': '', 'tags': []})
    return json.dumps(data, ensure_ascii=False, indent=1)


def legacy_path_map():
    m = {}

    def add(old, target):
        if old and old != '/':
            m[old] = target
            m[unquote(old)] = target

    for p in published:
        add(p.get('old_path'), p['path'])
        if p['type'] == 'page':
            add(f"/index.php/{p['slug']}/", p['path'])
    for pid, target in ID_REDIRECTS.items():
        src = next((x for x in posts_raw if x['id'] == pid), None)
        if src:
            add(urlparse(src.get('link') or '').path, target)
    return m


def render_404():
    id_map = {str(p['id']): p['path'] for p in published}
    id_map.update({str(k): v for k, v in ID_REDIRECTS.items()})
    path_map = legacy_path_map()
    body = '''
<header class="page-head"><div class="wrap">
  <p class="eyebrow">404</p>
  <h1>页面没有找到</h1>
  <p>这个地址可能已经迁移或删除。你可以回到首页，或使用搜索查找文章。</p>
  <div class="hero-actions" style="margin-top:22px">
    <a class="btn" href="/">返回首页</a>
    <a class="btn btn-ghost" href="/search/">搜索文章</a>
  </div>
</div></header>
<div class="wrap"><div class="empty">如果你是从旧版 WordPress 链接跳转而来，页面会自动带你到新地址。</div></div>'''
    graph = [website_node(), org_node(), person_node()]
    page = page_document('页面没有找到｜' + SITE_TITLE, '页面不存在。', SITE_URL + '/404.html',
                         body, jsonld_graph=graph, noindex=True)
    js = ('<script>(function(){var m=' + json.dumps(id_map) +
          ';var paths=' + json.dumps(path_map, ensure_ascii=False) +
          ';var q=new URLSearchParams(location.search);var k=q.get("p")||q.get("page_id");'
          'if(k&&m[k]){location.replace(m[k]);return;}'
          'if(paths[location.pathname]){location.replace(paths[location.pathname]);return;}'
          'var p=decodeURIComponent(location.pathname);'
          'if(paths[p]){location.replace(paths[p]);}})();</script>')
    return page.replace('</body>', js + '\n</body>')


def render_redirect(target):
    t = esc(target, quote=True)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>页面已迁移</title>
<link rel="canonical" href="{t}">
<meta name="robots" content="noindex, follow">
<meta http-equiv="refresh" content="0; url={t}">
<script>location.replace("{t}" + location.hash);</script>
</head>
<body style="font-family:system-ui,sans-serif;padding:48px;line-height:1.8">
<p>此页面已迁移，正在前往 <a href="{t}">{t}</a>。</p>
</body>
</html>
'''


def render_favicon():
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="hightbiger">
  <rect width="64" height="64" rx="14" fill="#17150f"/>
  <path d="M18 16v32M18 33h17a9 9 0 0 0 9-9v-8M44 33v15" fill="none" stroke="#f0b429" stroke-width="6" stroke-linecap="round"/>
  <circle cx="47" cy="19" r="3.5" fill="#f7f5f0"/>
</svg>
'''


def render_redirects_and_cname():
    # legacy WordPress permalinks -> new canonical pages
    seen = set()
    for p in published:
        targets = [p['path']]
        olds = []
        if p.get('old_path'):
            olds.append(p['old_path'])
        if p['type'] == 'page':
            olds.append(f"/index.php/{p['slug']}/")
        for old in olds:
            if not old or old in seen or old == p['path']:
                continue
            seen.add(old)
            # store decoded names: web servers decode %XX before filesystem lookup
            fp = DOCS / unquote(old).strip('/') / 'index.html'
            # Windows path length limit: very long legacy URLs are handled by 404.html
            if len(str(fp)) > 240:
                continue
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(render_redirect(p['path']), encoding='utf-8')
    # WordPress category/tag bases -> new archive paths
    for c in active_cats:
        for old in (f"/category/{c['slug']}/",):
            fp = DOCS / old.strip('/') / 'index.html'
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(render_redirect(c['path']), encoding='utf-8')
    for t in active_tags:
        fp = DOCS / 'tag' / t['slug'] / 'index.html'
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(render_redirect(t['path']), encoding='utf-8')
    for old, target in [
        ('/categories/uncategorized/', '/categories/'),
        ('/category/uncategorized/', '/categories/'),
        ('/feed/', '/feed.xml'),
        ('/feed', '/feed.xml'),
    ]:
        fp = DOCS / old.strip('/') / 'index.html'
        if old.startswith('/categories/') and fp.exists():
            continue
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(render_redirect(target), encoding='utf-8')
    (DOCS / 'CNAME').write_text('wangbiger.com\n', encoding='utf-8')


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
def main():
    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir(parents=True)
    (DOCS / 'assets').mkdir(parents=True, exist_ok=True)

    # static assets
    for f in ('style.css', 'app.js'):
        shutil.copy2(STATIC / f, DOCS / 'assets' / f)
    (DOCS / 'assets' / 'favicon.svg').write_text(render_favicon(), encoding='utf-8')
    (DOCS / '.nojekyll').write_text('', encoding='utf-8')

    # images
    if UPLOADS_SRC.exists():
        shutil.copytree(UPLOADS_SRC, DOCS / 'wp-content' / 'uploads')

    # home
    write('/', render_home())
    # articles
    for p in articles:
        if p.get('is_page'):
            continue
        write(p['path'], render_article(p))
    # about + tools
    if 1 in by_id:
        p = by_id[1]
        write('/about/', render_standalone(p, 'AboutPage', 'about',
                                           desc=f'了解 hightbiger：{AUTHOR_BIO}'))
    if 452 in by_id:
        p = by_id[452]
        write('/tools/', render_standalone(p, 'WebPage', 'tools',
                                           desc='hightbiger 的常用工具箱：交易所注册与返佣链接、看盘工具、社群与个人主页入口。'))
    if privacy_raw:
        write('/privacy-policy/', render_privacy())
    # listings
    write('/archive/', render_archive())
    write('/categories/', render_categories())
    write('/tags/', render_tags())
    write('/search/', render_search())
    for c in active_cats:
        write(c['path'], render_listing(c['path'], c['name'], c['name'], c['description'],
                                        posts_by_date_desc(c['posts']), active='categories'))
    for t in active_tags:
        write(t['path'], render_listing(t['path'], t['name'], t['name'], t['description'],
                                        t['posts'], active='',
                                        noindex=len(t['posts']) < 2))
    # data files
    write_raw('feed.xml', render_feed())
    write_raw('sitemap.xml', render_sitemap())
    write_raw('robots.txt', render_robots())
    write_raw('llms.txt', render_llms())
    write_raw('llms-full.txt', render_llms_full())
    write_raw('search-index.json', render_search_index())
    write_raw('manifest.webmanifest', render_manifest())
    write_raw('404.html', render_404())
    render_redirects_and_cname()

    # report
    total_files = sum(1 for _ in DOCS.rglob('*') if _.is_file())
    print(f'built: {len(articles)} articles, {len(active_cats)} categories, '
          f'{len(active_tags)} tags, {total_files} files')
    print(f'latest update: {latest_date.date()}')


if __name__ == '__main__':
    main()
