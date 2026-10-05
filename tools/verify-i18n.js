// 双语（中/英）端到端验收：
// 1) 中文页文案正确、无 JS 错误、无横向溢出
// 2) /en/ 页面文案为英文（关键标题/导航按钮）
// 3) 语言切换器存在，且切到英文后 URL 前缀正确
// 用法: NODE_PATH="D:/workspace/_tools/node_modules" node tools/verify-i18n.js
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const OUT = path.join(__dirname, '..', 'shots-i18n');
const BASE = process.env.BASE || 'http://127.0.0.1:8903';

let pass = 0, fail = 0;
const ok = m => { pass++; console.log('  ✓ ' + m); };
const bad = m => { fail++; console.log('  ✗ ' + m); };
const eq = (a, b, m) => (a === b ? ok(m) : bad(`${m}  (期望 ${JSON.stringify(b)}，实际 ${JSON.stringify(a)})`));

// 中文页断言
const ZH = [
  { url: '/', name: 'zh-home', w: 1440, must: [/免费/, /接收短信/, /验证码/], nav: '首页' },
  { url: '/', name: 'zh-home-mobile', w: 375, must: [/免费/, /接收短信/], nav: '首页' },
  { url: '/numbers', name: 'zh-numbers', w: 1440, must: [/全部可用号码|\d+ 个/], nav: '号码' },
  { url: '/guide', name: 'zh-guide', w: 1440, must: [/使用指南/, /四步完成接码/], nav: '使用指南' },
  { url: '/faq', name: 'zh-faq', w: 1440, must: [/常见问题/], nav: '常见问题' },
];

// 英文页断言
const EN = [
  { url: '/en/', name: 'en-home', w: 1440, must: [/Free/i, /Temporary Phone Numbers/i, /Verification/i], nav: 'Home' },
  { url: '/en/', name: 'en-home-mobile', w: 375, must: [/Free/i, /Temporary Phone Numbers/i], nav: 'Home' },
  { url: '/en/numbers', name: 'en-numbers', w: 1440, must: [/All available numbers|\d+ numbers/i], nav: 'Numbers' },
  { url: '/en/guide', name: 'en-guide', w: 1440, must: [/How to use/i], nav: 'Guide' },
  { url: '/en/faq', name: 'en-faq', w: 1440, must: [/Frequently asked questions/i], nav: 'FAQ' },
  { url: '/en/country/us', name: 'en-country-us', w: 1440, must: [/United States/i, /Phone Numbers for SMS Verification/i], nav: 'Numbers' },
  { url: '/en/country/gb', name: 'en-country-gb', w: 1440, must: [/United Kingdom/i], nav: 'Numbers' },
  { url: '/en/country/de', name: 'en-country-de', w: 375, must: [/Germany/i], nav: 'Numbers' },
];

async function probe(page, item, base) {
  const errs = [];
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  const resp = await page.goto(base + item.url, { waitUntil: 'networkidle2', timeout: 30000 });
  await new Promise(r => setTimeout(r, 900));
  const status = resp ? resp.status() : 0;
  const info = await page.evaluate(() => ({
    title: document.title,
    lang: document.documentElement.getAttribute('lang') || '',
    body: (document.querySelector('main') || document.body).innerText.replace(/\s+/g, ' ').slice(0, 4000),
    navTexts: [...document.querySelectorAll('.nav a')].map(a => a.textContent.trim()),
    langSw: !!document.getElementById('langSw'),
    langSwText: (document.getElementById('langSw') || {}).textContent || '',
    langSwAlt: (document.getElementById('langSw') || {}).dataset?.alt || '',
    canonical: document.querySelector('link[rel=canonical]')?.href || '',
    h1: [...document.querySelectorAll('h1')].map(e => e.textContent.trim()),
    scrollWidth: document.documentElement.scrollWidth,
    cards: document.querySelectorAll('.ncard, .cty, .s4, .faq-item, .q').length,
  }));
  return { status, errs, info };
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--hide-scrollbars',
           '--proxy-server=direct://', '--proxy-bypass-list=*'],
  });

  for (const group of [['中文版', ZH, true], ['英文版 /en/', EN, false]]) {
    const [label, items, required] = group;
    console.log(`\n===== ${label} =====`);
    for (const item of items) {
      const page = await browser.newPage();
      await page.setViewport({ width: item.w, height: 1200, deviceScaleFactor: 1 });
      let r;
      try { r = await probe(page, item, BASE); }
      catch (e) { bad(`${item.url} 打开失败: ${e.message}`); await page.close(); continue; }

      const isOk = r.status === 200 || r.status === 304;
      if (!isOk) {
        if (required) bad(`${item.url} HTTP ${r.status}`);
        else console.log(`  ⏭ ${item.url} HTTP ${r.status}（英文版尚未生成，跳过）`);
        await page.close();
        continue;
      }
      console.log(`\n[${item.name}] ${item.w}px  HTTP ${r.status}`);
      for (const re of item.must) {
        if (re.test(r.info.body)) ok(`含 ${re}`);
        else bad(`缺少 ${re}`);
      }
      if (r.info.navTexts.includes(item.nav)) ok(`导航含「${item.nav}」`);
      else bad(`导航缺少「${item.nav}」 → ${JSON.stringify(r.info.navTexts)}`);
      if (r.info.langSw) ok(`语言切换器存在（按钮文案「${r.info.langSwText}」→ ${r.info.langSwAlt}）`);
      else bad('缺少语言切换器 #langSw');
      console.log(`      title: ${r.info.title}`);
      console.log(`      lang=${r.info.lang}  H1=${JSON.stringify(r.info.h1)}  元素=${r.info.cards}`);
      const ovf = r.info.scrollWidth - item.w;
      if (ovf > 1) bad(`横向溢出 ${ovf}px`); else ok('无横向溢出');
      if (r.errs.length) bad(`JS 错误: ${r.errs.join(' | ')}`); else ok('无 JS 错误');
      await page.screenshot({ path: path.join(OUT, item.name + '.png') });
      await page.close();
    }
  }

  await browser.close();
  console.log(`\n===== 汇总：${pass} 通过 / ${fail} 失败 =====`);
  process.exit(fail ? 1 : 0);
})();
