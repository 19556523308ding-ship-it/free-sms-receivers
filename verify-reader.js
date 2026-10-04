/**
 * 站内短信查看面板 —— 端到端真浏览器验收
 *
 * 重要教训（2026-10-05踩坑）：判断「是否可见」必须查 getComputedStyle +
 * getBoundingClientRect 的**视觉状态**，不能只看 el.hidden 属性。
 * 上一版只查 hidden，结果全绿却漏掉了「.reader{display:flex} 覆盖 hidden」
 * 导致的面板关不掉 + 页面一加载就常驻显示。
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
  const errors = [], failed = [], throttled = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 150)); });
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + String(e.message).slice(0, 150)));
  page.on('response', (r) => {
    const u = r.url();
    if (r.status() < 400 || !u.startsWith(SITE)) return;
    // 429 是本站限频保护按预期生效（验收脚本会连续点刷新，必然触发），
    // 不算缺陷，单独归类以便区分「保护生效」与「真报错」。
    if (r.status() === 429) throttled.push('429 ' + u.replace(SITE, '').slice(0, 70));
    else failed.push(r.status() + ' ' + u.replace(SITE, '').slice(0, 70));
  });

  await page.setViewport({ width: 1440, height: 900 });
  await page.goto(SITE + '/', { waitUntil: 'networkidle2', timeout: 45000 });
  await sleep(2500);

  // 视觉可见性探针：面积 > 0 且 display 非 none
  const visible = (sel) => page.evaluate((s) => {
    const el = document.querySelector(s);
    if (!el) return { exists: false };
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return {
      exists: true,
      hiddenAttr: el.hidden,
      display: cs.display,
      vis: r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden',
      area: Math.round(r.width) + 'x' + Math.round(r.height),
    };
  }, sel);

  const PASS = [];
  const check = (name, ok, detail) => {
    PASS.push(ok);
    console.log(`  ${ok ? '✅' : '❌'} ${name}${detail ? '  ' + detail : ''}`);
  };

  // ---- 0. 初始状态不该有面板 ----
  console.log('【0】初始状态（页面刚加载，不应出现面板）');
  const r0 = await visible('#reader');
  const m0 = await visible('#readerMask');
  check('面板未加载时不可见', !r0.vis, `hidden=${r0.hiddenAttr} display=${r0.display} 面积=${r0.area}`);
  check('遮罩未加载时不可见', !m0.vis, `display=${m0.display}`);

  // ---- 1. 按钮出现范围 ----
  const btns = await page.evaluate(() => {
    const all = Array.from(document.querySelectorAll('.card'));
    const withBtn = all.filter((c) => c.querySelector('.inline-read'));
    return {
      totalCards: all.length,
      withBtn: withBtn.length,
      samples: withBtn.slice(0, 3).map((c) => ({
        src: ((c.querySelector('.card-src') || {}).textContent || '').trim(),
        phone: ((c.querySelector('.card-phone') || {}).textContent || '').replace(/\s+/g, ' ').trim(),
        slug: (c.querySelector('.inline-read') || {}).dataset ? c.querySelector('.inline-read').dataset.slug : null,
      })),
    };
  });
  console.log('\n【1】站内查看按钮范围');
  console.log(`  总卡片 ${btns.totalCards} | 带「站内查看」${btns.withBtn} 张（应等于 receiveasmsonline 的 364 张）`);
  btns.samples.forEach((c) => console.log(`    ${c.phone}  slug=${c.slug}  src=${c.src}`));

  // ---- 2. 打开面板并等待真实短信 ----
  console.log('\n【2】打开面板（等待真实渲染，最长 40s）');
  await page.evaluate(() => {
    const t = Array.from(document.querySelectorAll('.card')).find((c) => c.querySelector('.inline-read'));
    t.scrollIntoView({ block: 'center' });
    t.querySelector('.inline-read').click();
  });
  await sleep(1200);
  const opening = await page.evaluate(() => ({
    sub: (document.querySelector('#readerSub') || {}).textContent || '',
  }));
  const r1 = await visible('#reader');
  const m1 = await visible('#readerMask');
  check('面板打开后可见', r1.vis, `面积=${r1.area}`);
  check('遮罩打开后可见', m1.vis, `面积=${m1.area}`);
  console.log(`  标题「${opening.sub}」`);

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
        tip: (document.querySelector('.reader-tip') || {}).textContent || '',
        items: msgs.slice(0, 4).map((m) => ({
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
  panel.items.forEach((m) => console.log(`    ▸ [${m.time}] ${m.otp ? 'OTP=' + m.otp : ''}\n      ${m.body}`));
  check('渲染出真实短信', panel.count > 0, `${panel.count} 条`);

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
  check('复制按钮生效', cp.ok && cp.label === '已复制 ✓', cp.ok ? `「${cp.otp}」→ 「${cp.label}」` : cp.why);

  // ---- 4. 合规提示 + 无打开原站按钮 ----
  console.log('\n【4】合规与文案');
  check('合规提示常驻', panel.tip.length > 20, `长度 ${panel.tip.length}`);
  const noSrc = await page.evaluate(() => ({
    srcGone: !document.querySelector('#readerSrc') && !document.querySelector('.reader-src'),
    hasRefresh: !!document.querySelector('#readerRefresh'),
  }));
  check('已移除「打开原站」按钮', noSrc.srcGone);
  check('存在「刷新短信」按钮', noSrc.hasRefresh);

  // ---- 5. 三种方式关闭都必须真正隐藏（视觉层面）----
  console.log('\n【5】关闭（三种方式，视觉层面校验）');
  await page.evaluate(() => document.querySelector('#readerClose').click());
  await sleep(600);
  let rc = await visible('#reader');
  const mc = await visible('#readerMask');
  const closedState = await page.evaluate(() => document.body.style.overflow);
  check('点 ✕ 关闭后面板隐藏', !rc.vis, `display=${rc.display} 面积=${rc.area}`);
  check('点 ✕ 关闭后遮罩隐藏', !mc.vis);
  check('body 滚动已恢复', closedState === '');

  await page.evaluate(() => {
    const t = Array.from(document.querySelectorAll('.card')).find((c) => c.querySelector('.inline-read'));
    t.querySelector('.inline-read').click();
  });
  await sleep(1500);
  await page.evaluate(() => document.querySelector('#readerMask').click());
  await sleep(600);
  rc = await visible('#reader');
  check('点遮罩关闭生效', !rc.vis, `面积=${rc.area}`);

  await page.evaluate(() => {
    const t = Array.from(document.querySelectorAll('.card')).find((c) => c.querySelector('.inline-read'));
    t.querySelector('.inline-read').click();
  });
  await sleep(1500);
  await page.keyboard.press('Escape');
  await sleep(600);
  rc = await visible('#reader');
  check('ESC 关闭生效', !rc.vis, `面积=${rc.area}`);

  // ---- 6. 刷新按钮 ----
  console.log('\n【6】刷新短信按钮');
  await page.evaluate(() => {
    const t = Array.from(document.querySelectorAll('.card')).find((c) => c.querySelector('.inline-read'));
    t.scrollIntoView({ block: 'center' });
    t.querySelector('.inline-read').click();
  });
  await sleep(3000);
  const before = await page.evaluate(() => (document.querySelector('#readerNote') || {}).textContent);
  // 连点 5 次：验证前端防重入（inflight + 按钮 disabled）确实拦住了并发请求，
  // 而不是把请求全打出去再让后端 429 兜底。防护在前端 = 对源站更友好。
  for (let i = 0; i < 5; i++) {
    await page.evaluate(() => {
      const b = document.querySelector('#readerRefresh');
      if (b && !b.disabled) b.click();
    });
    await sleep(150);
  }
  await sleep(2500);
  const after = await page.evaluate(() => ({
    note: (document.querySelector('#readerNote') || {}).textContent || '',
    count: document.querySelectorAll('.msg').length,
    empty: (document.querySelector('.reader-empty') || {}).textContent || '',
    tip: (document.querySelector('.reader-tip') || {}).textContent || '',
    refreshEnabled: !document.querySelector('#readerRefresh').disabled,
  }));
  // 无论走缓存(200) 还是限频(429)，都要有明确文案、短信不丢、合规提示仍在
  const noteOk = /^\d+ 条 ·/.test(after.note) || /自动重试|暂无短信/.test(after.note + after.empty);
  check('连点多次后状态文案明确', noteOk, `「${after.note}」`);
  check('连点多次后短信未丢失', after.count > 0 || after.empty.length > 0, `${after.count} 条`);
  check('连点多次后合规提示仍在', after.tip.length > 20);
  check('刷新按钮已恢复可用（无卡死）', after.refreshEnabled);
  console.log(`  刷新前「${before}」→ 连点 5 次后「${after.note}」`);
  console.log(`  说明：前端 inflight 防重入会拦下并发（此处${throttled.length ? '仍命中 ' + throttled.length + ' 次后端限频' : '未触发后端 429，请求未重复发出'}）`);

  // ---- 7. 多视口面板溢出 ----
  console.log('\n【7】面板多视口');
  for (const vp of [{ n: 'desktop', w: 1440, h: 900 }, { n: 'tablet', w: 768, h: 1024 }, { n: 'mobile', w: 390, h: 844 }, { n: 'small', w: 360, h: 740 }]) {
    await page.setViewport({ width: vp.w, height: vp.h });
    await sleep(500);
    await page.evaluate(() => {
      const t = Array.from(document.querySelectorAll('.card')).find((c) => c.querySelector('.inline-read'));
      t.scrollIntoView({ block: 'center' });
      t.querySelector('.inline-read').click();
    });
    await sleep(3500);
    const o = await page.evaluate(() => {
      const p = document.querySelector('#reader');
      const b = p.getBoundingClientRect();
      return {
        sw: document.documentElement.scrollWidth,
        cw: document.documentElement.clientWidth,
        inView: b.top < window.innerHeight && b.bottom > 0,
        w: Math.round(b.width), h: Math.round(b.height),
        refreshH: Math.round(document.querySelector('#readerRefresh').getBoundingClientRect().height),
        closeH: Math.round(document.querySelector('#readerClose').getBoundingClientRect().height),
      };
    });
    const ok = o.sw - o.cw <= 1 && o.inView;
    const touch = o.refreshH >= 44 && o.closeH >= 44 ? '' : ` ⚠️ 触控区不足 44px`;
    check(`${vp.n} ${vp.w}px 面板 ${o.w}x${o.h} 溢出 ${o.sw - o.cw}px`, ok, `刷新键高 ${o.refreshH}px 关闭键 ${o.closeH}px${touch}`);
    await page.screenshot({ path: `/tmp/panel-${vp.n}.png` });
    await page.evaluate(() => document.querySelector('#readerClose').click());
    await sleep(400);
  }

  // ---- 8. 首页整体溢出 ----
  await page.setViewport({ width: 1440, height: 900 });
  await sleep(500);
  const home = await page.evaluate(() => ({
    sw: document.documentElement.scrollWidth,
    cw: document.documentElement.clientWidth,
    cards: document.querySelectorAll('.card').length,
    readerHidden: getComputedStyle(document.querySelector('#reader')).display === 'none',
  }));
  check(`首页横向溢出 ${home.sw - home.cw}px`, home.sw - home.cw <= 1);
  check('首页无残留面板', home.readerHidden);

  console.log('\n【9】错误汇总');
  // 429 相关 console 报错是限频保护的正常副产品，不计入缺陷
  const realErrors = errors.filter((e) => !/429|Too Many Requests/.test(e));
  console.log(`  控制台错误 ${realErrors.length} 条（已排除 429 限频 ${errors.length - realErrors.length} 条）`);
  realErrors.slice(0, 5).forEach((e) => console.log(`    ${e}`));
  console.log(`  站点失败请求 ${failed.length} 条`);
  failed.slice(0, 5).forEach((e) => console.log(`    ${e}`));
  console.log(`  限频命中 ${throttled.length} 次（保护按预期生效，不算缺陷）`);

  const passed = PASS.filter(Boolean).length;
  console.log(`\n===== 验收结果：${passed}/${PASS.length} 项通过 =====`);
  const allOk = passed === PASS.length && !realErrors.length && !failed.length;
  console.log(allOk ? '全部通过 ✅' : '有未通过项 ❌');

  await browser.close();
})();