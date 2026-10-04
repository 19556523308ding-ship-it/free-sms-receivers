/** 线上站点真实浏览器验证 */
const puppeteer = require('puppeteer-core');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = process.env.TARGET || 'https://sms.jinzhai.icu/';

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--ignore-certificate-errors'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 1300 });

  const errs = [];
  page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  page.on('response', r => { if (r.status() >= 400) errs.push('HTTP' + r.status() + ' ' + r.url()); });

  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 40000 });
  await new Promise(r => setTimeout(r, 1500));

  const info = await page.evaluate(() => ({
    title: document.title,
    total: document.getElementById('s-total')?.textContent,
    country: document.getElementById('s-country')?.textContent,
    source: document.getElementById('s-source')?.textContent,
    time: document.getElementById('s-time')?.textContent,
    cards: document.querySelectorAll('.card').length,
    chips: document.querySelectorAll('#chips .chip').length,
    firstNum: document.querySelector('.card .num')?.textContent,
    firstLink: document.querySelector('.card .go')?.href,
    https: location.protocol,
  }));
  console.log('=== 线上实测 ===');
  console.log(JSON.stringify(info, null, 2));

  await page.screenshot({ path: 'D:/workspace/sms-hub/shot-online.png' });

  // 交互复测
  await page.type('#q', '美国');
  await new Promise(r => setTimeout(r, 500));
  console.log('搜索"美国" ->', await page.evaluate(() => document.querySelectorAll('.card').length), '张');

  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2 });
  await page.reload({ waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 1200));
  const mob = await page.evaluate(() => ({
    cards: document.querySelectorAll('.card').length,
    overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
  }));
  console.log('移动端 390px ->', JSON.stringify(mob));
  await page.screenshot({ path: 'D:/workspace/sms-hub/shot-online-mobile.png' });

  console.log('\n=== 错误 ===');
  console.log(errs.length ? errs.join('\n') : '无');
  await browser.close();
})();
