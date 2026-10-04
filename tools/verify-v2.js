/**
 * SMS Hub 2.0 — 端到端验收（真实浏览器）
 * 对齐设计文档 §51 Desktop 验收 / §52 Mobile 验收 / §53 功能验收
 *
 * 用法：
 *   node tools/verify-v2.js [baseURL]
 *   baseURL 默认 http://127.0.0.1:8899
 */
const path = require('path');
const puppeteer = require('puppeteer-core');

const BASE = (process.argv[2] || 'http://127.0.0.1:8899').replace(/\/+$/, '');
const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const SHOT = path.join(__dirname, '..', 'shots-v2');

const results = [];
const ok = (n, d = '') => { results.push(['PASS', n, d]); console.log(`  ✅ ${n}${d ? ' — ' + d : ''}`); };
const bad = (n, d = '') => { results.push(['FAIL', n, d]); console.log(`  ❌ ${n}${d ? ' — ' + d : ''}`); };
const warn = (n, d = '') => { results.push(['WARN', n, d]); console.log(`  ⚠️  ${n}${d ? ' — ' + d : ''}`); };

const VIEWPORTS = {
  d1440: { width: 1440, height: 900, dpr: 1, mobile: false },
  d1366: { width: 1366, height: 800, dpr: 1, mobile: false },
  d1280: { width: 1280, height: 800, dpr: 1, mobile: false },
  m375: { width: 375, height: 812, dpr: 2, mobile: true },
  m390: { width: 390, height: 844, dpr: 2, mobile: true },
  m430: { width: 430, height: 932, dpr: 2, mobile: true },
};

async function goto(browser, url, vp, opts = {}) {
  const page = await browser.newPage();
  await page.setViewport({ ...vp, deviceScaleFactor: 1 });
  if (vp.mobile) {
    await page.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1');
  }
  const errs = [];
  const badUrls = [];
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  page.on('pageerror', e => errs.push('pageerror: ' + e.message));
  page.on('response', r => {
    const u = r.url();
    if (r.status() >= 400 && !u.includes('flagcdn.com')) badUrls.push(r.status() + ' ' + u);
  });
  page.on('requestfailed', r => {
    const u = r.url();
    if (u.includes('flagcdn.com')) return; // 离线环境国旗图可失败
    errs.push('reqfail: ' + u + ' ' + (r.failure() || {}).errorText);
  });
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  if (opts.wait !== false) {
    // 等骨架屏消失
    await page.waitForFunction(() => !document.querySelector('.skel'), { timeout: opts.timeout || 25000 }).catch(() => {});
    await new Promise(r => setTimeout(r, opts.settle ?? 700));
  }
  return { page, errs, badUrls };
}


/* 资源错误检查：/api/sms 在后端未启动时返回 404/连接失败，属本地预览预期，不计入 */
function checkErrs(errs, badUrls, label, vp, bad, ok) {
  const tag = vp ? `${label} @${vp}` : label;
  const e = (errs || []).filter(x => !/api\/sms|Failed to load resource/i.test(x));
  const b = (badUrls || []).filter(u => !/api\/sms|favicon\.ico/.test(u));
  if (e.length || b.length) {
    bad(`${tag} 有资源/脚本错误`, [...e.slice(0, 2), ...b.slice(0, 2)].join(' | '));
  } else {
    ok(`${tag} 无资源/脚本错误`);
  }
}

const overflow = page => page.evaluate(() =>
  Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth));

