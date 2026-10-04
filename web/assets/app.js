/* SMS Hub 2.0 — 共享数据层与工具
   零构建：原生 ES 模块，多页复用。
   对外不暴露来源 / alsoOn / 来源数（§1 内外分离）。 */

export const DATA_URL = 'data/numbers.json';

/* ---------- 工具 ---------- */
export const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* §10 状态模型：可用 / 较少使用 / 暂未验证 */
export const STATUS_LABEL = {
  available: '可用',
  low_usage: '较少使用',
  unverified: '暂未验证',
};
export const STATUS_DESC = {
  available: '可正常接收',
  low_usage: '活跃度较低',
  unverified: '暂无近期短信',
};

/* 彩色国旗（Windows 不渲染国旗 emoji，用图片；失败则隐藏，文字始终在场） */
export const flagImg = cc =>
  `<img class="fl" src="https://flagcdn.com/w40/${String(cc || '').toLowerCase()}.png" ` +
  `width="21" height="16" alt="" loading="lazy" onerror="this.style.visibility='hidden'">`;

/* 号码按国际惯例分组：+1 202 555 0188；复制仍是完整 E.164 */
export function fmtPhone(phone, callingCode) {
  const bare = String(phone || '').replace(/\D/g, '');
  const cc = String(callingCode || '').replace(/\D/g, '');
  const rest = cc && bare.startsWith(cc) && bare.length > cc.length ? bare.slice(cc.length) : bare;
  if (!rest) return '+' + (cc || bare);
  const chunks = rest.match(/.{1,3}/g) || [];
  if (chunks.length > 1 && chunks[chunks.length - 1].length === 1) {
    const last = chunks.pop();
    chunks[chunks.length - 1] += last;
  }
  return '+' + cc + ' ' + chunks.join(' ');
}

export function relTime(iso) {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (isNaN(t)) return null;
  const s = Math.floor((Date.now() - t) / 1000);
  if (s < 0) return '刚刚';
  if (s < 60) return '刚刚';
  if (s < 3600) return Math.floor(s / 60) + ' 分钟前';
  if (s < 86400) return Math.floor(s / 3600) + ' 小时前';
  return Math.floor(s / 86400) + ' 天前';
}

/* ---------- 数据加载 ---------- */
let _cache = null;

export async function loadData({ force = false } = {}) {
  if (_cache && !force) return _cache;
  const r = await fetch(DATA_URL + '?t=' + (force ? Date.now() : ''), { cache: force ? 'no-store' : 'default' });
  if (!r.ok) throw new Error('HTTP ' + r.status);
  const j = await r.json();
  if (!j || !Array.isArray(j.numbers)) throw new Error('数据格式异常');
  _cache = j;
  return j;
}

/* ---------- 号码池规则（§11 默认只展示 direct inbox） ---------- */
export const isDirect = n => n.directInbox === true;

/** 主池：站内可收短信（directInbox = true） */
export const mainPool = data => data.numbers.filter(isDirect);
/** 备用池：仅可跳原站查看，不进推荐、不进默认列表 */
export const sparePool = data => data.numbers.filter(n => !isDirect(n));

/* ---------- §12 推荐排序（对外只显示「推荐」） ---------- */
export function scoreOf(n) {
  if (typeof n.availabilityScore === 'number') return n.availabilityScore;
  let s = 0;
  if (isDirect(n)) s += 0.35 + 0.25;
  if (n.sourceStatus === 'ok') s += 0.20;
  if ((n.sourceCount || 1) >= 2) s += 0.10;
  if (n.statusCheckedAt || n.probed) s += 0.10;
  return s;
}

/** 推荐池排序：direct inbox 优先 -> availabilityScore -> 短信数 -> 国家号池规模 */
export function rank(list) {
  // 先算出各国家的可用号码规模，规模大的国家整体靠前（避免小众国家霸屏首屏）
  const sizeByIso = new Map();
  for (const n of list) {
    if (!n.countryCode) continue;
    sizeByIso.set(n.countryCode, (sizeByIso.get(n.countryCode) || 0) + 1);
  }
  const size = n => sizeByIso.get(n.countryCode) || 0;

  return list.slice().sort((a, b) => {
    if (isDirect(a) !== isDirect(b)) return isDirect(a) ? -1 : 1;
    const d = scoreOf(b) - scoreOf(a);
    if (Math.abs(d) > 0.0001) return d;
    const s = size(b) - size(a);
    if (s) return s;
    const m = (b.messageCount || b.smsToday || 0) - (a.messageCount || a.smsToday || 0);
    if (m) return m;
    return (a.messageCount == null ? 1 : 0) - (b.messageCount == null ? 1 : 0);
  });
}

