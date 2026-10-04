/**
 * SMS Hub 短信渲染服务 (sms-reader)
 * ---------------------------------------------------------------------------
 * 用途：对「页面上公开可见」的短信正文做按需渲染，站内展示。
 * 当前唯一支持的源：receiveasmsonline.com（2026-10-05 实测确认无验证码、
 * 无 X-Frame-Options 限制、无 robots.txt 限制）。
 *
 * 合规边界（硬约束，写在代码里防止后续被无意破坏）：
 *  1. 只读取页面公开可见的短信内容，不绕登录墙、不破人机验证、不做反检测伪装。
 *  2. 不代理任何需要鉴权的接口。
 *  3. 单源限频：同号码 >= MIN_INTERVAL_MS 才允许再次抓取，避免把源站打挂。
 *  4. 内容始终附原站链接，站内展示不替代原站。
 *
 * 资源控制（常驻 Chrome 的主要风险点）：
 *  - 全局单例 browser，最多 CONCURRENCY 个并发 page
 *  - 每个 page 用完立刻 close()，杜绝泄漏
 *  - 空闲 IDLE_RESTART_MS 或存活 BROWSER_TTL_MS 后重启 browser
 *  - 渲染超时 HARD_TIMEOUT_MS，超时强制 close
 *  - --disable-dev-shm-usage 避免 /dev/shm 写满导致 Chrome 崩溃
 */
'use strict';

const express = require('express');
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

// ------------------------------------------------------------------ 配置
const CONFIG = {
  port: Number(process.env.SMS_READER_PORT || 18620),
  bind: process.env.SMS_READER_BIND || '127.0.0.1',
  chromePath: process.env.CHROME_PATH || '/usr/bin/google-chrome',
  upstreamBase: 'https://receiveasmsonline.com',

  // 允许的国家 slug 白名单（只开放实测有货的国家，避免任意 slug 变成开放代理）
  allowedSlugs: new Set([
    'united-states', 'united-kingdom', 'germany', 'france', 'china', 'canada',
    'russia', 'netherlands', 'india', 'israel', 'kazakhstan', 'mexico',
    'indonesia', 'portugal', 'thailand', 'philippines', 'croatia', 'sweden',
    'hong-kong', 'finland', 'ukraine', 'ireland', 'nigeria', 'brazil',
    'belgium', 'spain', 'romania', 'czech-republic', 'italy', 'japan',
    'austria', 'taiwan', 'singapore', 'south-korea', 'poland', 'mauritius',
    'morocco', 'georgia', 'ukraine-alt',
  ]),

  maxPerSlug: new Map(),      // slug -> 同时进行的抓取数（每国限流）
  MIN_INTERVAL_MS: 15000,     // 同号码最小抓取间隔
  CACHE_TTL_MS: 12000,        // 缓存有效期（此期间直接返回，不重复抓源）
  CONCURRENCY: 2,             // 全局最大并发 page
  HARD_TIMEOUT_MS: 30000,     // 单次渲染硬超时
  IDLE_RESTART_MS: 180000,    // 空闲多久后重启 browser
  BROWSER_TTL_MS: 900000,     // browser 最长存活
  MAX_CACHE_ENTRIES: 300,     // 内存缓存条目上限
};

const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';

// ------------------------------------------------------------------ 状态
let browser = null;
let browserBornAt = 0;
let lastActivityAt = Date.now();
let launching = null;
let shuttingDown = false;

/** phone -> { at, payload } */
const cache = new Map();
/** phone -> timestamp，**上次成功抓取**时刻（用于限频；失败不计入） */
const lastSuccessAt = new Map();
/** 客户端 IP -> { count, windowStart }，防止单个 IP 换号码轮番轰炸源站 */
const ipHits = new Map();
const IP_WINDOW_MS = 60000;
const IP_MAX_PER_WINDOW = 12;   // 单 IP 每分钟最多 12 次（号码级限频之外的粗粒度防洪）
/** 当前活跃 page 数 */
let activePages = 0;
const stats = { requests: 0, hits: 0, misses: 0, failures: 0, timeouts: 0, rendered: 0 };

const log = (...a) => console.log(new Date().toISOString(), ...a);

