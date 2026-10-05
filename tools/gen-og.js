const puppeteer = require('puppeteer-core');
const fs = require('fs');
const b64 = f => 'data:image/svg+xml;base64,' + fs.readFileSync(f).toString('base64');

(async () => {
  let html = fs.readFileSync('tools/og-template.html', 'utf8');
  html = html.replace('HERO', b64('web/assets/backgrounds/hero-bg.svg'))
             .replace('LOGO', b64('web/assets/brand/logo.svg'))
             .replace('PHONE', b64('web/assets/elements/phone-mockup.svg'));
  const b = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox'],
  });
  const p = await b.newPage();
  await p.setViewport({ width: 1200, height: 630, deviceScaleFactor: 1 });
  await p.setContent(html, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 800));
  await p.screenshot({ path: 'web/assets/backgrounds/og-cover.png', type: 'png' });
  await b.close();
  console.log('OG 封面已生成');
})();