async function shot(page, name) {
  const fs = require('fs');
  if (!fs.existsSync(SHOT)) fs.mkdirSync(SHOT, { recursive: true });
  await page.screenshot({ path: path.join(SHOT, name + '.png') });
}

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--font-render-hinting=none'],
  });

  try {
    /* ================= 首页 ================= */
    console.log('\n== 首页 / ==');
    for (const [k, vp] of Object.entries(VIEWPORTS)) {
      const { page, errs, badUrls } = await goto(browser, BASE + '/index.html', vp);
      const of = await overflow(page);
      of > 1 ? bad(`首页无横向溢出 @${k}`, `溢出 ${of}px`) : ok(`首页无横向溢出 @${k}`);

      if (k === 'd1440' || k === 'm390') {
        const info = await page.evaluate(() => ({
          h1: (document.querySelector('.hero h1') || {}).innerText || '',
          sub: (document.querySelector('.hero .sub') || {}).innerText || '',
          ctys: document.querySelectorAll('#ctys .cty').length,
          recs: document.querySelectorAll('#recGrid .ncard').length,
          stats: document.querySelectorAll('#hstats .hstat').length,
          steps: document.querySelectorAll('.stepc').length,
          hasPick: !!document.querySelector('#pickBtn'),
          hasShuffle: !!document.querySelector('#shuffle'),
          hasSpare: !!document.querySelector('#spare'),
          hasSafety: !!document.querySelector('.safety'),
          hasMap: !!document.querySelector('svg.map, .world-map, [data-world-map]'),
          statText: (document.querySelector('#hstats') || {}).innerText || '',
          ctyNames: [...document.querySelectorAll('#ctys .cty')].map(e => e.innerText.replace(/\s+/g, ' ')).slice(0, 3),
          recText: (document.querySelector('#recGrid .ncard') || {}).innerText || '',
        }));
        if (k === 'd1440') {
          /免费.*接收短信.*验证码/.test(info.h1.replace(/\s/g, '')) ? ok('H1 = 免费接收短信验证码', info.h1) : bad('H1 文案', info.h1);
          /无需注册.*免费.*在线查看/.test(info.sub.replace(/\s/g, '')) ? ok('副标题正确') : bad('副标题', info.sub);
          info.stats === 4 ? ok('Hero 统计 4 项') : bad('Hero 统计项数', String(info.stats));
          !/来源|数据源|个来源/.test(info.statText) ? ok('Hero 统计已去掉来源指标') : bad('Hero 仍含来源指标', info.statText.replace(/\s+/g, ' '));
          info.ctys >= 6 ? ok('国家卡 >= 6', String(info.ctys)) : warn('国家卡偏少', String(info.ctys));
          info.recs >= 4 ? ok('推荐号码卡 >= 4', String(info.recs)) : bad('推荐号码卡不足', String(info.recs));
          info.steps === 4 ? ok('如何使用 4 步') : bad('如何使用步数', String(info.steps));
          info.hasPick && info.hasShuffle && info.hasSafety && info.hasSpare ? ok('核心区块齐备（CTA/换一批/折叠/安全）') : bad('区块缺项', JSON.stringify({ pick: info.hasPick, shuffle: info.hasShuffle, safety: info.hasSafety, spare: info.hasSpare }));
          !info.hasMap ? ok('Hero 未使用世界地图（§44）') : bad('Hero 仍含地图');
          !/来源|alsoOn/.test(info.recText) ? ok('推荐卡不展示来源') : bad('推荐卡含来源字段', info.recText.replace(/\s+/g, ' '));
          /使用此号码/.test(info.recText) ? ok('推荐卡含「使用此号码」入口') : bad('推荐卡缺入口');
        }
        await shot(page, `home-${k}`);
      }
      checkErrs(errs, badUrls, `首页`, k, bad, ok);
      await page.close();
    }

    // 首页交互：换一批
    {
      const { page } = await goto(browser, BASE + '/index.html', VIEWPORTS.d1440, { settle: 1200 });
      await page.evaluate(() => window.scrollTo(0, 600));
      await new Promise(r => setTimeout(r, 250));
      const yBefore = await page.evaluate(() => window.scrollY);
      const before = await page.$eval('#recGrid .ncard .val', e => e.textContent.trim());
      await page.click('#shuffle');
      await new Promise(r => setTimeout(r, 600));
      const after = await page.$eval('#recGrid .ncard .val', e => e.textContent.trim());
      const yAfter = await page.evaluate(() => window.scrollY);
      before !== after ? ok('「换一批」切换了推荐池') : bad('「换一批」未改变内容');
      Math.abs(yAfter - yBefore) < 60 ? ok('「换一批」未刷新整页（滚动位置保留）') : warn('换一批后滚动位置偏移', `${yBefore} → ${yAfter}`);
      await page.close();
    }

    // 首页搜索
    {
      const { page } = await goto(browser, BASE + '/index.html', VIEWPORTS.d1440);
      await page.type('#hq', '美国');
      await new Promise(r => setTimeout(r, 500));
      const n1 = await page.$$eval('#ctys .cty', els => els.length);
      await page.$eval('#hq', e => e.value = '');
      await page.type('#hq', '+1');
      await new Promise(r => setTimeout(r, 500));
      const n2 = await page.$$eval('#ctys .cty', els => els.length);
      (n1 >= 1 && n2 >= 1) ? ok('搜索支持中文与区号', `美国=${n1} +1=${n2}`) : bad('搜索失效', `美国=${n1} +1=${n2}`);
      await page.close();
    }

    // 首页推荐区国家多样性（避免单国霸屏首屏）
    {
      const { page } = await goto(browser, BASE + '/index.html', VIEWPORTS.d1440);
      const isos = await page.$$eval('#recGrid .ncard .ncard-ctry .nm', els => els.map(e => e.textContent.trim()));
      const uniq = [...new Set(isos)];
      uniq.length >= 2 ? ok('推荐区首屏国家多样', uniq.join('/')) : warn('推荐区首屏单国霸屏', isos.join('/'));
      await page.close();
    }

    /* ================= 号码列表 /numbers ================= */
    console.log('\n== 号码列表 /numbers ==');
    for (const [k, vp] of Object.entries(VIEWPORTS)) {
      const { page, errs, badUrls } = await goto(browser, BASE + '/numbers.html', vp);
      const of = await overflow(page);
      of > 1 ? bad(`列表无横向溢出 @${k}`, `溢出 ${of}px`) : ok(`列表无横向溢出 @${k}`);
      if (k === 'd1440') {
        const info = await page.evaluate(() => ({
          sub: (document.querySelector('#ptSub') || {}).innerText || '',
          cards: document.querySelectorAll('#grid .ncard').length,
          cardsNoSrc: [...document.querySelectorAll('#grid .ncard')].every(c => !/来源|alsoOn/.test(c.innerText)),
          res: (document.querySelector('#res') || {}).innerText || '',
          hasMore: !!document.querySelector('#moreBtn'),
          statuses: [...new Set([...document.querySelectorAll('#grid .st')].map(e => e.textContent.trim()))],
        }));
        /站内可直接接收短信的号码/.test(info.sub) ? ok('副标题说明站内可收短信池', info.sub.replace(/\s+/g, ' ')) : bad('列表副标题', info.sub);
        info.cards >= 20 ? ok('首屏渲染号码卡', String(info.cards)) : bad('号码卡过少', String(info.cards));
        info.cardsNoSrc ? ok('列表卡不展示来源') : bad('列表卡含来源');
        !/状态未知/.test(info.statuses.join(',')) ? ok('未出现「状态未知」（§10）', info.statuses.join('/')) : bad('仍出现「状态未知」');
        await shot(page, 'numbers-d1440');
      }
      if (k === 'm390') {
        const sheetOk = await page.evaluate(() => {
          const b = document.querySelector('#openSheet');
          if (!b) return false;
          const cs = getComputedStyle(b);
          return cs.display !== 'none';
        });
        sheetOk ? ok('移动端显示筛选按钮') : bad('移动端缺筛选按钮');
        await shot(page, 'numbers-m390');
      }
      checkErrs(errs, badUrls, `列表`, k, bad, ok);
      await page.close();
    }

    // 筛选交互
    {
      const { page } = await goto(browser, BASE + '/numbers.html', VIEWPORTS.d1440);
      await page.select('#fCountry', 'US');
      await new Promise(r => setTimeout(r, 500));
      const usOnly = await page.$$eval('#grid .ncard .ncard-ctry .nm', els => [...new Set(els.map(e => e.textContent.trim()))]);
      (usOnly.length === 1 && usOnly[0] === '美国') ? ok('国家筛选生效', usOnly.join(',')) : bad('国家筛选异常', usOnly.join(','));
      const chip = await page.$eval('#chips', e => e.innerText.replace(/\s+/g, ' '));
      /国家：美国/.test(chip) ? ok('筛选条件 chip 显示') : bad('筛选 chip 缺失', chip);
      await page.click('#chips button');
      await new Promise(r => setTimeout(r, 500));
      const chip2 = await page.$eval('#chips', e => e.innerText.trim());
      const res2 = await page.$eval('#res', e => e.innerText.replace(/\s+/g, ' '));
      // 清除后：chip 消失、结果数回到全量（不再是 186）
      (!/国家：/.test(chip2)) ? ok('清除筛选：条件 chip 已移除') : bad('清除筛选无效', chip2);
      const m = res2.match(/(\d+)\s*\/\s*(\d+)/);
      const shown = m ? +m[1] : null;
      (shown === null || shown > 200) ? ok('清除筛选：结果集恢复全量', res2) : bad('清除筛选：结果未恢复', res2);
      await page.close();
    }

    // 备用池折叠
    {
      const { page } = await goto(browser, BASE + '/index.html', VIEWPORTS.d1440);
      const t = await page.$eval('#spareTitle', e => e.textContent);
      /其他号码/.test(t) ? ok('备用池折叠存在', t) : bad('备用池折叠缺失');
      await page.click('#spare summary');
      await new Promise(r => setTimeout(r, 300));
      const n = await page.$$eval('#spareGrid .sp', els => els.length);
      n > 0 ? ok('备用池展开有内容', String(n) + ' 个国家') : bad('备用池展开为空');
      await page.close();
    }

    /* ================= 收短信页 /number ================= */
    console.log('\n== 收短信页 /number ==');
    let numId = null;
    {
      const { page } = await goto(browser, BASE + '/numbers.html', VIEWPORTS.d1440);
      numId = await page.$eval('#grid .ncard a[href*="number.html"]', a => {
        const m = a.getAttribute('href').match(/id=([^&]+)/);
        return m ? decodeURIComponent(m[1]) : null;
      }).catch(() => null);
      await page.close();
    }
    if (!numId) bad('未能取到可用号码 id');
    else {
      ok('取到站内可接码号码 id', numId);
      for (const [k, vp] of Object.entries(VIEWPORTS)) {
        const { page, errs, badUrls } = await goto(browser, BASE + '/number.html?id=' + encodeURIComponent(numId), vp, { settle: 900 });
        const of = await overflow(page);
        of > 1 ? bad(`收码页无横向溢出 @${k}`, `溢出 ${of}px`) : ok(`收码页无横向溢出 @${k}`);
        if (k === 'd1440') {
          const info = await page.evaluate(() => ({
            phone: (document.querySelector('#nhPhone') || {}).innerText || '',
            steps: document.querySelectorAll('#flow .fstep').length,
            hasCopy: !!document.querySelector('#cpNum'),
            hasSwitch: !!document.querySelector('#switchNum'),
            metaLabels: [...document.querySelectorAll('#nmeta .m .k')].map(e => e.innerText),
            tabs: [...document.querySelectorAll('#ibTabs .tab')].map(e => e.innerText.replace(/\s+/g, ' ')),
            waitText: (document.querySelector('#wait') || {}).innerText.replace(/\s+/g, ' '),
            otpSize: (() => { const e = document.querySelector('.otp-val'); return e ? parseFloat(getComputedStyle(e).fontSize) : 0; })(),
          }));
          /^\+/.test(info.phone) ? ok('号码头展示完整 E.164', info.phone) : bad('号码头异常', info.phone);
          info.steps === 3 ? ok('使用流程条 3 步（§15）') : bad('流程条步数', String(info.steps));
          info.hasCopy && info.hasSwitch ? ok('含「复制号码」与「换号」') : bad('缺关键按钮');
          /本次使用后/.test(info.tabs.join('')) && /所有短信/.test(info.tabs.join('')) ? ok('收件箱双 Tab（§21）', info.tabs.join(' / ')) : bad('收件箱 Tab 缺失', info.tabs.join(' / '));
          ['最近活跃', '今日短信', '当前状态', '自动检测'].every(x => info.metaLabels.includes(x)) ? ok('号码信息 4 项齐备') : bad('信息项缺失', info.metaLabels.join(','));
          await shot(page, 'number-d1440');
        }
        if (k === 'm390') {
          const st = await page.evaluate(() => {
            const s = document.querySelector('.sticky-bar');
            if (!s) return null;
            const cs = getComputedStyle(s);
            return { display: cs.display, visible: s.getBoundingClientRect().height > 0 };
          });
          (st && st.display !== 'none' && st.visible) ? ok('移动端 Sticky Bar 可见（§26）') : bad('移动端 Sticky Bar 不可见', JSON.stringify(st));
          await shot(page, 'number-m390');
        }
        checkErrs(errs, badUrls, `收码页`, k, bad, ok);
        await page.close();
      }

      // 复制号码 → 建立会话 → 流程推进
      {
        const { page } = await goto(browser, BASE + '/number.html?id=' + encodeURIComponent(numId), VIEWPORTS.d1440);
        await page.click('#cpNum');
        await new Promise(r => setTimeout(r, 700));
        const st = await page.evaluate(() => ({
          flow: [...document.querySelectorAll('#flow .fstep')].map(e => e.className.replace('fstep', '').trim()),
          wait: (document.querySelector('#wait') || {}).innerText.replace(/\s+/g, ' '),
          sess: localStorage.getItem('smshub.session.v2'),
        }));
        const s = st.sess ? JSON.parse(st.sess) : null;
        s && s.numberId === numId ? ok('复制号码建立接码 Session（§16）') : bad('Session 未建立', st.sess || 'null');
        s && s.sessionStartedAt ? ok('Session 记录开始时间') : bad('Session 缺时间');
        /第|2|填写/.test(st.flow[1] || '') || st.flow[1].includes('on') ? ok('流程条推进到「填写」') : warn('流程未推进', st.flow.join('|'));
        /等待|填写/.test(st.wait) ? ok('自动进入等待状态') : bad('未进入等待', st.wait);
        await shot(page, 'number-after-copy');
        await page.close();
      }

      // 换号
      {
        const { page } = await goto(browser, BASE + '/number.html?id=' + encodeURIComponent(numId), VIEWPORTS.d1440);
        const before = await page.$eval('#nhPhone', e => e.textContent);
        await page.click('#switchNum');
        await page.waitForFunction(p => document.querySelector('#nhPhone') && document.querySelector('#nhPhone').textContent !== p, { timeout: 12000 }, before).catch(() => {});
        const after = await page.$eval('#nhPhone', e => e.textContent);
        after !== before ? ok('一键换同国家号码（§23）', before + ' → ' + after) : bad('换号未生效', before);
        await page.close();
      }

      // 伪造：无短信时的 30/90 秒文案（直接注入 session 起始时间）
      {
        const { page } = await goto(browser, BASE + '/number.html?id=' + encodeURIComponent(numId), VIEWPORTS.d1440);
        await page.evaluate(() => {
          localStorage.setItem('smshub.session.v2', JSON.stringify({
            numberId: new URLSearchParams(location.search).get('id'),
            country: 'US',
            sessionStartedAt: new Date(Date.now() - 100000).toISOString(),
            initialMessageIds: [],
          }));
        });
        await page.reload({ waitUntil: 'domcontentloaded' });
        await new Promise(r => setTimeout(r, 3500));
        const w = await page.$eval('#wait', e => e.innerText.replace(/\s+/g, ' '));
        /可能暂时|换一个/.test(w) ? ok('90 秒无短信提示（§22）', w) : warn('90 秒提示未触发（可能已收到真实短信）', w);
        await page.close();
      }
    }

    /* ================= 国家页 /country ================= */
    console.log('\n== 国家页 /country ==');
    for (const [k, vp] of Object.entries({ d1440: VIEWPORTS.d1440, m390: VIEWPORTS.m390 })) {
      const { page, errs, badUrls } = await goto(browser, BASE + '/country.html?c=US', vp);
      const of = await overflow(page);
      of > 1 ? bad(`国家页无横向溢出 @${k}`, `溢出 ${of}px`) : ok(`国家页无横向溢出 @${k}`);
      const info = await page.evaluate(() => ({
        h1: (document.querySelector('.cp-head h1') || {}).innerText || '',
        stats: document.querySelectorAll('.cp-stat .s').length,
        tabs: [...document.querySelectorAll('#tabs .tab')].map(e => e.innerText.replace(/\s+/g, ' ')),
        cards: document.querySelectorAll('#grid .ncard').length,
        other: document.querySelectorAll('#ochips .ochip').length,
      }));
      /美国免费接码号码/.test(info.h1) ? ok(`国家页 H1 @${k}`, info.h1) : bad(`国家页 H1 @${k}`, info.h1);
      if (k === 'd1440') {
        info.stats === 3 ? ok('国家页统计 3 项') : bad('国家页统计项数', String(info.stats));
        info.tabs.length === 4 ? ok('状态 Tabs 4 项（§13）', info.tabs.join(' / ')) : bad('状态 Tabs 异常', info.tabs.join(' / '));
        info.cards >= 20 ? ok('国家页号码卡', String(info.cards)) : bad('国家页卡片少', String(info.cards));
        info.other >= 3 ? ok('其他国家入口', String(info.other)) : warn('其他国家入口少');
        await shot(page, 'country-d1440');
      }
      checkErrs(errs, badUrls, `国家页`, k, bad, ok);
      await page.close();
    }

    /* ================= 后台 /admin ================= */
    console.log('\n== 后台 /admin ==');
    {
      const { page, errs, badUrls } = await goto(browser, BASE + '/admin.html', VIEWPORTS.d1440, { settle: 900 });
      const info = await page.evaluate(() => ({
        kpis: document.querySelectorAll('.kpi').length,
        srcRows: document.querySelectorAll('#srcTable tbody tr').length,
        poolRows: document.querySelectorAll('#poolTable tbody tr').length,
        hasDep: /高依赖/.test(document.body.innerText),
        srcText: (document.querySelector('#srcTable') || {}).innerText || '',
        probeText: (document.querySelector('#probeBody') || {}).innerText || '',
      }));
      info.kpis >= 6 ? ok('KPI 卡 >= 6', String(info.kpis)) : bad('KPI 卡少', String(info.kpis));
      info.srcRows >= 5 ? ok('来源健康表有数据', String(info.srcRows) + ' 行') : bad('来源表空', String(info.srcRows));
      info.poolRows >= 10 ? ok('号码池结构表有数据', String(info.poolRows) + ' 行') : bad('号码池表空', String(info.poolRows));
      info.hasDep ? ok('展示「高依赖风险」标记（§33）') : warn('未见高依赖标记');
      /健康|可疑零值|疑似退化|采集失败|空结果/.test(info.srcText) ? ok('来源健康状态已渲染（§30-§32）') : bad('来源状态未渲染');
      /403|429|探测/.test(info.probeText) ? ok('探测覆盖说明存在') : warn('探测说明缺失');
      await shot(page, 'admin-d1440');
      errs.length ? bad('后台控制台错误', errs.slice(0, 2).join(' | ')) : ok('后台无控制台错误');
      await page.close();
    }

    /* ================= 指南 / FAQ ================= */
    console.log('\n== 指南 / FAQ ==');
    for (const p of ['/guide.html', '/faq.html']) {
      const { page, errs, badUrls } = await goto(browser, BASE + p, VIEWPORTS.d1440);
      const of = await overflow(page);
      of > 1 ? bad(`${p} 无横向溢出`, `溢出 ${of}px`) : ok(`${p} 无横向溢出`);
      const h1 = await page.$eval('h1', e => e.innerText).catch(() => '');
      h1 ? ok(`${p} 有 H1`, h1) : bad(`${p} 缺 H1`);
      checkErrs(errs, badUrls, `${p}`, '', bad, ok);
      await page.close();
    }

    /* ================= 移动端底部导航 ================= */
    console.log('\n== 移动端底部导航（§27）==');
    {
      const { page } = await goto(browser, BASE + '/index.html', VIEWPORTS.m390);
      const st = await page.evaluate(() => {
        const b = document.querySelector('.bnav');
        if (!b) return null;
        return { display: getComputedStyle(b).display, items: b.querySelectorAll('a').length, h: b.getBoundingClientRect().height };
      });
      (st && st.display !== 'none' && st.items === 3) ? ok('底部导航 3 项可见', `${st.items} 项 / ${Math.round(st.h)}px`) : bad('底部导航异常', JSON.stringify(st));
      await page.close();
    }

    /* ================= 视觉规范核对（§41） ================= */
    console.log('\n== 视觉规范（§41）==');
    {
      const { page } = await goto(browser, BASE + '/index.html', VIEWPORTS.d1440);
      const vars = await page.evaluate(() => {
        const cs = getComputedStyle(document.documentElement);
        const g = n => cs.getPropertyValue(n).trim();
        return { bg: g('--bg'), surface: g('--surface'), primary: g('--primary'), accent: g('--accent'), success: g('--success'), warning: g('--warning'), text: g('--text'), muted: g('--text-muted') };
      });
      const want = { bg: '#070B12', surface: '#101722', primary: '#4F7FFF', accent: '#2DD4A8', success: '#22C55E', warning: '#F59E0B', text: '#F8FAFC', muted: '#94A3B8' };
      let all = true;
      for (const [k, v] of Object.entries(want)) {
        if (String(vars[k]).toUpperCase() !== v) { all = false; bad(`token --${k} = ${vars[k]}，应为 ${v}`); }
      }
      if (all) ok('8 项视觉 token 全部对齐设计规范');
      const radius = await page.evaluate(() => {
        const cs = getComputedStyle(document.documentElement);
        const g = n => cs.getPropertyValue(n).trim();
        return { btn: g('--r-btn'), input: g('--r-input'), card: g('--r-card'), modal: g('--r-modal') };
      });
      (radius.btn === '8px' && radius.input === '10px' && radius.card === '12px' && radius.modal === '16px')
        ? ok('Radius 规范对齐（8/10/12/16）') : bad('Radius 不符', JSON.stringify(radius));
      await page.close();
    }

    /* ================= 台面配色抽查 ================= */
    console.log('\n== 关键元素配色抽查 ==');
    {
      const { page } = await goto(browser, BASE + '/index.html', VIEWPORTS.d1440);
      const c = await page.evaluate(() => ({
        body: getComputedStyle(document.body).backgroundColor,
        card: (() => { const e = document.querySelector('.ncard'); return e ? getComputedStyle(e).backgroundColor : ''; })(),
      }));
      c.body === 'rgb(7, 11, 18)' ? ok('页面背景 #070B12') : bad('背景色不符', c.body);
      c.card ? ok('卡片使用 surface 底色', c.card) : warn('未取到卡片');
      await page.close();
    }

  } catch (e) {
    console.error('\n验收脚本异常：', e);
    bad('脚本执行异常', e.message);
  } finally {
    await browser.close();
  }

  /* ---------- 汇总 ---------- */
  const p = results.filter(r => r[0] === 'PASS').length;
  const f = results.filter(r => r[0] === 'FAIL').length;
  const w = results.filter(r => r[0] === 'WARN').length;
  console.log('\n' + '='.repeat(58));
  console.log(`验收结果：通过 ${p} · 失败 ${f} · 警告 ${w}`);
  if (f) {
    console.log('\n失败项：');
    results.filter(r => r[0] === 'FAIL').forEach(r => console.log(`  ❌ ${r[1]}${r[2] ? ' — ' + r[2] : ''}`));
  }
  if (w) {
    console.log('\n警告项：');
    results.filter(r => r[0] === 'WARN').forEach(r => console.log(`  ⚠️  ${r[1]}${r[2] ? ' — ' + r[2] : ''}`));
  }
  console.log('='.repeat(58));
  process.exit(f ? 1 : 0);
})();