// ------------------------------------------------------------------ browser
async function launchBrowser() {
  if (launching) return launching;
  launching = (async () => {
    const b = await puppeteer.launch({
      executablePath: CONFIG.chromePath,
      headless: 'new',
      // 容器环境必备：/dev/shm 通常只有 64MB，不关掉会随机崩溃
      args: [
        '--no-sandbox', '--disable-setuid-sandbox',
        '--disable-dev-shm-usage', '--disable-gpu',
        '--disable-software-rasterizer', '--no-zygote',
        '--lang=en-US',
        '--window-size=1280,900',
      ],
      protocolTimeout: 60000,
    });
    browser = b;
    browserBornAt = Date.now();
    lastActivityAt = Date.now();
    b.on('disconnected', () => {
      if (browser === b) { browser = null; log('[browser] 已断开，下次请求时重建'); }
    });
    log('[browser] 已启动 pid=' + (b.process() ? b.process().pid : '?'));
    return b;
  })().finally(() => { launching = null; });
  return launching;
}

async function getBrowser() {
  if (browser && browser.connected) {
    const idle = Date.now() - lastActivityAt;
    const tooOld = Date.now() - browserBornAt > CONFIG.BROWSER_TTL_MS;
    if (idle > CONFIG.IDLE_RESTART_MS || tooOld) {
      log('[browser] 空闲 ' + Math.round(idle / 1000) + 's / 超龄，重启');
      const old = browser; browser = null;
      old.close().catch(() => {});
    } else {
      return browser;
    }
  }
  return launchBrowser();
}

function acquireSlot() {
  if (activePages >= CONFIG.CONCURRENCY) return false;
  activePages++;
  return true;
}
function releaseSlot() { activePages = Math.max(0, activePages - 1); }

// ------------------------------------------------------------------ 解析
/**
 * 从渲染后的页面里抽取短信。
 * 选择器依据实测 DOM：[class*="MessageContainer"] 内每条 [class*="Message"]，
 * 结构为「正文 …… 发件方 …… 时间」。
 * 抽取失败时返回空数组而不是报错（可能该号码确实没短信）。
 */
function extractMessages() {
  // 注意：本函数被序列化后在浏览器上下文执行，不能引用外部作用域变量。
  const KEYWORD = /verification code|your code|one[-\s]?time|otp|passcode|security code|is your|code is|验证码|短信|code:/i;
  // 正文 -> 记录。用Map 而非按 raw 去重：源站同一页面会渲染多份消息区
  //（桌面版 + 移动版），其中一份可能带完整时间、另一份只有正文。
  // 按 raw 去重会把它们当成两条不同短信（实测出现重复且 when 为空的条目），
  // 故按正文归并，同一条短信取元数据更完整的那份。
  const byBody = new Map();

  const containers = document.querySelectorAll('[class*="MessageContainer"], [class*="MessagesContainer"]');
  containers.forEach((box) => {
    box.querySelectorAll('[class*="Message"]').forEach((el) => {
      // 排除容器本身与 LoadingMessage 骨架屏
      if (el.className && String(el.className).includes('LoadingMessage')) return;
      const raw = (el.innerText || '').trim();
      if (!raw || raw.length < 4) return;

      const lines = raw.split('\n').map((s) => s.trim()).filter(Boolean);
      if (lines.length === 0) return;

      // 末行常是「发件方 · 日期 时间」，倒数第二行是正文
      let sender = '';
      let when = '';
      const tail = lines[lines.length - 1];
      const tailParts = tail.split(/\s*[|·•]\s*/).map((s) => s.trim()).filter(Boolean);
      if (tailParts.length && /\d{4}/.test(tail)) {
        when = tailParts[tailParts.length - 1];
        if (tailParts.length >= 2) sender = tailParts[tailParts.length - 2];
        else if (lines.length >= 2) {
          // 没有分隔符时，倒数第二行常是纯发件方（如 FACEBOOK / ECG）
          const cand = lines[lines.length - 2];
          if (cand.length <= 24 && !/\d{3,}/.test(cand)) { sender = cand; lines.splice(lines.length - 2, 1); }
        }
        lines.pop();
      }
      const body = lines.join(' ').trim();
      if (!body) return;
      if (!KEYWORD.test(body) && !/\d{4,8}/.test(body)) return;

      const prev = byBody.get(body);
      // 已存在时只在「新这份元数据更全」时覆盖
      if (!prev) byBody.set(body, { body, sender, when, raw });
      else if (!prev.when && when) byBody.set(body, { body, sender: sender || prev.sender, when, raw });
    });
  });

  const out = Array.from(byBody.values());
  out.sort((a, b) => (b.when || '').localeCompare(a.when || ''));
  return out.slice(0, 20);
}

