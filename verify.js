/**
 * 真实浏览器验证：渲染截图 + 断言关键元素
 * 自带静态服务器，避免跨进程后台服务不存活的问题
 */
const puppeteer = require('puppeteer-core');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const ROOT = path.join(__dirname, 'web');
const MIME = { '.html': 'text/html; charset=utf-8', '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.webp': 'image/webp', '.css': 'text/css', '.js': 'text/javascript' };

const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/') p = '/index.html';
  const fp = path.join(ROOT, p);
  if (!fp.startsWith(ROOT) || !fs.existsSync(fp) || fs.statSync(fp).isDirectory()) {
    res.writeHead(404); return res.end('not found');
  }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(fp)] || 'application/octet-stream' });
  fs.createReadStream(fp).pipe(res);
});

(async () => {
  await new Promise(r => server.listen(8899, '127.0.0.1', r));
  const URL = 'http://127.0.0.1:8899/';
  console.log('静态服务器已启动:', URL);

  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 1400, deviceScaleFactor: 1 });

  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push('CONSOLE: ' + m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
  page.on('requestfailed', r => errors.push('REQFAIL: ' + r.url() + ' ' + (r.failure()?.errorText || '')));
  page.on('response', r => { if (r.status() >= 400) errors.push('HTTP' + r.status() + ': ' + r.url()); });

  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 30000 });
  await new Promise(r => setTimeout(r, 1200));

  const stats = await page.evaluate(() => ({
    total: document.getElementById('s-total')?.textContent,
    country: document.getElementById('s-country')?.textContent,
    source: document.getElementById('s-source')?.textContent,
    time: document.getElementById('s-time')?.textContent,
    cards: document.querySelectorAll('.num').length,
    chips: document.querySelectorAll('#chips .chip').length,
    firstCard: document.querySelector('.num .num-val')?.textContent,
    firstGo: document.querySelector('.num .go')?.getAttribute('href'),
    emptyShown: document.getElementById('empty')?.style.display,
  }));

  console.log('=== 首屏断言 ===');
  console.log(JSON.stringify(stats, null, 2));

  await page.screenshot({ path: 'D:/workspace/sms-hub/shot-desktop.png', fullPage: false });

  // 测试搜索
  await page.type('#q', '瑞典');
  await new Promise(r => setTimeout(r, 500));
  const afterSearch = await page.evaluate(() => document.querySelectorAll('.num').length);
  console.log('搜索"瑞典" -> 卡片数:', afterSearch);
  await page.screenshot({ path: 'D:/workspace/sms-hub/shot-search.png' });

  // 清空 + 国家 chip
  await page.evaluate(() => { document.getElementById('q').value = ''; document.getElementById('q').dispatchEvent(new Event('input')); });
  await new Promise(r => setTimeout(r, 400));
  const chips = await page.$$('#chips .chip');
  if (chips.length > 3) { await chips[3].click(); await new Promise(r => setTimeout(r, 500)); }
  const afterChip = await page.evaluate(() => ({
    n: document.querySelectorAll('.num').length,
    country: document.getElementById('f-country').value,
  }));
  console.log('点击国家 chip ->', JSON.stringify(afterChip));

  // 移动端
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2 });
  await page.reload({ waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 1000));
  const mob = await page.evaluate(() => {
    const g = document.getElementById('grid');
    return {
      cards: document.querySelectorAll('.num').length,
      gridCols: getComputedStyle(g).gridTemplateColumns.split(' ').length,
      overflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
      scrollW: document.documentElement.scrollWidth,
      winW: window.innerWidth,
    };
  });
  console.log('=== 移动端 390px ===');
  console.log(JSON.stringify(mob));
  await page.screenshot({ path: 'D:/workspace/sms-hub/shot-mobile.png', fullPage: false });

  console.log('\n=== JS/网络错误 ===');
  console.log(errors.length ? errors.join('\n') : '无');

  await browser.close();
  server.close();
})();
