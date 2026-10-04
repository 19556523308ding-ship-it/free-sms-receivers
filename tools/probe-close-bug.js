/**
 * 复现「面板关不掉 / 一直显示读取中」
 * 关键：上一版验收只查 el.hidden 属性（DOM 状态），
 * 但 CSS display 能覆盖 hidden 属性（视觉状态）——必须查计算样式。
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
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto(SITE + '/', { waitUntil: 'networkidle2', timeout: 45000 });
  await sleep(2000);

  // 真实可见性：getBoundingClientRect 有面积 + computed display 非 none
  const vis = () => page.evaluate(() => {
    const probe = (sel) => {
      const el = document.querySelector(sel);
      if (!el) return { sel, exists: false };
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      return {
        sel,
        exists: true,
        hiddenAttr: el.hidden,
        display: cs.display,
        opacity: cs.opacity,
        // 视觉上真的占面积吗
        visible: r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden',
        area: Math.round(r.width) + 'x' + Math.round(r.height),
      };
    };
    return [probe('#reader'), probe('#readerMask')];
  });

  console.log('【A】刚加载完页面（未点任何按钮）');
  let v = await vis();
  v.forEach((x) => console.log(`  ${x.sel.padEnd(12)} hidden属性=${String(x.hiddenAttr).padEnd(5)} display=${String(x.display).padEnd(6)} 实际可见=${x.visible ? '❌ 是（BUG！）' : '否✅'}  面积=${x.area || '-'}`));

  console.log('\n【B】点卡片上的「站内查看短信」');
  await page.evaluate(() => {
    const c = Array.from(document.querySelectorAll('.card'));
    const t = c.find((x) => x.querySelector('.inline-read'));
    t.scrollIntoView({ block: 'center' });
    t.querySelector('.inline-read').click();
  });
  await sleep(2500);
  v = await vis();
  v.forEach((x) => console.log(`  ${x.sel.padEnd(12)} hidden属性=${String(x.hiddenAttr).padEnd(5)} display=${String(x.display).padEnd(6)} 实际可见=${x.visible ? '✅ 是' : '❌ 否'}  面积=${x.area || '-'}`));
  const sub = await page.evaluate(() => ({
    sub: (document.querySelector('#readerSub') || {}).textContent,
    note: (document.querySelector('#readerNote') || {}).textContent,
  }));
  console.log(`  副标题「${sub.sub}」 状态「${sub.note}」`);

  console.log('\n【C】点右上角 ✕ 关闭（用户报告这一步无效）');
  await page.evaluate(() => document.querySelector('#readerClose').click());
  await sleep(800);
  v = await vis();
  v.forEach((x) => console.log(`  ${x.sel.padEnd(12)} hidden属性=${String(x.hiddenAttr).padEnd(5)} display=${String(x.display).padEnd(6)} 实际可见=${x.visible ? '❌ 仍可见（BUG！）' : '已隐藏 ✅'}  面积=${x.area || '-'}`));

  console.log('\n【D】点遮罩关闭');
  await page.evaluate(() => {
    const c = Array.from(document.querySelectorAll('.card'));
    const t = c.find((x) => x.querySelector('.inline-read'));
    t.querySelector('.inline-read').click();
  });
  await sleep(1200);
  await page.evaluate(() => {
    const m = document.querySelector('#readerMask');
    m.click();
    // 遮罩 onclick 只绑在元素上，但坐标点击更接近真实用户
  });
  await sleep(600);
  const afterMask = await page.evaluate(() => {
    const r = document.querySelector('#reader').getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height) };
  });
  console.log(`  遮罩点击后面板面积 ${afterMask.w}x${afterMask.h}（宽>0 说明还开着）`);

  console.log('\n【E】ESC 关闭');
  await page.keyboard.press('Escape');
  await sleep(600);
  v = await vis();
  const r = v[0];
  console.log(`  ${r.sel} 实际可见=${r.visible ? '❌ 仍可见（BUG！）' : '已隐藏 ✅'}`);

  await browser.close();
})();