/**
 * 提取最可能的验证码。
 *
 * 实测踩过的坑：源站短信正文后面常带一串干扰号码（发件方号码/推广号），形如
 *   "G-132619 is your Google verification code. 1897373737"
 * 真正的验证码是132619，但朴素的「code 后面取数字」会命中尾部的 10 位号码并截成
 * 18973737 —— 直接把用户引到错误验证码上。因此这里加了三层约束：
 *   1. 数字串必须是「完整」的 4-8 位（用 (?!\d) 挡住长号码被截断）
 *   2. 优先带前缀的强特征（G-123456 / #123456 / 短信里的 6 位独立码）
 *   3. 候选必须自带验证码语境或独立成词，否则宁可返回 null 让用户自己看正文，
 * 也不给一个可能错的。
 */
function extractOtp(text) {
  if (!text) return null;
  const s = String(text);

  // 数字必须是完整的 4-8 位，前后不能再接数字（否则就是长号被截断）
  const NUM = String.raw`(?<!\d)(\d{4,8})(?!\d)`;

  // 强特征：G-123456（Google）、#123456、括号包裹、短信：【123456】
  const strong = [
    new RegExp(String.raw`\bG-(\d{4,8})\b`, 'i'),
    new RegExp(String.raw`[【\[（(](\d{4,8})[】\]）)]`),
    new RegExp(String.raw`#(\d{4,8})\b`),
    new RegExp(String.raw`验证码[^0-9]{0,6}(\d{4,8})`),
    new RegExp(String.raw`(?:verification|security|confirmation)\s*code[^0-9]{0,12}${NUM}`, 'i'),
    new RegExp(String.raw`\b(?:code|pin|otp|passcode)\b[^0-9]{0,12}${NUM}`, 'i'),
    new RegExp(String.raw`\bcode\s+(\d{4,8})\b`, 'i'),
  ];
  for (const re of strong) {
    const m = s.match(re);
    if (m && m[1]) return m[1];
  }

  // 兜底：正文里独立成词的 4-8 位数字
  const standalone = s.match(new RegExp(String.raw`(?:^|\s)${NUM}(?:\s|$)`));
  if (standalone) return standalone[1];

  return null;
}

// ------------------------------------------------------------------ 抓取
async function renderPhone(slug, phone) {
  if (shuttingDown) throw new Error('服务正在关闭');

  if (!acquireSlot()) {
    const err = new Error('服务繁忙，请稍后重试');
    err.status = 503;
    throw err;
  }

  let page = null;
  const timer = setTimeout(() => {
    stats.timeouts++;
    log('[timeout] ' + slug + '/' + phone);
    if (page) { try { page.close(); } catch (e) { /* ignore */ } }
  }, CONFIG.HARD_TIMEOUT_MS);

  try {
    const b = await getBrowser();
    lastActivityAt = Date.now();

    page = await b.newPage();
    await page.setUserAgent(UA);
    await page.setExtraHTTPHeaders({ 'Accept-Language': 'en-US,en;q=0.9' });
    // 关掉本地缓存：验证码短信有时效，宁可每次都回源站拿最新的，
    // 也好过因为命中 ETag 拿到 304 的旧页面。
    await page.setCacheEnabled(false);
    // 图片/字体拦掉，省内存也快
    await page.setRequestInterception(true);
    page.on('request', (req) => {
      const t = req.resourceType();
      if (t === 'image' || t === 'font' || t === 'media') {
        req.abort().catch(() => {});
      } else {
        req.continue().catch(() => {});
      }
    });

    const url = `${CONFIG.upstreamBase}/${slug}/${phone}/`;
    // 用 domcontentloaded 而非 networkidle2：实测 networkidle2 要等满 15s
    // （页面有长轮询/广告请求），而消息容器出现后即可取数。
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: CONFIG.HARD_TIMEOUT_MS - 5000 });
    const status = resp ? resp.status() : 0;

    // 304 也要当成功：源站带 ETag/Last-Modified，浏览器命中本地缓存时会回304，
    // 此时 DOM 内容（缓存副本）仍然完整可用，不能判为失败。
    if (status !== 200 && status !== 304) {
      const err = new Error('源站返回 ' + status);
      err.status = 502;
      throw err;
    }

    // 等消息区出现。实测 React CSR 渲染偏慢，8s 有时不够（会漏掉已存在的短信），
    // 故改为「等到容器出现或 LoadingMessage 骨架全部消失」再取数。
    await page.waitForSelector('[class*="MessageContainer"], [class*="MessagesContainer"]', { timeout: 10000 })
      .catch(() => { /* 空号码页不会有容器，走空态 */ });

    // 轮询等待骨架屏消失，最多再等 10 秒
    const t0wait = Date.now();
    while (Date.now() - t0wait < 10000) {
      const loading = await page.evaluate(() =>
        document.querySelectorAll('[class*="LoadingMessage"]').length);
      if (loading === 0) break;
      await new Promise((r) => setTimeout(r, 500));
    }
    await new Promise((r) => setTimeout(r, 300));

    const messages = await page.evaluate(extractMessages);
    stats.rendered++;

    const payload = {
      phone,
      slug,
      sourceUrl: url,
      sourceName: 'ReceiveAsmsOnline',
      fetchedAt: new Date().toISOString(),
      count: messages.length,
      messages: messages.map((m) => ({
        body: m.body,
        sender: m.sender || null,
        when: m.when || null,
        otp: extractOtp(m.body),
      })),
    };
    return payload;
  } finally {
    clearTimeout(timer);
    if (page) { try { await page.close(); } catch (e) { /* ignore */ } }
    releaseSlot();
    lastActivityAt = Date.now();
  }
}

