/**
 * 决定性验证：真浏览器(puppeteer-core + 系统Chrome)能否读到公开短信正文
 * 仅访问页面上公开可见的内容，不做登录、不破验证码、不隐藏自动化痕迹以外的反检测。
 */
const puppeteer = require('puppeteer-core');

const TARGETS = [
  { name: 'FreePhoneNum',       url: 'https://freephonenum.com/be/receive-sms/466900108' },
  { name: 'sms-online.co',      url: 'https://www.sms-online.co/receive-free-sms/447599512664' },
  { name: 'sms-online.co(US)',  url: 'https://www.sms-online.co/receive-free-sms/12018577757' },
  { name: 'ReceiveAsmsOnline',  url: 'https://receiveasmsonline.com/united-states/12175285111/' },
  { name: 'GetSMS.uk',          url: 'https://getsms.uk/' },
];

const KEYWORDS = /verification code|your code|one[-\s]?time|OTP|passcode|security code|is your|验证码|短信|code is|code:/i;

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: [
      '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
      '--disable-gpu', '--lang=en-US',
    ],
  });

  const results = [];
  for (const t of TARGETS) {
    const page = await browser.newPage();
    await page.setUserAgent(
      'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    );
    await page.setExtraHTTPHeaders({ 'Accept-Language': 'en-US,en;q=0.9' });

    // 记录该页发出的 XHR，用来定位真实数据接口
    const xhrs = [];
    page.on('response', async (res) => {
      const u = res.url();
      const ct = (res.headers()['content-type'] || '');
      if (ct.includes('json') || /api|message|sms|inbox/i.test(u)) {
        let body = '';
        try { body = (await res.text()).slice(0, 300); } catch (e) { /* ignore */ }
        xhrs.push({ url: u, status: res.status(), ct, body });
      }
    });

    const row = { name: t.name, url: t.url };
    try {
      const resp = await page.goto(t.url, { waitUntil: 'networkidle2', timeout: 45000 });
      row.status = resp ? resp.status() : 0;
      // 等骨架屏消失
      await new Promise((r) => setTimeout(r, 3500));

      row.title = await page.title();

      // 提取可见文本
      const text = await page.evaluate(() => {
        const b = document.body;
        return (b ? b.innerText : '').replace(/[ \t]+/g, ' ').replace(/\n{2,}/g, '\n');
      });
      row.textLen = text.length;

      // 找短信块：常见容器
      const blocks = await page.evaluate(() => {
        const sels = [
          '[class*="message"]', '[class*="Message"]', '[class*="sms"]', '[class*="Sms"]',
          '[class*="inbox"]', '[class*="Inbox"]', 'tbody tr', '.casetext > .row',
          '[class*="chat"]', '[class*="Card"]',
        ];
        const seen = new Set(), out = [];
        for (const s of sels) {
          document.querySelectorAll(s).forEach((el) => {
            const t = (el.innerText || '').trim();
            if (t && t.length > 8 && t.length < 600 && !seen.has(t)) {
              seen.add(t);
              out.push({ sel: s, text: t.slice(0, 300) });
            }
          });
        }
        return out.slice(0, 25);
      });
      row.blocks = blocks;
      row.keywordBlocks = blocks.filter((b) => KEYWORDS.test(b.text));

      // 找验证码数字
      const otps = text.match(/\b\d{4,8}\b/g) || [];
      row.otpCandidates = [...new Set(otps)].slice(0, 20);

      // 是否撞上人机验证
      row.hasCaptcha = await page.evaluate(() =>
        !!document.querySelector('#aliyunCaptcha, .g-recaptcha, [class*="captcha" i], iframe[src*="captcha"]')
      );
      row.xhrs = xhrs.slice(0, 8);
    } catch (e) {
      row.error = `${e.name}: ${String(e.message).slice(0, 120)}`;
    }

    await page.close();
    results.push(row);

    // 报告
    console.log('='.repeat(84));
    console.log(`[${row.name}] ${row.url}`);
    console.log(`  状态 ${row.status}  标题「${(row.title || '').slice(0, 60)}」  可见文本 ${row.textLen} 字符`);
    console.log(`  人机验证: ${row.hasCaptcha ? '⛔ 有' : '✅ 无'}`);
    console.log(`  候选块 ${row.blocks ? row.blocks.length : 0} 个，其中含短信关键词 ${row.keywordBlocks ? row.keywordBlocks.length : 0} 个`);
    if (row.keywordBlocks && row.keywordBlocks.length) {
      row.keywordBlocks.slice(0, 4).forEach((b) => console.log(`    ▸ [${b.sel}] ${b.text.replace(/\n/g, ' | ').slice(0, 200)}`));
    } else if (row.blocks && row.blocks.length) {
      row.blocks.slice(0, 4).forEach((b) => console.log(`    · [${b.sel}] ${b.text.replace(/\n/g, ' | ').slice(0, 160)}`));
    }
    if (row.otpCandidates && row.otpCandidates.length) console.log(`  数字候选: ${row.otpCandidates.join(', ')}`);
    if (row.xhrs && row.xhrs.length) {
      console.log('  XHR:');
      row.xhrs.forEach((x) => console.log(`    ${x.status} ${x.url.slice(0, 110)}`));
      const j = row.xhrs.find((x) => x.body && x.body.length > 10 && /message|sms|text|code/i.test(x.body));
      if (j) console.log(`    JSON样例: ${j.body.slice(0, 220)}`);
    }
    if (row.error) console.log(`  ❌ ${row.error}`);
    console.log('');
  }

  await browser.close();
  require('fs').writeFileSync('/tmp/pptr_result.json', JSON.stringify(results, null, 2));
  console.log('已写入 /tmp/pptr_result.json');
})();
