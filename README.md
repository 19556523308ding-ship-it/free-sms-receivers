# SMS Hub · 全球公开号码聚合

线上：<https://sms.jinzhai.icu/>

聚合多个公开平台的临时号码索引，标注国家归属、短信条数与可核实状态，一键跳转原站查看短信。

## 数据来源与实测结果

| 源 | 抓取内容 | 记录数 | 覆盖 |
|---|---|---|---|
| [Receive-SMS-Online](https://receive-sms-online.info/) | 完整号码 + 国家 + **短信条数** + **Ready 状态** | 72 | 瑞典/芬兰/荷兰等 |
| [Quackr](http://quackr.io/) | 完整号码 + 国家 + 在线图标（**无短信条数**） | 18 | 13 国 |
| [WeTalk](https://wetalkapp.com/receive-sms/) | 完整号码 + 国家（无状态、无计数） | 4 | 美国/加拿大 |

合计 **94 个去重号码 / 14 个国家**。

已探明但不可用：

| 源 | 原因 |
|---|---|
| smsreceivefree.com | 502，站点已挂 |
| sms-man.com | 403 Cloudflare 拦截 |
| 5sim / SMS-Activate / Grizzly | 付费平台，无免费公开号码 |

> 原始的 16 平台文字介绍（来自上游 `fazgal0/free-sms-receivers`）保留在
> [`docs/PLATFORMS.md`](docs/PLATFORMS.md)。

## 字段口径（重要）

严格遵守「只写真实抓到的字段，抓不到就写 null」：

| 字段 | 说明 |
|---|---|
| `phone` | 完整号码，E.164 格式。**从不显示掩码** |
| `countryCode` | ISO 两字母，由区号归类 |
| `messageCount` | 仅 RSO 提供；其余来源为空，页面显示「短信记录未提供」 |
| `lastMessageAt` | **全部为 null**。三个来源列表页均不提供最近短信时间 |
| `collectedAt` | 本站收录该记录的时间，**不是**短信收发时间 |
| `availability` | 仅 `recent_activity`(72) / `unknown`(22) |
| `statusEvidence` | 状态判断的文字依据 |

### 为什么不显示「在线」

方案要求「没有核验依据不展示在线」。要给出「已验证在线」必须实际发短信确认接收，
本站不做此类验证，因此：

- **不产出** `verified_online` 状态
- Quackr 虽有在线图标，但无短信条数可交叉验证 → 记为「状态未知」
- 不提供可用性评分（「92 分高可用」这类静态评分会误导）

## 目录结构

```
sms-hub/
├── scrapers/
│   ├── collect.py           # 采集器（3 源，单源失败隔离）
│   └── data/numbers.json    # 采集输出
├── web/
│   ├── index.html           # 首页
│   ├── guide.html           # 使用说明
│   ├── sources.html         # 数据来源
│   ├── sitemap.xml / robots.txt
│   └── data/numbers.json    # 前端读取
├── scripts/
│   ├── refresh.sh           # 服务器定时刷新（采集→校验→替换）
│   ├── issue-cert.sh        # 一键签证书+切配置+自检
│   ├── deploy.sh            # 本地一键部署
│   └── sms-hub.nginx.conf   # nginx 站点配置
├── verify-v2.js             # 5 视口 + 20 项交互验收
├── verify-pages.js          # 内页与链接验收
└── verify-online.js         # 线上真实浏览器验证
```

## 使用

```bash
# 采集
python scrapers/collect.py

# 本地预览
cd web && python -m http.server 8899

# 部署（采集→校验→上传→线上自检）
bash scripts/deploy.sh

# 验收（需 puppeteer-core）
NODE_PATH=<路径> node verify-v2.js
NODE_PATH=<路径> node verify-pages.js
```

## 部署架构

- 服务器：腾讯云美国弗吉尼亚 `170.106.38.62`（`VM-0-4-ubuntu`，与 jinzhai / tingguanjia / bank-converter 同机）
- 站点目录 `/opt/sms-hub`，纯静态 nginx 直出，不起反代进程
- 定时刷新 crontab `7,37 * * * *`（错开整点），日志 `logs/refresh.log`
- 刷新脚本为**采集→校验→替换**三段式，校验不通过则保留旧数据，不会把线上刷空
- HTTPS：Let's Encrypt ECDSA，certbot.timer 自动续期

## 合规边界

- ✅ 只抓公开列表页，串行请求 + 随机延迟
- ✅ 单源失败隔离，任一源挂掉不影响整体产出
- ❌ 不登录、不绕过登录墙 / 付费墙 / 反爬
- ❌ **不抓取短信正文**。RSO 的 `get_sms_register.php` 虽无需鉴权即可返回 JSON，
  但正文已被替换为「To view message you need to Login or Sign up」占位——
  对方已设限制，本站尊重该限制
- ❌ 不存储、不转发短信内容；不提供短信接收或验证码代收
- 页面顶部有醒目提示，页脚与使用说明页均有免责声明

## 验收记录

真实浏览器（puppeteer-core + 本机 Chrome）实测：

- 5 视口 1440 / 1024 / 768 / 390 / 360：无页面级横向溢出，移动端单列
- 20 项交互测试全通过：搜索（中文名/英文名/区号）、组合筛选、国家快捷、
  排序、复制、刷新、移动端筛选面板（临时选择 + 应用才生效 + Esc 关闭）
- 内链 103 条全部有效；页面无「在线」「已验证」字样
- 线上 6 个 URL（首页/说明/来源/sitemap/robots/数据）全部 200，零 JS 错误
