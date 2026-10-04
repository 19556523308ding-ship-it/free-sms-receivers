/** 内页与链接验收 */
const puppeteer = require('puppeteer-core');
const http = require('http'); const fs = require('fs'); const path = require('path');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const ROOT = path.join(__dirname, 'web');
const MIME = { '.html':'text/html; charset=utf-8', '.json':'application/json; charset=utf-8',
  '.xml':'application/xml; charset=utf-8', '.txt':'text/plain; charset=utf-8',
  '.png':'image/png', '.svg':'image/svg+xml', '.webp':'image/webp' };
const server = http.createServer((req,res)=>{
  let p = decodeURIComponent(req.url.split('?')[0]);
  if(p==='/') p='/index.html';
  const fp = path.join(ROOT,p);
  if(!fp.startsWith(ROOT)||!fs.existsSync(fp)||fs.statSync(fp).isDirectory()){res.writeHead(404);return res.end('nf');}
  res.writeHead(200,{'Content-Type':MIME[path.extname(fp)]||'application/octet-stream'});
  fs.createReadStream(fp).pipe(res);
});
(async()=>{
  await new Promise(r=>server.listen(8902,'127.0.0.1',r));
  const B='http://127.0.0.1:8902';
  const browser = await puppeteer.launch({executablePath:CHROME,headless:'new',
    args:['--no-sandbox','--disable-dev-shm-usage']});
  const problems=[];

  for(const pg of ['/guide.html','/sources.html']){
    for(const vp of [{n:'1440',w:1440,h:1100},{n:'390',w:390,h:844}]){
      const page = await browser.newPage();
      const errs=[];
      page.on('pageerror',e=>errs.push('PAGEERROR: '+e.message));
      page.on('response',r=>{if(r.status()>=400)errs.push('HTTP'+r.status()+' '+r.url());});
      await page.setViewport({width:vp.w,height:vp.h});
      await page.goto(B+pg,{waitUntil:'networkidle0'});
      await new Promise(r=>setTimeout(r,600));
      const m = await page.evaluate(()=>({
        title:document.title,
        h1:document.querySelector('h1')?.textContent,
        overflowX:document.documentElement.scrollWidth>window.innerWidth+1,
        scrollW:document.documentElement.scrollWidth,winW:window.innerWidth,
        canonical:document.querySelector('link[rel=canonical]')?.href,
        desc:document.querySelector('meta[name=description]')?.content?.length||0,
        links:[...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')),
      }));
      // 内部链接目标必须真实存在
      const bad=[];
      for(const href of [...new Set(m.links.filter(h=>h&&!h.startsWith('http')&&!h.startsWith('#')))]){
        const target = href.split('#')[0];
        if(!target) continue;
        if(!fs.existsSync(path.join(ROOT,target))) bad.push(href);
      }
      const issues=[];
      if(m.overflowX) issues.push('横向溢出 '+m.scrollW+'>'+m.winW);
      if(errs.length) issues.push(errs.join(' | '));
      if(bad.length) issues.push('失效内链: '+bad.join(','));
      console.log(`\n=== ${pg} @${vp.n} ===`);
      console.log(`  title="${m.title}"`);
      console.log(`  h1="${m.h1}" canonical=${m.canonical||'无'} desc长度=${m.desc}`);
      console.log('  内链数='+[...new Set(m.links)].length+(bad.length?' 失效:'+bad.join(','):' 全部有效✅'));
      console.log(issues.length?'  ⚠️ '+issues.join('; '):'  ✅ 通过');
      issues.forEach(i=>problems.push(pg+'@'+vp.n+': '+i));
      if(vp.n==='390') await page.screenshot({path:`D:/workspace/sms-hub/pg-${path.basename(pg,'.html')}-mobile.png`,fullPage:false});
      await page.close();
    }
  }

  // sitemap / robots 可达性
  for(const p of ['/sitemap.xml','/robots.txt']){
    const r = await fetch(B+p);
    console.log(`\n${p} -> HTTP ${r.status} ${r.status===200?'✅':'❌'}`);
    if(r.status!==200) problems.push(p+' 不可达');
  }

  // 首页内链有效性
  const page = await browser.newPage();
  await page.goto(B+'/',{waitUntil:'networkidle0'});
  const links = await page.evaluate(()=>[...new Set([...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')))]);
  const bad=[];
  for(const href of links.filter(h=>!h.startsWith('http')&&!h.startsWith('#'))){
    const t=href.split('#')[0]; if(!t) continue;
    if(!fs.existsSync(path.join(ROOT,t))) bad.push(href);
  }
  console.log(`\n首页内链 ${links.length} 条${bad.length?' 失效: '+bad.join(','):' 全部有效 ✅'}`);
  bad.forEach(b=>problems.push('首页失效内链: '+b));
  await page.close();

  console.log('\n=== 汇总 ===');
  console.log(problems.length?'发现问题:\n  '+problems.join('\n  '):'全部通过 ✅');
  await browser.close(); server.close();
})();