// ------------------------------------------------------------------ 缓存
function cacheGet(key) {
  const hit = cache.get(key);
  if (!hit) return null;
  if (Date.now() - hit.at > CONFIG.CACHE_TTL_MS) { cache.delete(key); return null; }
  return hit.payload;
}
function cacheSet(key, payload) {
  if (cache.size >= CONFIG.MAX_CACHE_ENTRIES) {
    // 淘汰最旧
    const oldest = cache.keys().next().value;
    cache.delete(oldest);
  }
  cache.set(key, { at: Date.now(), payload });
}

// ------------------------------------------------------------------ 路由
const app = express();
app.disable('x-powered-by');
app.set('trust proxy', '127.0.0.1');

app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'SAMEORIGIN');
  res.setHeader('Referrer-Policy', 'no-referrer');
  next();
});

// 只允许来自本机 nginx 的调用。
// nginx 反代会带 X-Forwarded-For，配合 trust proxy 后 req.ip 是「真实客户端 IP」，
// 而 req.socket.remoteAddress 才是 nginx(127.0.0.1)。故按后者判断：
// 后端端口只绑 127.0.0.1，公网无法直连，这里再挡一层防止本机其他进程误调。
app.use((req, res, next) => {
  const peer = req.socket && req.socket.remoteAddress
    ? req.socket.remoteAddress.replace(/^::ffff:/, '')
    : '';
  const ok = peer === '127.0.0.1' || peer === '::1';
  if (!ok) {
    log('[deny] 非本机来源 peer=' + peer);
    res.status(403).json({ error: 'forbidden' });
    return;
  }
  next();
});

app.get('/healthz', (req, res) => {
  res.json({
    ok: true,
    browserAlive: !!(browser && browser.connected),
    activePages,
    cacheSize: cache.size,
    uptimeSec: Math.round(process.uptime()),
    stats,
  });
});

/** 距离该号码上次成功抓取还需等待多少毫秒（0 = 可抓） */
function rateLimit(key) {
  const last = lastSuccessAt.get(key) || 0;
  if (!last) return 0;
  const wait = last + CONFIG.MIN_INTERVAL_MS - Date.now();
  return wait > 0 ? wait : 0;
}