/** 推荐号码池：国家轮转采样，保证首屏国家多样性（§7 首页推荐） */
export function pickDiverse(list, size) {
  const ranked = rank(list);
  const byIso = new Map();
  for (const n of ranked) {
    const k = n.countryCode || 'XX';
    if (!byIso.has(k)) byIso.set(k, []);
    byIso.get(k).push(n);
  }
  // 国家顺序：可用号码多的优先
  const order = [...byIso.keys()].sort((a, b) => byIso.get(b).length - byIso.get(a).length);
  const out = [];
  let round = 0;
  while (out.length < size && round < 50) {
    let added = false;
    for (const iso of order) {
      const q = byIso.get(iso);
      if (q.length > round) { out.push(q[round]); added = true; }
      if (out.length >= size) break;
    }
    if (!added) break;
    round++;
  }
  return out;
}

/* ---------- 搜索：中文 / 英文 / ISO / 区号 (§5.2) ---------- */
export function matchCountry(c, q) {
  if (!q) return true;
  const s = q.trim().toLowerCase();
  const digits = s.replace(/[\s()\-+]/g, '');
  if (/^\d+$/.test(digits) && digits.length >= 1) {
    return String(c.callingCode || '') === digits || String(c.callingCode || '').startsWith(digits);
  }
  return (c.nameZh || '').toLowerCase().includes(s)
    || (c.nameEn || '').toLowerCase().includes(s)
    || (c.iso || '').toLowerCase().includes(s)
    || (c.iso || '').toLowerCase() === s;
}

/* ---------- 国家聚合（数据里已带 countries，缺失则本地兜底） ---------- */
export function countriesOf(data) {
  if (Array.isArray(data.countries) && data.countries.length) return data.countries;
  const map = new Map();
  for (const n of data.numbers) {
    const iso = n.countryCode;
    if (!iso || iso === 'XX') continue;
    const c = map.get(iso) || {
      iso, nameZh: n.countryNameZh, nameEn: n.countryNameEn,
      flag: n.flag, callingCode: n.callingCode,
      total: 0, directInbox: 0, active: 0, lowUsage: 0, unverified: 0,
    };
    c.total++;
    if (isDirect(n)) c.directInbox++;
    if (n.status === 'available') c.active++;
    else if (n.status === 'low_usage') c.lowUsage++;
    else c.unverified++;
    map.set(iso, c);
  }
  return [...map.values()].sort((a, b) => b.directInbox - a.directInbox || b.total - a.total || a.nameZh.localeCompare(b.nameZh, 'zh'));
}

/* ---------- 状态徽标 HTML ---------- */
export function statusHtml(n) {
  const st = n.status || 'unverified';
  return `<span class="st st-${esc(st)}">${esc(STATUS_LABEL[st] || '暂未验证')}</span>`;
}

/** 状态副文案：优先真实短信时间，其次活跃时间；无则说明未知，不编造 */
export function statusLine(n) {
  const t = n.lastSmsAt || n.lastMessageAt;
  if (t) {
    const r = relTime(t);
    if (r) return (n.status === 'available' ? '收到短信 ' : '最近活跃 ') + r;
  }
  if (n.status === 'available') return '近期有短信记录';
  if (n.status === 'low_usage') return '暂无近期活跃记录';
  return '暂无近期短信';
}

/* 短信量：只显示真实数字，缺则说明未提供 */
export function smsLine(n) {
  const v = n.smsToday ?? n.messageCount;
  if (v == null) return `<span class="na">短信数未提供</span>`;
  return `今日 ${Number(v).toLocaleString()} 条`;
}

/* ---------- 剪贴板 ---------- */
export async function copy(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (e) {
    // 回退：非安全上下文或权限被拒
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.cssText = 'position:fixed;opacity:0;pointer-events:none';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      ta.remove();
      return ok;
    } catch (e2) { return false; }
  }
}

/* ---------- Toast ---------- */
let toastEl = null, toastTimer = null;
export function toast(msg, kind = 'ok') {
  if (!toastEl) {
    toastEl = document.createElement('div');
    toastEl.className = 'toast';
    toastEl.setAttribute('role', 'status');
    toastEl.setAttribute('aria-live', 'polite');
    document.body.appendChild(toastEl);
  }
  toastEl.textContent = msg;
  toastEl.className = 'toast on ' + kind;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove('on'), 2200);
}

/* ---------- 导航渲染（多页共用） ---------- */
/* ---------- 素材助手 ---------- */
/** 内联 SVG 图标（从 assets/icons 读取需异步，此处用 sprite 方式按需加载） */
const ICON_CACHE = new Map();
export async function icon(name, cls = '') {
  if (!ICON_CACHE.has(name)) {
    try {
      const r = await fetch(`assets/icons/${name}.svg`);
      ICON_CACHE.set(name, r.ok ? await r.text() : '');
    } catch { ICON_CACHE.set(name, ''); }
  }
  const svg = ICON_CACHE.get(name);
  if (!svg) return '';
  return cls ? svg.replace('<svg ', `<svg class="${cls}" `) : svg;
}
/** 同步版本：从已缓存的图标拼 HTML（用于一次性渲染 chrome） */
export async function icons(list) {
  const out = {};
  await Promise.all(list.map(async n => { out[n] = await icon(n); }));
  return out;
}

