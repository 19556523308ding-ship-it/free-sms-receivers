// 国家静态页视觉验证：确认静态块与 JS 实时块不冲突、不重复
// 用法: NODE_PATH="D:/workspace/_tools/node_modules" node tools/shot-country.js
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const OUT = path.join(__dirname, '..', 'shots-v2');
const BASE = process.env.BASE || "http://127.0.0.1:8902";

const PAGES = [
  { url: '/country/us', name: 'country-us-desktop', w: 1440, h: 1400 },
  { url: '/country/us', name: 'country-us-mobile', w: 375, h: 1200 },
  { url: '/country/gb', name: 'country-gb-desktop', w: 1440, h: 1400 },
  { url: '/404.html', name: '404-desktop', w: 1440, h: 900 },
];

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--hide-scrollbars'],
  });

  const report = [];
  for (const p of PAGES) {
    const page = await browser.newPage();
    await page.setViewport({ width: p.w, height: p.h, deviceScaleFactor: 1 });
    const msgs = [];
    page.on('console', m => { if (m.type() === 'error') msgs.push(m.text()); });
    page.on('pageerror', e => msgs.push('PAGEERROR: ' + e.message));

    await page.goto(BASE + p.url, { waitUntil: 'networkidle2', timeout: 30000 });
    await new Promise(r => setTimeout(r, 900));

    const info = await page.evaluate(() => {
      const h1 = [...document.querySelectorAll('h1')].map(e => e.textContent.trim());
      const h2 = [...document.querySelectorAll('h2')].map(e => e.textContent.trim());
      const cstatic = document.querySelector('.cstatic');
      const cpHead = document.querySelector('#cpHead');
      return {
        title: document.title,
        canonical: document.querySelector('link[rel=canonical]')?.href || '',
        h1, h2: h2.slice(0, 8),
        scrollWidth: document.documentElement.scrollWidth,
        cstaticText: cstatic ? cstatic.innerText.replace(/\s+/g, ' ').slice(0, 160) : '(无)',
        cpHeadText: cpHead ? cpHead.innerText.replace(/\s+/g, ' ').slice(0, 160) : '(无)',
        cards: document.querySelectorAll('.ncard, .sp-num').length,
      };
    });

    await page.screenshot({ path: path.join(OUT, p.name + '.png'), fullPage: false });
    // 额外的滚动截图：抓静态块区域
    await page.evaluate(() => {
      const el = document.querySelector('.cstatic');
      if (el) el.scrollIntoView({ block: 'start' });
    });
    await new Promise(r => setTimeout(r, 500));
    await page.screenshot({ path: path.join(OUT, p.name + '-static.png'), fullPage: false });

    report.push({ ...p, ...info, errors: msgs });
    await page.close();
  }

  await browser.close();

  console.log('\n=== 国家静态页视觉验证 ===\n');
  for (const r of report) {
    const overflow = r.scrollWidth > r.w ? `  ⚠ 横向溢出 ${r.scrollWidth - r.w}px` : '  ✓ 无溢出';
    console.log(`[${r.name}] ${r.w}px`);
    console.log(`  title     : ${r.title}`);
    console.log(`  canonical : ${r.canonical}`);
    console.log(`  H1 数量   : ${r.h1.length}  ${JSON.stringify(r.h1)}`);
    console.log(`  H2        : ${JSON.stringify(r.h2)}`);
    console.log(`  元素数    : ${r.cards}`);
    console.log(`  滚动宽度  : ${r.scrollWidth}${overflow}`);
    console.log(`  静态块    : ${r.cstaticText}`);
    console.log(`  实时块    : ${r.cpHeadText}`);
    if (r.errors.length) console.log(`  ✗ JS 错误 : ${r.errors.join(' | ')}`);
    console.log('');
  }
})();