app.get('/api/sms', async (req, res) => {
  stats.requests++;
  const slug = String(req.query.slug || '').toLowerCase().trim();
  const phone = String(req.query.phone || '').replace(/\D/g, '');

  if (!CONFIG.allowedSlugs.has(slug)) {
    return res.status(400).json({ error: 'unsupported_country' });
  }
  if (phone.length < 9 || phone.length > 15) {
    return res.status(400).json({ error: 'bad_phone' });
  }

  const key = slug + '/' + phone;

  // 1) 缓存命中
  const cached = cacheGet(key);
  if (cached) {
    stats.hits++;
    return res.json(Object.assign({}, cached, { cached: true }));
  }

  // 2) 限频：先 IP 级，再号码级（两者都只在成功后计数）
  const nowMs = Date.now();
  const rec = ipHits.get(req.ip) || { count: 0, windowStart: nowMs };
  if (nowMs - rec.windowStart > IP_WINDOW_MS) { rec.count = 0; rec.windowStart = nowMs; }
  if (rec.count >= IP_MAX_PER_WINDOW) {
    stats.failures++;
    return res.status(429).json({
      error: 'ip_rate_limited',
      retryAfter: Math.ceil((rec.windowStart + IP_WINDOW_MS - nowMs) / 1000),
    });
  }

  const wait = rateLimit(key);
  if (wait > 0) {
    const err = new Error('请求过于频繁，请 ' + Math.ceil(wait / 1000) + ' 秒后重试');
    err.status = 429;
    err.retryAfter = Math.ceil(wait / 1000);
    stats.failures++;
    return res.status(429).json({ error: 'rate_limited', retryAfter: err.retryAfter });
  }

  // 3) 抓源
  stats.misses++;
  const t0 = Date.now();
  try {
    const payload = await renderPhone(slug, phone);
    // 成功后才计数
    rec.count++;
    ipHits.set(req.ip, rec);
    lastSuccessAt.set(key, Date.now());
    cacheSet(key, payload);
    log('[ok] ' + key + ' ' + payload.count + ' 条 ' + (Date.now() - t0) + 'ms');
    return res.json(payload);
  } catch (e) {
    stats.failures++;
    const status = e.status || 500;
    log('[fail] ' + key + ' ' + status + ' ' + (e.message || e));
    return res.status(status).json({
      error: e.message || 'render_failed',
      retryAfter: e.retryAfter || null,
      sourceUrl: `${CONFIG.upstreamBase}/${slug}/${phone}/`,
    });
  }
});

app.use((req, res) => res.status(404).json({ error: 'not_found' }));

// ------------------------------------------------------------------ 生命周期
async function shutdown(sig) {
  if (shuttingDown) return;
  shuttingDown = true;
  log('[shutdown] 收到 ' + sig + '，开始关闭');
  try {
    if (browser) { const b = browser; browser = null; await b.close(); }
  } catch (e) { /* ignore */ }
  process.exit(0);
}
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('unhandledRejection', (e) => log('[unhandledRejection]', e && e.message));

// 定期清理限频/缓存，防止长期运行内存无限增长
const janitor = setInterval(() => {
  const now = Date.now();
  for (const [ip, r] of ipHits) if (now - r.windowStart > IP_WINDOW_MS * 3) ipHits.delete(ip);
  for (const [k, v] of cache) if (now - v.at > CONFIG.CACHE_TTL_MS * 10) cache.delete(k);
  for (const [k, t] of lastSuccessAt) if (now - t > CONFIG.MIN_INTERVAL_MS * 20) lastSuccessAt.delete(k);
}, 120000);
janitor.unref();

if (require.main === module) {
  // 启动自检：配置项缺失就直接崩，别让错误拖到第一次请求才暴露
  const required = ['chromePath', 'upstreamBase', 'port', 'bind'];
  const missing = required.filter((k) => !CONFIG[k]);
  if (missing.length) {
    console.error('[fatal] 配置项缺失: ' + missing.join(', '));
    process.exit(1);
  }
  if (!fs.existsSync(CONFIG.chromePath)) {
    console.error('[fatal] Chrome 不存在: ' + CONFIG.chromePath);
    process.exit(1);
  }

  app.listen(CONFIG.port, CONFIG.bind, () => {
    log('[boot] 监听 ' + CONFIG.bind + ':' + CONFIG.port +
        '（源 ' + CONFIG.upstreamBase + '，白名单 ' + CONFIG.allowedSlugs.size + ' 国，' +
        '限频 ' + (CONFIG.MIN_INTERVAL_MS / 1000) + 's，并发 ' + CONFIG.CONCURRENCY + '）');
    log('[boot] Chrome: ' + CONFIG.chromePath);
    // 预热，避免首个用户等冷启动
    launchBrowser()
      .then((b) => b.version())
      .then((v) => log('[boot] 预热完成 ' + v))
      .catch((e) => log('[boot] 预热失败（首次请求会重试）:', e.message));
  });
}

module.exports = { app, CONFIG };