/** 把页面上所有 [data-ic="name"] 占位替换成真实 SVG 图标 */
export async function fillIcons(root = document) {
  const slots = [...root.querySelectorAll('[data-ic]')];
  if (!slots.length) return;
  const names = [...new Set(slots.map(s => s.dataset.ic))];
  const map = await icons(names);
  slots.forEach(s => {
    const svg = map[s.dataset.ic];
    if (svg) s.innerHTML = svg;
  });
}

export function renderChrome(active = '') {
  const nav = [
    ['index.html', '首页', 'home'],
    ['numbers.html', '号码', 'numbers'],
    ['guide.html', '使用指南', 'guide'],
    ['faq.html', '常见问题', 'faq'],
  ];
  const hd = document.getElementById('hd');
  if (hd) {
    hd.innerHTML =
      `<div class="hd-in">
        <button class="burger" id="burger" aria-label="菜单" aria-expanded="false">☰</button>
        <a class="brand" href="index.html"><img class="brand-logo" src="assets/brand/logo.svg" alt="SMS Hub 免费在线接码" width="140" height="32"></a>
        <nav class="nav" id="nav" aria-label="主导航">
          ${nav.map(([h, t, k]) => `<a href="${h}"${k === active ? ' aria-current="page"' : ''}>${t}</a>`).join('')}
        </nav>
        <div class="hd-act">
          <a class="hd-search" href="numbers.html" data-icon="search">搜索国家或区号</a>
          <a class="btn btn-primary btn-sm" href="numbers.html">选号码</a>
          <button class="icon-btn" id="hdRefresh" title="刷新数据" aria-label="刷新数据" data-icon="refresh"></button>
        </div>
      </div>`;
    // 用真实图标替换占位
    (async () => {
      const map = await icons(['search', 'refresh']);
      const s = hd.querySelector('[data-icon="search"]');
      if (s && map.search) s.innerHTML = `${map.search}<span>搜索国家或区号</span>`;
      const rf = hd.querySelector('#hdRefresh');
      if (rf && map.refresh) rf.innerHTML = map.refresh.replace('<svg ', '<svg width="17" height="17" ');
    })();
    const b = hd.querySelector('#burger');
    b.onclick = () => {
      const n = hd.querySelector('#nav');
      const on = n.classList.toggle('open');
      b.setAttribute('aria-expanded', String(on));
    };
    const rf = hd.querySelector('#hdRefresh');
    rf.onclick = async () => {
      rf.disabled = true;
      rf.innerHTML = '<span class="spin"></span>';
      try {
        await loadData({ force: true });
        location.reload();
      } catch (e) { toast('刷新失败，请稍后重试', 'err'); rf.disabled = false; rf.textContent = '↻'; }
    };
  }

  const bn = document.getElementById('bnav');
  if (bn) {
    bn.innerHTML = `<div class="bnav-in">
      ${[['index.html', '首页', '⌂', 'home'], ['numbers.html', '号码', '▦', 'numbers'], ['guide.html', '指南', '◎', 'guide']]
        .map(([h, t, i, k]) => `<a href="${h}"${k === active ? ' aria-current="page"' : ''}><span class="i">${i}</span>${t}</a>`).join('')}
    </div>`;
  }
}

/* ---------- 页脚 ---------- */
export function renderFooter() {
  const ft = document.getElementById('ft');
  if (!ft) return;
  ft.innerHTML = `<div class="ft-in">
    <div class="ft-brand">
      <img src="assets/brand/logo.svg" alt="SMS Hub" width="132" height="30">
      <p style="margin:10px 0 0;color:var(--text-muted);font-size:13px;line-height:1.6">
        公共号码收到的短信任何人都可能看到，请勿用于银行、支付、邮箱或其他敏感账户。
      </p>
    </div>
    <div class="ft-links">
      <a href="index.html">首页</a>
      <a href="numbers.html">全部号码</a>
      <a href="guide.html">使用指南</a>
      <a href="faq.html">常见问题</a>
    </div>
  </div>`;
}

/* ---------- 卡片复制按钮绑定（事件委托） ---------- */
export function bindCopyButtons(root = document) {
  root.addEventListener('click', async e => {
    const b = e.target.closest('.cp');
    if (!b) return;
    e.preventDefault();
    const v = b.dataset.phone;
    const store = b.dataset.ic || b.dataset.icon || 'copy';
    const ok = await copy(v);
    if (ok) {
      b.classList.add('done');
      const ck = await icon('check');
      if (ck) b.innerHTML = ck;
      else b.textContent = '✓';
      setTimeout(async () => {
        b.classList.remove('done');
        const back = await icon(store);
        if (back) b.innerHTML = back;
        else b.textContent = '⧉';
      }, 1500);
      toast('号码已复制：' + v);
    } else {
      toast('复制失败，请手动选择号码', 'err');
    }
  });
}
