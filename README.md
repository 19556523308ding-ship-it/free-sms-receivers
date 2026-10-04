# 接码号码聚合 · Free SMS Receiver Aggregator

聚合多个平台**公开展示**的免费临时接码手机号，标注国家归属、短信累计量与在线状态，一键跳转原站查看验证码。

## 数据来源与实测结果

| 源 | 状态 | 抓取内容 | 备注 |
|---|---|---|---|
| [Receive-SMS-Online](https://receive-sms-online.info/) | ✅ 200 | 72 个号码 + 国家 + 短信总数 | 瑞典/芬兰/荷兰为主 |
| [Quackr](http://quackr.io/) | ✅ 200 | 18 个号码 + 13 国 + 在线状态 | 完整号码在 permalink 里 |
| [WeTalk](https://wetalkapp.com/receive-sms/) | ✅ 200 | 4 个号码（美/加） | WordPress 博文 permalink |
| smsreceivefree.com | ❌ 502 | — | 站点已挂 |
| sms-man.com | ❌ 403 | — | Cloudflare 拦截 |
| 5sim / SMS-Activate / Grizzly | ✅ 200 | 付费平台，无免费公开号码 | 不纳入 |

合计 **94 个去重号码 / 14 个国家**。

> 原始的 16 平台文字介绍（来自上游 `fazgal0/free-sms-receivers`）已保留在
> [`docs/PLATFORMS.md`](docs/PLATFORMS.md)，作为选型参考。

## 合规边界（重要）

本项目**刻意不做**以下事情：

- ❌ 不绕过任何登录墙 / 付费墙 / 反爬机制
- ❌ **不抓取短信正文**。实测 Receive-SMS-Online 的接口
  `get_sms_register.php?phone=xxx` 虽然无需鉴权即可返回 JSON，但正文已被替换为
  "To view message you need to Login or Sign up" 占位提示——即对方已设限制，
  本站尊重该限制，只聚合号码元数据。
- ❌ 不存储、不转发短信内容
- ✅ 只抓公开列表页，串行请求 + 随机延迟（1.5–3s）
- ✅ 单源失败隔离，任一源挂掉不影响整体产出
- ✅ 所有跳转链接带 `rel="noopener noreferrer nofollow"`

页面顶部有醒目提示：公共号码短信对所有人可见，请勿用于重要账号。

## 目录结构

```
sms-hub/
├── scrapers/
│   ├── collect.py          # 采集器（3 个源，失败隔离）
│   └── data/numbers.json   # 采集输出
├── web/
│   ├── index.html          # 单页前端（零依赖）
│   └── data/numbers.json   # 前端读取的数据
├── verify.js               # puppeteer 真实浏览器验证
└── probe.py                # 结构探测脚本（开发用）
```

## 使用

```bash
# 采集（建议每 30 分钟跑一次）
python scrapers/collect.py

# 同步到前端目录
cp scrapers/data/numbers.json web/data/numbers.json

# 本地预览
cd web && python -m http.server 8899
# 打开 http://127.0.0.1:8899

# 浏览器验证（截图 + 断言 + 移动端检查）
NODE_PATH=<puppeteer-core路径> node verify.js
```

## 技术要点

- **纯静态**：无框架、无构建、无后端，扔到 Cloudflare Pages / 任意静态托管即可
- **国家名规范化**：源站用 `united-states` / `United States` / `USA` 等多种写法，
  统一 `_norm_key()` 归一化后查表映射到中文名 + 国旗 + 国家码
- **号码归一化**：统一输出 E.164 格式（`+3584573994619`）
- **移动端**：390px 下单列布局，控件全宽，实测无横向溢出

## 免责声明

本站仅做号码元数据聚合与导流。使用者需遵守所在地法律法规及各平台服务条款，
因使用公共接码号码造成的账号封禁、财产损失等后果由使用者自行承担。
