/**
 * 站内短信查看面板 —— 端到端真浏览器验收
 * 校验：按钮出现范围、面板打开、真实短信渲染、验证码高亮、复制、空态、
 *      限频提示、关闭、多视口无溢出、零控制台错误
 */
const puppeteer = require('puppeteer-core');
const SITE = 'https://sms.jinzhai.icu';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
  });
  const page = await browser.newPage();
  const errors = [], failed = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 150)); });
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + String(e.message).slice(0, 150)));
  page.on('response', (r) => {
    const u = r.url();
    if (r.status() >= 400 && u.startsWith(SITE)) failed.push(r.status() + ' ' + u.replace(SITE, '').slice(0, 70));
  });

  await page.setViewport({ width: 1440, height: 900 });
  await page.goto(SITE + '/', { waitUntil: 'networkidle2', timeout: 45000 });
  await sleep(2500);

  // ---- 1. 按钮出现范围 ----
  const btns = await page.evaluate(() => {
    const all = Array.from(document.querySelectorAll('.card'));
    const withBtn = all.filter((c) => c.querySelector('.inline-read'));
    const cards = withBtn.slice(0, 3).map((c) => ({
      src: ((c.querySelector('.card-src') || {}).textContent || '').trim(),
      country: ((c.querySelector('.card-country') || {}).textContent || '').trim(),
      phone: ((c.querySelector('.card-phone') || {}).textContent || '').replace(/\s+/g, ' ').trim(),
      slug: (c.querySelector('.inline-read') || {}).dataset ? c.querySelector('.inline-read').dataset.slug : null,
    }));
    return { totalCards: all.length, withBtn: withBtn.length, samples: cards };
  });
  console.log('【1】站内查看按钮范围');
  console.log(`  总卡片 ${btns.totalCards} | 带「站内查看」${btns.withBtn} 张（应等于 receiveasmsonline 的 364 张）`);
  btns.samples.forEach((c) => console.log(`    ${c.phone}  ${c.country}  slug=${c.slug}  src=${c.src}`));

  // ---- 2. 打开面板并等待真实短信 ----
  console.log('\n【2】打开面板（等待真实渲染，最长 40s）');
  await page.evaluate(() => {
    const cards = Array.from(document.querySelectorAll('.card'));
    const target = cards.find((c) => c.querySelector('.inline-read'));
    target.scrollIntoView({ block: 'center' });
    target.querySelector('.inline-read').click();
  });
  await sleep(1200);
  const opening = await page.evaluate(() => {
    const p = document.querySelector('#reader');
    return {
      visible: p && !p.hidden,
      sub: (document.querySelector('#readerSub') || {}).textContent || '',
      src: (document.querySelector('#readerSrc') || {}).href || '',
      loading: !!document.querySelector('.reader-load'),
    };
  });
  console.log(`  面板可见: ${opening.visible ? '✅' : '❌'} | 标题「${opening.sub}」`);
  console.log(`  原站链接: ${opening.src}`);

  let panel = null;
  for (let i = 0; i < 20; i++) {
    await sleep(2000);
    panel = await page.evaluate(() => {
      const msgs = Array.from(document.querySelectorAll('.msg'));
      return {
        count: msgs.length,
        loading: !!document.querySelector('.reader-load'),
        err: (document.querySelector('.reader-err') || {}).textContent || '',
        empty: (document.querySelector('.reader-empty') || {}).textContent || '',
        note: (document.querySelector('#readerNote') || {}).textContent || '',
        items: msgs.slice(0, 4).map((m) => ({
          from: ((m.querySelector('.msg-from') || {}).textContent || '').trim(),
          time: ((m.querySelector('.msg-time') || {}).textContent || '').trim(),
          body: ((m.querySelector('.msg-body') || {}).textContent || '').trim().slice(0, 72),
          otp: ((m.querySelector('.otp-val') || {}).textContent || '').trim(),
        })),
      };
    });
    if (panel.count > 0 || panel.err || panel.empty) break;
  }
  console.log(`  渲染 ${panel.count} 条 | 状态「${panel.note}」`);
  if (panel.err) console.log(`  ❌ 错误: ${panel.err.trim().slice(0, 120)}`);
  if (panel.empty) console.log(`  ℹ 空态: ${panel.empty.trim().slice(0, 100)}`);
  panel.items.forEach((m) => console.log(`    ▸ [${m.time}] ${m.from || '-'} ${m.otp ? 'OTP=' + m.otp : ''}\n      ${m.body}`));

  // ---- 3. 验证码复制 ----
  const cp = await page.evaluate(async () => {
    const b = document.querySelector('.otp-cp');
    if (!b) return { ok: false, why: '无复制按钮' };
    const otp = b.dataset.otp;
    b.click();
    await new Promise((r) => setTimeout(r, 400));
    return { ok: true, otp, label: b.textContent.trim() };
  });
  console.log('\n【3】验证码复制');
  console.log(cp.ok ? `  复制「${cp.otp}」→ 按钮变为「${cp.label}」` : `  ${cp.why}`);

  // ---- 4. 限频提示（立刻点关闭再开）----
  console.log('\n【4】限频与错误提示');
  const guard = await page.evaluate(() => {
    const tip = (document.querySelector('.reader-tip') || {}).textContent || '';
    const hasSrc = !!((document.querySelector('#readerSrc') || {}).href || '').startsWith('https://receiveasmsonline.com/');
    return { tipLen: tip.length, hasSrc, note: (document.querySelector('#readerNote') || {}).textContent };
  });
  console.log(`  合规提示: ${guard.tipLen > 20 ? '✅ 有' : '❌ 无'} | 原站链接正确: ${guard.hasSrc ? '✅' : '❌'}`);

  // ---- 5. 关闭 ----
  await page.evaluate(() => document.querySelector('#readerClose').click());
  await sleep(500);
  const closed = await page.evaluate(() => ({
    hidden: document.querySelector('#reader').hidden,
    maskHidden: document.querySelector('#readerMask').hidden,
    bodyOverflow: document.body.style.overflow,
  }));
  console.log('\n【5】关闭');
  console.log(`  面板隐藏 ${closed.hidden ? '✅' : '❌'} | 遮罩隐藏 ${closed.maskHidden ? '✅' : '❌'} | body 滚动已恢复 ${closed.bodyOverflow === '' ? '✅' : '❌ ' + closed.bodyOverflow}`);

  // ---- 6. 多视口面板溢出 ----
  console.log('\n【6】面板多视口');
  for (const vp of [{ n: 'desktop', w: 1440, h: 900 }, { n: 'tablet', w: 768, h: 1024 }, { n: 'mobile', w: 390, h: 844 }, { n: 'small', w: 360, h: 740 }]) {
    await page.setViewport({ width: vp.w, height: vp.h });
    await sleep(500);
    await page.evaluate(() => {
      const c = Array.from(document.querySelectorAll('.card'));
      const t = c.find((x) => x.querySelector('.inline-read'));
      t.scrollIntoView({ block: 'center' });
      t.querySelector('.inline-read').click();
    });
    await sleep(3500);
    const o = await page.evaluate(() => {
      const p = document.querySelector('#reader');
      const r = p.getBoundingClientRect();
      return {
        sw: document.documentElement.scrollWidth,
        cw: document.documentElement.clientWidth,
        inView: r.top < window.innerHeight && r.bottom > 0,
        w: Math.round(r.width), h: Math.round(r.height),
        overflowY: p.querySelector('.reader-body').scrollHeight > p.querySelector('.reader-body').clientHeight,
      };
    });
    const ok = o.sw - o.cw <= 1 && o.inView;
    console.log(`  ${vp.n.padEnd(8)} ${vp.w}px  面板 ${o.w}x${o.h}  页面横向溢出 ${o.sw - o.cw}px  可见 ${o.inView ? '✅' : '❌'}  ${ok ? '' : '❌'}`);
    if (vp.n !== 'small') {
      await page.screenshot({ path: `/tmp/panel-${vp.n}.png` });
    }
    await page.evaluate(() => document.querySelector('#readerClose').click());
    await sleep(400);
  }
  await page.setViewport({ width: 390, height: 844 });
  await sleep(600);
  await page.evaluate(() => {
    const c = Array.from(document.querySelectorAll('.card'));
    const t = c.find((x) => x.querySelector('.inline-read'));
    t.scrollIntoView({ block: 'center' });
    t.querySelector('.inline-read').click();
  });
  await sleep(4000);
  await page.screenshot({ path: '/tmp/panel-small.png' });

  // ---- 7. 首页整体溢出 ----
  await page.setViewport({ width: 1440, height: 900 });
  await page.evaluate(() => document.querySelector('#readerClose').click());
  await sleep(500);
  const home = await page.evaluate(() => ({
    sw: document.documentElement.scrollWidth,
    cw: document.documentElement.clientWidth,
    cards: document.querySelectorAll('.card').length,
  }));
  console.log(`\n【7】首页横向溢出 ${home.sw - home.cw}px（${home.sw - home.cw <= 1 ? '✅' : '❌'}）`);

  console.log('\n【8】错误汇总');
  console.log(`  控制台错误 ${errors.length} 条`);
  errors.slice(0, 5).forEach((e) => console.log(`    ${e}`));
  console.log(`  站点失败请求 ${failed.length} 条`);
  failed.slice(0, 5).forEach((e) => console.log(`    ${e}`));

  await browser.close();
})();
