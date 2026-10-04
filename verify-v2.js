/**
 * V2 首页验收：按设计方案第 10 节验收清单逐项检查
 */
const puppeteer = require('puppeteer-core');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const ROOT = path.join(__dirname, 'web');
const MIME = { '.html': 'text/html; charset=utf-8', '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.css': 'text/css', '.js': 'text/javascript' };

const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/') p = '/index.html';
  const fp = path.join(ROOT, p);
  if (!fp.startsWith(ROOT) || !fs.existsSync(fp) || fs.statSync(fp).isDirectory()) { res.writeHead(404); return res.end('nf'); }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(fp)] || 'application/octet-stream' });
  fs.createReadStream(fp).pipe(res);
});

const VIEWPORTS = [
  { name: '1440', w: 1440, h: 1200 },
  { name: '1024', w: 1024, h: 1100 },
  { name: '768',  w: 768,  h: 1000 },
  { name: '390',  w: 390,  h: 844, mobile: true },
  { name: '360',  w: 360,  h: 780, mobile: true },
];

(async () => {
  await new Promise(r => server.listen(8901, '127.0.0.1', r));
  const URL = 'http://127.0.0.1:8901/';
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });

  const problems = [];

  for (const vp of VIEWPORTS) {
    const page = await browser.newPage();
    const errs = [];
    page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
    page.on('response', r => { if (r.status() >= 400) errs.push('HTTP' + r.status() + ' ' + r.url()); });
    await page.setViewport({ width: vp.w, height: vp.h, deviceScaleFactor: 1 });
    await page.goto(URL, { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise(r => setTimeout(r, 900));

    const m = await page.evaluate(() => {
      const grid = document.getElementById('grid');
      const de = document.documentElement;
      // 检查触控目标尺寸
      const small = [];
      document.querySelectorAll('button,select,a.go,input').forEach(el => {
        const b = el.getBoundingClientRect();
        if (b.width > 0 && b.height > 0 && b.height < 44 && !el.closest('.chips,.card-meta,.foot')) {
          small.push((el.id || el.className || el.tagName) + ':' + Math.round(b.height));
        }
      });
      return {
        overflowX: de.scrollWidth > window.innerWidth + 1,
        scrollW: de.scrollWidth, winW: window.innerWidth,
        cards: document.querySelectorAll('.card').length,
        gridCols: getComputedStyle(grid).gridTemplateColumns.split(' ').length,
        countries: document.querySelectorAll('.ctry').length,
        sources: document.querySelectorAll('.src').length,
        stats: document.getElementById('stats').textContent.replace(/\s+/g, ' ').trim(),
        matchCnt: document.getElementById('matchCnt').textContent,
        h1: getComputedStyle(document.querySelector('h1')).fontSize,
        // 关键：不得出现无依据的「在线」字样
        fakeOnline: document.body.innerText.includes('在线'),
        verifiedBadge: document.body.innerText.includes('已验证'),
        smallTargets: small.slice(0, 6),
      };
    });

    const issues = [];
    if (m.overflowX) issues.push(`页面级横向溢出 ${m.scrollW}>${m.winW}`);
    if (m.cards !== 94) issues.push('卡片数=' + m.cards);
    if (m.fakeOnline) issues.push('出现「在线」字样（无核验依据）');
    if (m.verifiedBadge) issues.push('出现「已验证」字样');
    if (vp.mobile && m.gridCols !== 1) issues.push('移动端非单列: ' + m.gridCols);
    if (errs.length) issues.push('错误: ' + errs.join(' | '));

    console.log(`\n=== ${vp.name}px ===`);
    console.log(JSON.stringify(m));
    console.log(issues.length ? '  ⚠️ ' + issues.join('; ') : '  ✅ 通过');
    issues.forEach(i => problems.push(`${vp.name}px: ${i}`));

    await page.screenshot({ path: `D:/workspace/sms-hub/v2-${vp.name}.png`, fullPage: false });
    await page.close();
  }

  // ---- 交互测试（桌面 1440） ----
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1200 });
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 800));

  console.log('\n=== 交互测试 ===');

  // 搜索国家
  await page.type('#q', '瑞典');
  await new Promise(r => setTimeout(r, 450));
  let n = await page.evaluate(() => document.querySelectorAll('.card').length);
  console.log(`  搜索「瑞典」-> ${n} 张 ${n === 44 ? '✅' : '❌'}`);

  // 搜英文国家名
  await page.evaluate(() => { const q = document.getElementById('q'); q.value = 'Sweden'; q.dispatchEvent(new Event('input')); });
  await new Promise(r => setTimeout(r, 450));
  n = await page.evaluate(() => document.querySelectorAll('.card').length);
  console.log(`  搜索「Sweden」-> ${n} 张 ${n === 44 ? '✅' : '❌'}`);

  // 搜区号
  await page.evaluate(() => { const q = document.getElementById('q'); q.value = '358'; q.dispatchEvent(new Event('input')); });
  await new Promise(r => setTimeout(r, 450));
  n = await page.evaluate(() => document.querySelectorAll('.card').length);
  console.log(`  搜索区号「358」-> ${n} 张 ${n === 21 ? '✅' : '❌'}`);

  // 无匹配
  await page.evaluate(() => { const q = document.getElementById('q'); q.value = 'zzzz'; q.dispatchEvent(new Event('input')); });
  await new Promise(r => setTimeout(r, 450));
  const empty = await page.evaluate(() => ({
    shown: !!document.querySelector('#stateBox .state'),
    txt: document.querySelector('#stateBox h3')?.textContent,
    hasReset: !!document.querySelector('#resetAll'),
  }));
  console.log(`  无匹配 -> "${empty.txt}" +清除按钮=${empty.hasReset} ${empty.txt === '没有匹配的号码' && empty.hasReset ? '✅' : '❌'}`);

  // 清除
  await page.click('#resetAll');
  await new Promise(r => setTimeout(r, 400));
  n = await page.evaluate(() => document.querySelectorAll('.card').length);
  console.log(`  清除筛选 -> ${n} 张 ${n === 94 ? '✅' : '❌'}`);

  // 国家快捷筛选 + aria-pressed + 再次点击取消
  await page.click('.ctry');
  await new Promise(r => setTimeout(r, 400));
  let s = await page.evaluate(() => ({
    pressed: document.querySelector('.ctry').getAttribute('aria-pressed'),
    sel: document.getElementById('f-country').value,
    chips: document.querySelectorAll('.chip').length,
    n: document.querySelectorAll('.card').length,
  }));
  console.log(`  点国家 -> pressed=${s.pressed} 下拉同步=${s.sel||'(空)'} chips=${s.chips} 共${s.n}张 ${s.pressed === 'true' && s.chips === 1 ? '✅' : '❌'}`);

  await page.click('.ctry');
  await new Promise(r => setTimeout(r, 400));
  s = await page.evaluate(() => ({ pressed: document.querySelector('.ctry').getAttribute('aria-pressed'), n: document.querySelectorAll('.card').length }));
  console.log(`  再点取消 -> pressed=${s.pressed} 共${s.n}张 ${s.pressed === 'false' && s.n === 94 ? '✅' : '❌'}`);

  // 组合筛选：国家 + 状态
  await page.select('#f-status', 'unknown');
  await new Promise(r => setTimeout(r, 400));
  s = await page.evaluate(() => ({ n: document.querySelectorAll('.card').length, chips: document.querySelectorAll('.chip').length }));
  console.log(`  状态=状态未知 -> ${s.n}张 chips=${s.chips} ${s.n === 22 ? '✅' : '❌'}`);

  // 排序
  await page.select('#f-status', '');
  await page.select('#f-sort', 'sms');
  await new Promise(r => setTimeout(r, 400));
  const top = await page.evaluate(() => {
    const c = [...document.querySelectorAll('.card')].slice(0, 3);
    return c.map(x => ({
      phone: x.querySelector('.num').textContent,
      sms: x.querySelector('.card-meta span').textContent,
    }));
  });
  console.log('  按短信数排序 top3:', JSON.stringify(top));
  const desc = top.map(t => parseInt(t.sms.replace(/[^\d]/g, '')) || 0);
  console.log(`  排序递减 ${desc[0] >= desc[1] && desc[1] >= desc[2] ? '✅' : '❌'}`);

  // 完整号码 + 外链
  const link = await page.evaluate(() => {
    const a = document.querySelector('.card .go');
    return { href: a.href, target: a.target, rel: a.rel, phone: document.querySelector('.card .num').textContent };
  });
  console.log(`  号码=${link.phone} 外链=${link.href.slice(0, 52)}... target=${link.target} rel=${link.rel} ${link.target === '_blank' && link.rel.includes('noopener') ? '✅' : '❌'}`);

  // 号码是否完整（无掩码）
  const masked = await page.evaluate(() => {
    return [...document.querySelectorAll('.card .num')].filter(x => /\*{2,}|\.{3,}/.test(x.textContent)).length;
  });
  console.log(`  含掩码号码数=${masked} ${masked === 0 ? '✅' : '❌'}`);

  // 刷新不触发重复采集
  await page.click('#refresh');
  await new Promise(r => setTimeout(r, 1500));
  const after = await page.evaluate(() => ({
    n: document.querySelectorAll('.card').length,
    btn: document.getElementById('refresh').textContent.trim(),
  }));
  console.log(`  刷新后 -> ${after.n}张 按钮="${after.btn}" ${after.n === 94 && after.btn.includes('刷新') ? '✅' : '❌'}`);

  // 移动端筛选面板
  await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
  await page.reload({ waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 800));
  await page.click('#openSheet');
  await new Promise(r => setTimeout(r, 400));
  let sh = await page.evaluate(() => ({
    open: document.getElementById('sheet').classList.contains('on'),
    mask: document.getElementById('mask').classList.contains('on'),
  }));
  console.log(`  移动端筛选面板打开=${sh.open} 遮罩=${sh.mask} ${sh.open && sh.mask ? '✅' : '❌'}`);

  // 临时选择不立即生效
  await page.select('#s-country', 'SE');
  await new Promise(r => setTimeout(r, 250));
  let before = await page.evaluate(() => document.querySelectorAll('.card').length);
  await page.click('#sheetApply');
  await new Promise(r => setTimeout(r, 450));
  let after2 = await page.evaluate(() => ({
    n: document.querySelectorAll('.card').length,
    closed: !document.getElementById('sheet').classList.contains('on'),
    sel: document.getElementById('f-country').value,
  }));
  console.log(`  面板选瑞典:选择时${before}张(应94) 应用后${after2.n}张 关闭=${after2.closed} ${after2.n === 44 && after2.closed ? '✅' : '❌'}`);

  // Esc 关闭
  await page.click('#openSheet');
  await new Promise(r => setTimeout(r, 350));
  await page.keyboard.press('Escape');
  await new Promise(r => setTimeout(r, 350));
  sh = await page.evaluate(() => !document.getElementById('sheet').classList.contains('on'));
  console.log(`  Esc 关闭面板=${sh} ${sh ? '✅' : '❌'}`);

  await page.screenshot({ path: 'D:/workspace/sms-hub/v2-mobile-filter.png' });
  await page.close();

  console.log('\n=== 汇总 ===');
  console.log(problems.length ? '发现问题:\n  ' + problems.join('\n  ') : '全部视口通过 ✅');
  await browser.close();
  server.close();
})();
