# hightbiger 币圈博客

[wangbiger.com](https://wangbiger.com) 的静态站点重建版。内容来自 WordPress 备份，生成纯静态 HTML，托管在 GitHub Pages，并针对生成式搜索引擎（GEO）做了结构化数据与可抓取性优化。

## 技术栈

- 纯 Python 3 构建脚本，无第三方依赖
- 输出到 `docs/`，由 GitHub Pages 直接托管
- 原生 HTML / CSS / JavaScript，无前端框架
- 图片随站点托管，保留原 WordPress 的 `/wp-content/uploads/` 路径

## 目录结构

```
.
├── build/
│   ├── build.py            # 站点生成器（页面、JSON-LD、sitemap、feed 等）
│   ├── render.py           # WordPress HTML 清洗与文本工具
│   ├── static/             # style.css、app.js、favicon
│   └── uploads/            # 文章图片（构建时复制到 docs/wp-content/uploads/）
├── content/                # 从 WXR 提取的结构化内容（JSON）
├── docs/                   # 生成后的站点（GitHub Pages 根目录）
├── tools/
│   ├── extract_content.py  # WXR -> content/*.json
│   ├── download_assets.py  # 下载文章图片到 build/uploads/
│   └── validate_site.py    # 链接、JSON-LD、sitemap 等校验
└── README.md
```

## 本地预览

```bash
cd wangbiger-blog
python -I -m http.server 8000 --directory docs
```

打开 <http://127.0.0.1:8000/>。

## 重建

只有修改 `content/` 或 `build/` 时需要重建：

```bash
python -I build/build.py
python -I tools/validate_site.py docs
```

从原始 WordPress 备份完整重建：

```bash
python -I tools/extract_content.py "../备份/hightbiger.WordPress.2026-11-07.xml" content
python -I tools/download_assets.py content/posts.json build/uploads
python -I build/build.py
python -I tools/validate_site.py docs
```

> 原始 WXR 备份包含作者邮箱等个人信息，不要提交到仓库。仓库中只保留清洗后的 `content/`。

## 部署到 GitHub Pages

仓库：`hightbiger/wangbiger.com`

1. 推送 `main` 分支。
2. 仓库 **Settings → Pages**：
   - Source 选择 **Deploy from a branch**
   - Branch 选择 **main**，目录选择 **/docs**
3. **Custom domain** 填写 `wangbiger.com`，保存后等待 DNS 检查通过。
4. 勾选 **Enforce HTTPS**。

`docs/CNAME` 已包含 `wangbiger.com`，无需手动创建。

### DNS 记录

在域名服务商处配置：

| 类型 | 主机记录 | 记录值 |
| --- | --- | --- |
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| AAAA | @ | 2606:50c0:8000::153 |
| AAAA | @ | 2606:50c0:8001::153 |
| AAAA | @ | 2606:50c0:8002::153 |
| AAAA | @ | 2606:50c0:8003::153 |
| CNAME | www | hightbiger.github.io |

如果域名此前解析到旧 WordPress 主机，需要先删除旧的 A / CNAME 记录，避免冲突。

## GEO / SEO 说明

构建时自动生成：

- 每页 JSON-LD：`WebSite`、`Organization`、`Person`、`Blog`、`BlogPosting`、`BreadcrumbList`、`CollectionPage`、`FAQPage`、`AboutPage`
- `llms.txt` 与 `llms-full.txt`（供大模型读取的站点摘要与全文）
- `sitemap.xml`（含图片 sitemap）、`feed.xml`、`robots.txt`
- canonical、hreflang、Open Graph、Twitter Card、`speakable`
- 文章摘要、目录、作者 E-E-A-T 信息、相关阅读与上下篇
- 旧 WordPress 链接重定向（静态跳转页 + `404.html` 兜底）

## 内容约定

- 所有文章已按“全部公开”处理，付费/VIP 提示与重复段落已在构建时清理。
- 文章作者统一显示为站点作者 `hightbiger`。
- 旧文章链接通过 `ID_REDIRECTS` / `OLD_TO_NEW` 映射到新地址，新增文章时无需手动维护旧链接。

## 许可

内容版权归 hightbiger 所有，未经许可请勿转载。
