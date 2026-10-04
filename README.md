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
│   ├── collect.py           # 采集器（9 源，单源失败隔离）
│   └── data/numbers.json    # 采集输出
├── web/
│   ├── index.html           # 首页（含站内短信查看面板）
│   ├── guide.html           # 使用说明
│   ├── sources.html         # 数据来源
│   ├── sitemap.xml / robots.txt
│   └── data/numbers.json    # 前端读取
├── api/
│   └── reader.js# 短信渲染服务（puppeteer-core，127.0.0.1:18620）
├── scripts/
│   ├── refresh.sh           # 服务器定时刷新（采集→校验→替换）
│   ├── issue-cert.sh        # 一键签证书+切配置+自检
│   ├── deploy.sh            # 本地一键部署
│   ├── deploy-reader.sh     # 一键部署短信渲染服务
│   └── sms-hub.nginx.conf   # nginx 站点配置（含 /api/ 反代）
├── tools/
│   ├── test-otp.js# 验证码提取回归测试（13 条真实样本）
│   └── audit_*.py / probe_*.py# 源站审计与探测脚本
├── docs/
│   └── SOURCE-AUDIT-2026-10.md   # 20 源实测审计报告
├── verify-v2.js             # 5 视口 + 20 项交互验收
├── verify-pages.js          # 内页与链接验收
├── verify-multisource.js    # 多源改造验收
├── verify-reader.js         # 短信面板端到端验收
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

# 部署短信渲染服务（后端，只需首次或改代码时）
bash scripts/deploy-reader.sh

# 验证码提取回归测试（纯离线，不联网）
node tools/test-otp.js

# 验收（需 puppeteer-core）
NODE_PATH=<路径> node verify-v2.js
NODE_PATH=<路径> node verify-pages.js
NODE_PATH=<路径> node verify-reader.js
```

## 部署架构

- 服务器：腾讯云美国弗吉尼亚 `170.106.38.62`（`VM-0-4-ubuntu`，与 jinzhai / tingguanjia / bank-converter 同机）
- 站点目录 `/opt/sms-hub`，静态页nginx 直出 + 短信渲染服务经`/api/` 反代
- 短信渲染服务：systemd `sms-reader`，仅监听 `127.0.0.1:18620`，开机自启
- 定时刷新 crontab `7,37 * * * *`（错开整点），日志 `logs/refresh.log`
- 刷新脚本为**采集→校验→替换**三段式，校验不通过则保留旧数据，不会把线上刷空
- HTTPS：Let's Encrypt ECDSA，certbot.timer 自动续期

## 合规边界

采集侧（号码索引）：

- ✅ 只抓公开列表页，串行请求 + 随机延迟
- ✅ 单源失败隔离，任一源挂掉不影响整体产出
- ❌ 不登录、不绕过登录墙 / 付费墙 / 反爬
- 页面顶部有醒目提示，页脚与使用说明页均有免责声明

短信正文侧（站内查看，仅 `receiveasmsonline.com` 一个源）：

- ✅ 经20 源实测审计，只有该源的公开号码页**无需登录即可看到真实短信**
  （其余源或 403、或正文被替换成「登录后查看」占位——对方已设限制，本站尊重）
- ✅ 只渲染公开可见内容，**不绕人机验证、不做反检测伪装**；源站一旦挡住就放弃
- ✅ 双层限频保护源站：同号码 15 秒一次、来源 IP 12 次/分钟，**仅在成功后计数**
- ✅ 12 秒短缓存，读取的都是源站此刻的公开内容；不做历史留存、不做二次分发
- ⚠️ 公共号码人人可读，验证码有效性以原站与接收方为准——面板内每条短信
  都标注「疑似验证码（自动识别，请自行核对）」，合规提示常驻不可被覆盖
- ❌ 不存储短信正文、不提供验证码代收转发

## 短信渲染服务（api/）

站内「查看短信」面板的后端，跑在**同源 `127.0.0.1:18620`**，nginx `/api/` 反代，
公网不可直连（`/healthz` 返回 404）。

```
api/reader.js        puppeteer-core +系统 Chrome（不下载 Chromium）
scripts/deploy-reader.sh   一键部署 + systemd 守护
```

设计要点（都是实测踩出来的）：

|决策 | 原因 |
|---|---|
| `puppeteer-core` 复用 `/usr/bin/google-chrome` | 少下~300MB Chromium |
| 单例 browser + 全局并发 2 + 用完即close | 容器内存有限，防page 泄漏 |
| `--disable-dev-shm-usage` | 容器 `/dev/shm` 只有 64MB，不加会随机崩 |
| `domcontentloaded` + 轮询等骨架屏消失 | 比 `networkidle2` **快 11 倍**（15s → 2.7s） |
| `setCacheEnabled(false)` | 验证码有时效，宁可每次回源也不要 304 的旧页面 |
| `lastSuccessAt` 而非请求前占位 | 失败不占配额，否则首次请求会被自己的失败挡住 |
| 按正文去重（非按 raw） | 源站同页渲染桌面+移动两份 DOM，按 raw 会漏 |

### 验证码识别（extractOtp）

**宁可返回 null，也不给错的。** 实测源站短信尾部常挂干扰号码：

```
G-132619 is your Google verification code. 1897373737
     ↑ 真验证码        ↑ 干扰号
```

早期实现会命中尾部 10 位号码并截成 `18973737`，直接把用户引到错误验证码上。
现用 `(?<!\d)(\d{4,8})(?!\d)` 锁死数字完整性 + 优先`G-` / 括号 / 「code」上下文强特征，
干扰号因超长被排除。回归测试：`node tools/test-otp.js`（13 条真实样本，全通过）。

## 验收记录

真实浏览器（puppeteer-core + 本机 Chrome）实测：

- 5 视口 1440 / 1024 / 768 / 390 / 360：无页面级横向溢出，移动端单列
- 20 项交互测试全通过：搜索（中文名/英文名/区号）、组合筛选、国家快捷、
  排序、复制、刷新、移动端筛选面板（临时选择 + 应用才生效 + Esc 关闭）
- 内链 103 条全部有效；页面无「在线」「已验证」字样
- 线上 6 个 URL（首页/说明/来源/sitemap/robots/数据）全部 200，零 JS 错误

短信面板端到端（`verify-reader.js`，线上真实号码）：

- 1103 张卡片中 364 张带「站内查看」（= receiveasmsonline 的全部号码，范围精确）
- 面板真实渲染 6 条短信、耗时 4.2s，验证码复制按钮生效
- 合规提示常驻、原站链接正确、关闭后body 滚动恢复
- 4 视口（1440/768/390/360）面板零横向溢出
- **控制台错误 0 条、失败请求 0 条**
