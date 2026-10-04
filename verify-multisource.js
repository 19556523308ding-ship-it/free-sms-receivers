/**
 * 线上验收：sms.jinzhai.icu 多源改造后
 * 校验项：真实数据加载、9源渲染、号码量、筛选/搜索/排序/复制、E.164格式、无溢出、无控制台错误
 */
const puppeteer = require('puppeteer-core');

const SITE = 'https://sms.jinzhai.icu';
const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 390, height: 844 },
];

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
  });

  const page = await browser.newPage();
  const errors = [];
  const failedReq = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 160)); });
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + String(e.message).slice(0, 160)));
  page.on('requestfailed', (r) => failedReq.push(r.url().slice(0, 100) + ' :: ' + (r.failure() || {}).errorText));
  page.on('response', (r) => { if (r.status() >= 400) failedReq.push(r.status() + ' ' + r.url().slice(0, 100)); });

  await page.setViewport({ width: 1440, height: 900 });
  await page.goto(SITE + '/', { waitUntil: 'networkidle2', timeout: 45000 });
  await new Promise((r) => setTimeout(r, 2500));

  // ---- 1. 数据真实性 ----
  const stats = await page.evaluate(async () => {
    const r = await fetch('data/numbers.json?t=' + Date.now(), { cache: 'no-store' });
    const d = await r.json();
    const t = d.totals || {};
    return {
      records: t.records, unique: t.uniquePhones, countries: t.countries, sources: t.sources,
      srcRows: (d.sources || []).length,
      srcOk: (d.sources || []).filter((s) => s.ok).length,
      srcNames: (d.sources || []).map((s) => s.sourceName + (s.ok ? '' : '(失败)')),
    };
  });
  console.log('【1】数据层');
  console.log(`  记录 ${stats.records} / 唯一 ${stats.unique} / 国家 ${stats.countries} / 成功源 ${stats.srcOk}/${stats.srcRows}`);
  console.log(`  源: ${stats.srcNames.join(', ')}`);

  // ---- 2. 卡片渲染 ----
  const cards = await page.evaluate(() => {
    const list = document.querySelectorAll('.card');
    const out = { count: list.length, samples: [], badPhone: 0, noCta: 0, noSrc: 0 };
    list.forEach((c, i) => {
      const phone = ((c.querySelector('.card-phone') || {}).textContent || '').trim();
      const cta = c.querySelector('.go');
      if (!/^\+\d[\d\s]{7,}$/.test(phone)) out.badPhone++;
      if (!cta || !cta.getAttribute('href')) out.noCta++;
      if (!((c.querySelector('.card-src') || {}).textContent || '').trim()) out.noSrc++;
      if (i < 4) {
        out.samples.push({
          phone: phone.replace(/\s+/g, ' '),
          country: ((c.querySelector('.card-country') || {}).textContent || '').trim(),
          badge: ((c.querySelector('.badge') || {}).textContent || '').trim(),
          src: ((c.querySelector('.card-src') || {}).textContent || '').trim(),
          href: cta ? cta.getAttribute('href') : null,
        });
      }
    });
    return out;
  });
  console.log('\n【2】卡片渲染');
  console.log(`  渲染 ${cards.count} 张 | 号码格式异常 ${cards.badPhone} | 缺CTA ${cards.noCta} | 缺来源 ${cards.noSrc}`);
  cards.samples.forEach((s) => console.log(`    ${s.phone}  ${s.country}  [${s.badge}]  ${s.src}  → ${s.href ? s.href.slice(0, 46) : '无'}`));

  // ---- 3. 排序验证 ----
  const sortCheck = await page.evaluate(async () => {
    const sel = document.querySelector('#f-sort');
    if (!sel) return { err: '无排序控件' };
    const readTop = () => {
      const el = document.querySelector('.card .card-meta span');
      return el ? el.textContent.trim() : '';
    };
    const before = readTop();
    sel.value = 'count';
    sel.dispatchEvent(new Event('change'));
    await new Promise((r) => setTimeout(r, 500));
    const after = readTop();
    sel.value = '';
    sel.dispatchEvent(new Event('change'));
    return { before, after };
  });
  console.log('\n【3】排序');
  console.log(`  默认首位「${sortCheck.before}」 → 按短信数首位「${sortCheck.after}」`);

  // ---- 4. 搜索 ----
  const searchCheck = await page.evaluate(async () => {
    const q = document.querySelector('#q');
    if (!q) return { err: '无搜索框' };
    q.value = '+1';
    q.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise((r) => setTimeout(r, 700));
    const n = document.querySelectorAll('.card').length;
    const cnt = (document.querySelector('#matchCnt') || {}).textContent || '';
    q.value = '';
    q.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise((r) => setTimeout(r, 700));
    const total = document.querySelectorAll('.card').length;
    return { filtered: n, label: cnt.trim(), total };
  });
  console.log('\n【4】搜索');
  console.log(`  搜「+1」→ ${searchCheck.filtered} 张（文案「${searchCheck.label}」）| 清空后 ${searchCheck.total} 张`);

  // ---- 5. 源筛选 ----
  const filterCheck = await page.evaluate(async () => {
    const sel = document.querySelector('#f-source');
    if (!sel) return { err: '无源筛选' };
    const opts = Array.from(sel.options).map((o) => o.value).filter(Boolean);
    const pick = opts.find((v) => v === 'freephonenum') || opts[1];
    if (!pick) return { err: '无可选源' };
    sel.value = pick;
    sel.dispatchEvent(new Event('change'));
    await new Promise((r) => setTimeout(r, 600));
    const n = document.querySelectorAll('.card').length;
    const firstSrc = (document.querySelector('.card .srcname') || {}).textContent || '';
    sel.value = '';
    sel.dispatchEvent(new Event('change'));
    return { pick, n, firstSrc: firstSrc.trim(), optCount: opts.length };
  });
  console.log('\n【5】源筛选');
  console.log(`  可选源 ${filterCheck.optCount} 个 | 选「${filterCheck.pick}」→ ${filterCheck.n} 张（首条来源：${filterCheck.firstSrc}）`);

  // ---- 6. 响应式 ----
  console.log('\n【6】多视口溢出检查');
  for (const vp of VIEWPORTS) {
    await page.setViewport({ width: vp.width, height: vp.height });
    await new Promise((r) => setTimeout(r, 700));
    const o = await page.evaluate(() => ({
      sw: document.documentElement.scrollWidth,
      cw: document.documentElement.clientWidth,
      cards: document.querySelectorAll('.card').length,
    }));
    const overflow = o.sw - o.cw;
    console.log(`  ${vp.name.padEnd(8)} ${vp.width}px  卡片 ${o.cards}  横向溢出 ${overflow}px  ${overflow <= 1 ? '✅' : '❌'}`);
  }

  // ---- 7. 数据源页 ----
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto(SITE + '/sources.html', { waitUntil: 'networkidle2', timeout: 30000 });
  await new Promise((r) => setTimeout(r, 2000));
  const srcPage = await page.evaluate(() => {
    const cards = Array.from(document.querySelectorAll('.src'));
    return {
      count: cards.length,
      names: cards.map((c) => (c.querySelector('h3') || {}).textContent || '').filter(Boolean),
      // 说明块可能用 .note，也可能直接是文本；只要卡片文本够长即视为有说明
      detailed: cards.filter((c) => (c.innerText || '').length > 120).length,
      samples: cards.slice(0, 2).map((c) => (c.innerText || '').replace(/\s+/g, ' ').slice(0, 150)),
    };
  });
  console.log('\n【7】数据源页');
  console.log(`  ${srcPage.count} 个源卡片 | 含详细说明 ${srcPage.detailed} 个`);
  srcPage.samples.forEach((s) => console.log(`    ${s}`));

  // ---- 8. 截图 ----
  await page.goto(SITE + '/', { waitUntil: 'networkidle2' });
  await new Promise((r) => setTimeout(r, 2500));
  await page.setViewport({ width: 1440, height: 1100 });
  await page.screenshot({ path: '/tmp/shot-new-desktop.png' });
  await page.setViewport({ width: 390, height: 900 });
  await new Promise((r) => setTimeout(r, 800));
  await page.screenshot({ path: '/tmp/shot-new-mobile.png' });
  await page.goto(SITE + '/sources.html', { waitUntil: 'networkidle2' });
  await new Promise((r) => setTimeout(r, 2000));
  await page.setViewport({ width: 1440, height: 1100 });
  await page.screenshot({ path: '/tmp/shot-new-sources.png' });
  console.log('\n【8】截图已保存 /tmp/shot-new-*.png');

  console.log('\n【9】错误汇总');
  console.log(`  控制台错误 ${errors.length} 条`);
  errors.slice(0, 5).forEach((e) => console.log(`    ${e}`));
  const realFailed = failedReq.filter((u) => !/favicon|google|doubleclick/.test(u));
  console.log(`  失败请求 ${realFailed.length} 条`);
  realFailed.slice(0, 5).forEach((u) => console.log(`    ${u}`));

  await browser.close();
})();
