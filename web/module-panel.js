// 모듈 패널: 지금 코드베이스의 ln 모듈 지도. 지도 계산은 lnt 가 하고(서버가 lnt map --json 으로 받아 준다) 화면은 그리기만 한다
// 파일이 바뀌면 서버가 modules 알림을 보내고 다시 그린다. 지도는 파일을 직접 쓰지 않는다. 사용자가 한 일은 보내기에 실린다
// app.js 보다 먼저 읽힌다. app.js 의 전역(ui, sessions, cur, esc, api, LIVE, GEAR)은 함수 안에서만 쓴다
'use strict';

// 그려 둔 탭, 폴더별 노드 순서(새 모듈은 줄 끝에 붙여 기존 노드가 움직이지 않게), 마우스 미리보기
const MP = { tab: null, order: {}, hoverKey: null, hoverTimer: 0, peek: null, editing: null };

const mpNorm = p => String(p || '').replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase();
const mpShort = name => name.split('.').pop();

// 지도 받아 오기 --------------------------------------------------------------

function mpLoad(s) {
  if (!s || s.modules || s._mpLoading) return;
  if (!LIVE) {
    mpSet(s, window.MOCK_MODULES ? { status: 'ok', map: window.MOCK_MODULES } : { status: 'none' });
    return;
  }
  s._mpLoading = true;
  // 화면이 서버보다 새것일 수 있다. 예전 서버는 이 경로를 모르니 알림 창 없이 패널에만 적는다
  fetch(`/api/tabs/${s.id}/modules`).then(r => r.ok ? r.json() : null).then(data => {
    mpSet(s, data ? data.modules : { status: 'error', message: '서버가 모듈 지도를 모른다. 패널 서버를 다시 띄운다' });
  }).catch(() => mpSet(s, { status: 'error', message: '서버에 닿지 않는다' })).finally(() => {
    s._mpLoading = false;
    if (s.id === ui.cur) renderModules();
  });
}

// 새 지도. 파싱에 실패한 모듈은 그 파일의 import 가 빠져 나오므로 마지막으로 정상이던 간선을 이어 쓴다
function mpSet(s, result) {
  s.modules = result;
  s._mpIndex = null;
  s._mpStamp = Date.now();
}

// 서버 알림: 같은 폴더를 연 탭 모두에 적용한다
function onModulesEvent(msg) {
  let hit = false;
  sessions.filter(s => mpNorm(s.cwd) === mpNorm(msg.cwd)).forEach(s => { mpSet(s, msg.modules); if (s.id === ui.cur) hit = true; });
  if (hit) { renderModules(); mpTick(); }
}

// 지도 색인 -----------------------------------------------------------------

function mpIndex(s) {
  if (s._mpIndex) return s._mpIndex;
  const map = s.modules?.map;
  if (!map) return null;
  const mods = {};
  for (const m of map.modules || []) mods[m.name] = { ...m, bad: [], parseErr: false, orphan: false, kids: [] };
  for (const v of map.violations || []) {
    const m = mods[v.module];
    if (!m) continue;
    m.bad.push(v);
    if (v.code === 'E') m.parseErr = true;
  }
  for (const o of map.orphans || []) if (mods[o]) mods[o].orphan = true;
  for (const m of Object.values(mods)) if (m.scope && mods[m.scope]) mods[m.scope].kids.push(m.name);

  const good = s._mpGood ||= {};
  const edges = [];
  const seen = new Set();
  const add = e => {
    const key = `${e.src}>${e.dst}`;
    if (seen.has(key) || !mods[e.src] || !mods[e.dst]) return;
    seen.add(key);
    edges.push({ src: e.src, dst: e.dst });
  };
  const fresh = {};
  for (const e of map.edges || []) {
    if (e.kind === 'inherits') continue;
    add(e);
    (fresh[e.src] ||= []).push({ src: e.src, dst: e.dst });
  }
  for (const m of Object.values(mods)) {
    if (m.parseErr) (good[m.name] || []).forEach(add);
    else good[m.name] = fresh[m.name] || [];
  }

  // 노드 순서: 처음 본 순서를 기억하고 새 모듈은 뒤에 붙인다
  const order = MP.order[mpNorm(s.cwd)] ||= [];
  Object.keys(mods).sort().forEach(n => { if (!order.includes(n)) order.push(n); });
  const rank = Object.fromEntries(order.map((n, i) => [n, i]));
  s._mpIndex = { map, mods, edges, rank };
  return s._mpIndex;
}

function mpMembers(ix, id) {
  const out = new Set([id]);
  const walk = n => (ix.mods[n]?.kids || []).forEach(k => { out.add(k); walk(k); });
  walk(id);
  return out;
}
// 바깥으로 나가는 import. 중첩 모듈은 안쪽 모듈들의 import 를 합친다
function mpDeps(ix, id) {
  const mem = mpMembers(ix, id);
  return new Set(ix.edges.filter(e => mem.has(e.src) && !mem.has(e.dst)).map(e => e.dst));
}
// 영향 범위: 이 모듈(안쪽 포함)에 기대는 바깥 모듈. 안쪽 모듈에 기대면 그 중첩 모듈에도 기댄다
function mpUps(ix, id) {
  const mem = mpMembers(ix, id);
  const out = new Set();
  const stack = [...mem];
  while (stack.length) {
    const c = stack.pop();
    const ups = ix.edges.filter(e => e.dst === c).map(e => e.src);
    if (ix.mods[c]?.scope) ups.push(ix.mods[c].scope);
    for (const u of ups) if (!mem.has(u) && !out.has(u)) { out.add(u); stack.push(u); }
  }
  return out;
}

const mpOpenSet = s => {
  ui.mpOpen[s.id] ||= new Set(ui.rememberOpen ? JSON.parse(pref(`overseer.mpopen.${mpNorm(s.cwd)}`, '[]')) : []);
  return ui.mpOpen[s.id];
};
// 접힌 중첩 모듈 안의 모듈은 그 중첩 모듈로 보인다
function mpVisible(ix, open, id) {
  const m = ix.mods[id];
  if (m && m.scope && ix.mods[m.scope] && !open.has(m.scope)) return mpVisible(ix, open, m.scope);
  return id;
}

// 턴과 사안이 다룬 모듈 ------------------------------------------------------------

// 파일 경로가 속한 가장 안쪽 모듈
function mpModuleOf(s, ix, file) {
  const cwd = mpNorm(s.cwd);
  let rel = mpNorm(file);
  if (rel.startsWith(cwd + '/')) rel = rel.slice(cwd.length + 1);
  let best = null;
  for (const m of Object.values(ix.mods)) {
    const p = mpNorm(m.path);
    if ((rel === p || rel.startsWith(p + '/')) && (!best || p.length > mpNorm(best.path).length)) best = m;
  }
  return best?.name || null;
}
// 이번 턴(마지막 턴)에 고친 모듈
function mpTurnMods(s, ix) {
  const t = s.turns[s.turns.length - 1];
  return new Set((t?.files || []).map(f => mpModuleOf(s, ix, f)).filter(Boolean));
}
// 사안이 언급한 모듈: 점 경로(l1.cli_io), 백틱 안의 이름이나 경로. 이름이 겹치는 짧은 이름은 쓰지 않는다
function itemModules(s, item) {
  const ix = s.modules?.status === 'ok' && mpIndex(s);
  if (!ix) return [];
  const text = `${item.title}\n${item.body}`;
  const names = Object.keys(ix.mods);
  const byShort = {};
  names.forEach(n => (byShort[mpShort(n)] ||= []).push(n));
  const out = new Set(names.filter(n => n.includes('.') && new RegExp(`(^|[^\\w.])${n.replace(/\./g, '\\.')}(?![\\w])`).test(text)));
  for (const [, tok] of text.matchAll(/`([^`\n]+)`/g)) {
    const t = tok.trim().replace(/\\/g, '/');
    if (t.includes('/')) {
      const m = mpModuleOf(s, ix, t);
      if (m) { out.add(m); continue; }
      const seg = t.split('/').filter(Boolean);
      for (const part of seg) if (byShort[part]?.length === 1) out.add(byShort[part][0]);
    } else if (byShort[t]?.length === 1) out.add(byShort[t][0]);
  }
  // 안쪽 모듈과 그 바깥 중첩 모듈이 함께 걸리면 가장 안쪽 것만 남긴다
  return [...out].filter(n => ![...out].some(o => o !== n && o.startsWith(`${n}.`)));
}

// 보낼 것: 책임 수정, 모듈 질문, 새 책임 카드 ------------------------------------------------

const mpQueue = s => (s.map ||= { resp: {}, ask: {}, cards: [] });
function mapCount(s) {
  const q = s.map;
  return q ? Object.keys(q.resp).length + Object.keys(q.ask).length + q.cards.length : 0;
}
function mapLines(s) {
  const q = s.map;
  if (!q) return [];
  return [
    ...Object.entries(q.resp).map(([m, t]) => `[책임 수정] ${m}: ${t}`),
    ...Object.entries(q.ask).map(([m, t]) => `[모듈 질문] ${m}: ${t}`),
    ...q.cards.map(c => `[새 책임 카드] ${c.name ? `${c.name}: ` : ''}${c.resp} → 타당성, 이름과 경계, 놓을 층, 공용 모듈 사용, 하위 구성을 [제안]으로 올린다`),
  ];
}
function mapClear(s) { s.map = { resp: {}, ask: {}, cards: [] }; }

// 그리기 ------------------------------------------------------------------

const MP_LEGEND = `<div class="mp-legend">
  <span class="lg-turn"><b></b>이번 턴 수정</span><span class="lg-blast"><b></b>그 영향 범위</span>
  <span class="lg-bad"><b></b>위반·파싱 오류</span><span class="lg-orphan"><b></b>고아</span>
  <span class="lg-vocab"><b></b>l0 공용 모듈로 가는 선</span><span class="lg-layer"><b></b>층 경계</span></div>`;

const MP_STATUS = {
  none: '이 프로젝트는 ln 구조가 아니다 (src/&lt;패키지&gt;/lN 이 없다)',
  missing: 'lnt 명령이 없다. <code>uv tool install ff-lntools</code>',
  unsupported: 'lnt 가 <code>map --json</code> 을 모른다. ff-lntools 를 새 판으로 올린다',
};

function renderModules() {
  const host = $('#modhost');
  if (!host) return;
  const s = cur();
  MP.tab = ui.cur;
  if (!s) { host.innerHTML = ''; return; }
  mpLoad(s);
  const r = s.modules;
  const ix = r?.status === 'ok' ? mpIndex(s) : null;
  const scroll = $('#mp-scroll');
  const pos = scroll && MP.scrollFor === s.id ? [scroll.scrollLeft, scroll.scrollTop] : null;
  const bad = ix ? Object.values(ix.mods).reduce((n, m) => n + m.bad.length, 0) : 0;
  const info = !r ? '불러오는 중' : ix
    ? `<span class="live" id="mp-live"><i></i>LIVE</span> · 모듈 ${Object.keys(ix.mods).length} · 위반 ${bad} · ${esc(ix.map.package_root || '')}`
    : '';
  const open = mpOpenSet(s);
  const nests = ix ? Object.values(ix.mods).filter(m => m.nested) : [];
  host.innerHTML = `<section class="mod-pane">
    <header class="pane-bar"><span class="pane-name">모듈 패널</span><span class="pane-info">${info}</span>
      ${nests.length ? `<button class="bar-btn" data-mp-expand>${nests.every(m => open.has(m.name)) ? '모두 접기' : '모두 펼치기'}</button>` : ''}
      ${ix ? '<button class="bar-btn" data-mp-throw>+ 책임 카드</button>' : ''}
      <button class="pane-gear ${ui.drawer === 'map' ? 'on' : ''}" data-drawer="map" title="모듈 패널 설정">${GEAR}</button></header>
    ${ix ? MP_LEGEND : ''}
    <div class="mp-scroll" id="mp-scroll">${ix ? mpMapHTML(s, ix, open) : `<div class="empty">${!r ? '모듈 지도를 불러오는 중' : MP_STATUS[r.status] || esc(r.message || '모듈 지도를 받지 못했다')}</div>`}</div>
    <div class="mp-detail" id="mp-detail" hidden></div>
    <form class="mp-throw" id="mp-throw" ${ui.mpThrow ? '' : 'hidden'}>
      <div class="ps-title">책임 카드 던지기</div>
      <label>모듈 이름 (선택)<input name="name" placeholder="비우면 에이전트가 이름과 경계를 제안" autocomplete="off"></label>
      <label>책임 (필수)<textarea name="resp" placeholder="무엇을 맡는지. 예: 에이전트의 보고를 슬랙 채널로 전달한다"></textarea></label>
      <div class="mp-hint">놓을 자리(층, 중첩, 공용 모듈 사용)는 정하지 않는다. 보내면 에이전트가 타당성 분석과 함께 [제안]으로 올린다.</div>
      <div class="row-btns"><button type="button" data-mp-cancel>취소</button><button type="submit" class="primary">넣기</button></div>
    </form>
  </section>`;
  host.style.setProperty('--mfs', `${ui.fs.map}px`);
  if (ui.mpPin && ix && !ix.mods[ui.mpPin]) ui.mpPin = null;
  if (ui.mpPin) mpShowDetail(s, ui.mpPin);
  const sc = $('#mp-scroll');
  MP.scrollFor = s.id;
  if (pos) { sc.scrollLeft = pos[0]; sc.scrollTop = pos[1]; }
  requestAnimationFrame(mpRepaint);
}

function mpChips(s, m) {
  const q = s.map || { resp: {}, ask: {} };
  const c = [...new Set(m.bad.map(v => v.code))].map(code => `<span class="chip c-bad">${code === 'E' ? '파싱 실패' : code}</span>`);
  if (m.orphan) c.push('<span class="chip c-orphan">고아</span>');
  if (q.resp[m.name]) c.push('<span class="chip c-wait">수정 대기</span>');
  if (q.ask[m.name]) c.push('<span class="chip c-wait">질문 대기</span>');
  if (m.external) c.push('<span class="chip c-ext">+ext</span>');
  return c.join('');
}
function mpResp(s, m) {
  const want = s.map?.resp[m.name];
  if (want) return `<div class="n-resp pending">${esc(want)}</div>`;
  return m.responsibility ? `<div class="n-resp">${esc(m.responsibility)}</div>` : '<div class="n-resp empty">책임 한 줄 없음</div>';
}
function mpNodeHTML(s, ix, name) {
  const m = ix.mods[name];
  const cls = ['node', m.bad.length && 'bad', m.parseErr && 'parse-err', m.orphan && 'orphan'].filter(Boolean).join(' ');
  return `<div class="${cls}" data-mod-id="${esc(name)}"><div class="n-head"><span class="n-name">${esc(mpShort(name))}</span><span class="n-path">l${m.layer}</span></div>${mpResp(s, m)}<div class="chips">${mpChips(s, m)}</div></div>`;
}
function mpNestHTML(s, ix, open, name) {
  const m = ix.mods[name];
  const all = [...mpMembers(ix, name)].filter(n => n !== name);
  const bad = all.filter(n => ix.mods[n].bad.length).length;
  const isOpen = open.has(name);
  const chips = [mpChips(s, m), `<span class="chip c-orphan">안쪽 ${m.kids.length}</span>`,
    bad && !isOpen ? `<span class="chip c-bad">안쪽 위반 ${bad}</span>` : ''].join('');
  const cls = ['nest', isOpen && 'open', (bad && !isOpen || m.bad.length) && 'bad'].filter(Boolean).join(' ');
  return `<div class="${cls}" data-nest="${esc(name)}"><div class="nest-head" data-mod-id="${esc(name)}"><div class="n-head"><span class="n-name">${esc(mpShort(name))}</span><span class="n-path">l${m.layer} · 중첩</span><button class="nest-tog" data-mp-tog="${esc(name)}">${isOpen ? '접기' : '펼치기'}</button></div>${mpResp(s, m)}<div class="chips">${chips}</div></div>
    ${isOpen ? `<div class="nest-body">${mpRowsHTML(s, ix, open, m.kids, true)}</div>` : ''}</div>`;
}
function mpRowsHTML(s, ix, open, names, inner) {
  const layers = [...new Set(names.map(n => ix.mods[n].layer))].sort((a, b) => b - a);
  return layers.map(n => {
    const row = names.filter(k => ix.mods[k].layer === n).sort((a, b) => ix.rank[a] - ix.rank[b]);
    return `<div class="row"><div class="row-label">${inner ? 'l' : 'L'}${n}</div><div class="row-nodes">${row.map(k => ix.mods[k].nested ? mpNestHTML(s, ix, open, k) : mpNodeHTML(s, ix, k)).join('')}</div></div>`;
  }).join('');
}
function mpMapHTML(s, ix, open) {
  const cards = s.map?.cards || [];
  const tray = cards.length ? `<div class="row tray"><div class="row-label">제안 대기</div><div class="row-nodes">${cards.map((g, i) => `<div class="node ghost">
      <div class="n-head"><span class="n-name">${esc(g.name || '(이름 제안 대기)')}</span><span class="n-path">층 미정</span><button class="x" data-mp-uncard="${i}" title="빼기">×</button></div>
      <div class="n-resp">${esc(g.resp)}</div><div class="chips"><span class="chip c-wait">보낼 예정</span></div></div>`).join('')}</div></div>` : '';
  const top = Object.keys(ix.mods).filter(n => !ix.mods[n].scope || !ix.mods[ix.mods[n].scope]);
  return `<div class="map" id="mp-map"><svg class="edges" id="mp-edges"></svg>${tray}${mpRowsHTML(s, ix, open, top, false)}</div>`;
}

const mpEl = id => document.querySelector(`#mp-map [data-mod-id="${CSS.escape(id)}"]`);
const mpHolder = id => { const e = mpEl(id); return e?.classList.contains('nest-head') ? e.parentElement : e; };

// 강조할 대상. 마우스 미리보기 > 누른 모듈 > 커맨드 패널에서 고른 카드가 언급한 모듈
function mpFocus(s, ix) {
  const f = MP.peek || (ui.mpPin ? { mod: ui.mpPin } : null) || (ui.active && findItem(s, ui.active) ? { mods: itemModules(s, findItem(s, ui.active)) } : null);
  if (!f) return null;
  if (f.mod) return ix.mods[f.mod] ? { mem: mpMembers(ix, f.mod), deps: mpDeps(ix, f.mod), ups: mpUps(ix, f.mod), sel: [f.mod] } : null;
  if (!f.mods.length) return null;
  const mem = new Set();
  f.mods.forEach(m => mpMembers(ix, m).forEach(x => mem.add(x)));
  return { mem, deps: new Set(), ups: new Set(), sel: f.mods };
}

// 이번 턴, 영향 범위, 선택 강조와 의존선. 다시 그리지 않고 칠만 한다
function mpRepaint() {
  const s = cur();
  const map = $('#mp-map');
  if (!s || !map || MP.tab !== s.id) return;
  const ix = mpIndex(s);
  if (!ix) return;
  const open = mpOpenSet(s);
  const vis = id => mpVisible(ix, open, id);
  map.querySelectorAll('.turn,.blast,.sel,.lit').forEach(n => n.classList.remove('turn', 'blast', 'sel', 'lit'));
  const edited = mpTurnMods(s, ix);
  const turnVis = new Set([...edited].map(vis));
  turnVis.forEach(v => mpHolder(v)?.classList.add('turn'));
  if (ui.showBlast) {
    const blast = new Set();
    edited.forEach(m => mpUps(ix, m).forEach(u => blast.add(vis(u))));
    blast.forEach(v => { if (!turnVis.has(v)) mpHolder(v)?.classList.add('blast'); });
  }
  const fs = mpFocus(s, ix);
  map.classList.toggle('dim', !!fs);
  if (fs) {
    fs.sel.forEach(id => mpHolder(vis(id))?.classList.add('sel'));
    [...fs.mem, ...fs.deps, ...fs.ups].forEach(id => mpHolder(vis(id))?.classList.add('lit'));
  }
  mpDrawEdges(s, ix, open, fs);
}

function mpDrawEdges(s, ix, open, fs) {
  const svg = $('#mp-edges');
  const map = $('#mp-map');
  if (!svg || !map) return;
  const base = map.getBoundingClientRect();
  svg.setAttribute('width', map.scrollWidth);
  svg.setAttribute('height', map.scrollHeight);
  const drawn = new Map();
  for (const { src, dst } of ix.edges) {
    const vs = mpVisible(ix, open, src);
    const vd = mpVisible(ix, open, dst);
    if (vs === vd) continue;
    const a = mpEl(vs);
    const b = mpEl(vd);
    if (!a || !b) continue;
    const cls = [];
    const d = ix.mods[dst];
    if (ui.vocabFaint && (!d.scope || !ix.mods[d.scope]) && d.layer === 0) cls.push('vocab');
    if (ix.mods[src].scope && ix.mods[src].scope === d.scope) cls.push('inner');
    let rank = 0;
    if (fs) {
      if (fs.mem.has(src) && !fs.mem.has(dst)) { cls.push('dep'); rank = 3; }
      else if (fs.ups.has(src) && (fs.mem.has(dst) || fs.ups.has(dst))) { cls.push('blast'); rank = 2; }
      else if (fs.mem.has(src) && fs.mem.has(dst)) { cls.push('own'); rank = 1; }
      else cls.push('faded');
    }
    // 접혀서 같은 선으로 겹치면 더 강조된 쪽을 남긴다
    const key = `${vs}>${vd}`;
    if (drawn.has(key) && drawn.get(key).rank >= rank) continue;
    const ra = a.getBoundingClientRect();
    const rb = b.getBoundingClientRect();
    const x1 = ra.left + ra.width / 2 - base.left;
    const y1 = ra.bottom - base.top;
    const x2 = rb.left + rb.width / 2 - base.left;
    const y2 = rb.top - base.top;
    const dy = Math.max(26, (y2 - y1) / 2);
    const c = cls.join(' ');
    drawn.set(key, { rank, svg: `<path class="${c}" d="M${x1},${y1} C${x1},${y1 + dy} ${x2},${y2 - dy} ${x2},${y2}"/><circle class="${c}" cx="${x2}" cy="${y2}" r="2.6"/>` });
  }
  svg.innerHTML = [...drawn.values()].sort((x, y) => x.rank - y.rank).map(x => x.svg).join('');
}

function mpTick() {
  const l = $('#mp-live');
  if (!l) return;
  l.classList.remove('tick');
  void l.offsetWidth;
  l.classList.add('tick');
}

// 모듈 상세 ---------------------------------------------------------------

function mpShowDetail(s, id) {
  const box = $('#mp-detail');
  const ix = mpIndex(s);
  const m = ix?.mods[id];
  if (!box || !m) { if (box) box.hidden = true; return; }
  const q = mpQueue(s);
  const items = allItems(s).filter(i => itemModules(s, i).some(x => x === id || mpMembers(ix, id).has(x)));
  const recs = (s.records || []).filter(r => r.status === 'active' && `${r.text} ${r.note || ''}`.includes(mpShort(id)));
  const where = m.bad.map(v => `<span class="bad">${esc(v.code)} ${esc(v.message)}${v.line > 0 ? ` (${esc(v.file)}:${v.line})` : ''}</span>`).join('<br>');
  const edit = MP.editing?.id === id ? MP.editing.kind : null;
  box.innerHTML = `
    <h3>${esc(id)}<button class="x" data-mp-close>×</button></h3>
    <div class="d-resp">${m.responsibility ? esc(m.responsibility) : '<i>책임 한 줄 없음</i>'}</div>
    <dl>
      <dt>구분</dt><dd>${m.nested ? '중첩 모듈' : '모듈'}${m.orphan ? ' · 고아' : ''}${m.external ? ' · 외부 패키지 사용' : ''}</dd>
      <dt>층</dt><dd>선언 l${m.layer}${m.computed != null && m.computed !== m.layer ? ` · 계산 l${m.computed}` : ''}${where ? `<br>${where}` : ''}</dd>
      <dt>의존</dt><dd>${[...mpDeps(ix, id)].map(esc).join(', ') || '-'}</dd>
      <dt>영향 범위</dt><dd>${[...mpUps(ix, id)].map(esc).join(', ') || '-'}</dd>
      <dt>위치</dt><dd>${esc(m.path)}</dd>
    </dl>
    ${recs.length ? '<div class="d-sec">결정 기록</div>' + recs.map(r => `<div class="rec"><code>${esc(r.ref)}</code> ${esc(r.text)}</div>`).join('') : ''}
    ${items.length ? '<div class="d-sec">언급한 사안</div>' + items.map(i => `<div class="rec"><button class="parent" data-jump="${esc(i.id)}">#${esc(i.id)}</button> ${esc(i.title)}</div>`).join('') : ''}
    ${q.resp[id] ? `<div class="queued"><span>책임 수정 보낼 예정: ${esc(q.resp[id])}</span><button data-mp-unq="resp">×</button></div>` : ''}
    ${q.ask[id] ? `<div class="queued"><span>질문 보낼 예정: ${esc(q.ask[id])}</span><button data-mp-unq="ask">×</button></div>` : ''}
    ${edit ? `<div class="inline"><textarea class="note" data-mp-text placeholder="${edit === 'resp' ? '새 책임 한 줄. 무엇을 하는지가 아니라 무엇을 맡는지' : '이 모듈에 대해 물을 것'}">${esc(edit === 'resp' ? (q.resp[id] || m.responsibility || '') : (q.ask[id] || ''))}</textarea>
      <div class="row-btns"><button data-mp-inline="cancel">취소</button><button data-mp-inline="ok" class="primary">넣기</button></div></div>`
      : '<div class="acts"><button data-mp-act="resp">책임 고치기</button><button data-mp-act="ask">이 모듈에 대해 묻기</button></div>'}`;
  box.hidden = false;
  box.dataset.id = id;
  if (edit) box.querySelector('[data-mp-text]')?.focus();
}

// 마우스를 잠시 올려 두면 임시로 그 대상을 강조하고, 벗어나면 고정한 상태로 돌아간다
function mpHover(key, f) {
  if (key === MP.hoverKey) return;
  MP.hoverKey = key;
  clearTimeout(MP.hoverTimer);
  if (MP.peek) { MP.peek = null; mpRepaint(); }
  if (key) MP.hoverTimer = setTimeout(() => { MP.peek = f; mpRepaint(); }, ui.peekDelay * 1000);
}

// 모듈을 눌러 고정. 같은 것을 다시 누르면 풀린다
function mpPin(id) {
  const s = cur();
  ui.mpPin = ui.mpPin === id ? null : id;
  MP.peek = null;
  MP.editing = null;
  if (ui.mpPin) mpShowDetail(s, ui.mpPin); else $('#mp-detail').hidden = true;
  mpRepaint();
}

// Esc: 책임 카드 창, 그다음 고정한 모듈. 처리했으면 true
function mpEsc() {
  if (ui.mpThrow) { ui.mpThrow = false; $('#mp-throw').hidden = true; return true; }
  if (ui.mpPin || MP.peek) {
    ui.mpPin = null;
    MP.peek = null;
    MP.editing = null;
    if ($('#mp-detail')) $('#mp-detail').hidden = true;
    mpRepaint();
    return false;
  }
  return false;
}

function mpSaved(s) {
  saveDraft(s);
  renderModules();
  refreshLive(s, null);
}

// 이벤트 -----------------------------------------------------------------

document.addEventListener('click', e => {
  const s = cur();
  if (!s) return;
  // 커맨드 패널 카드의 모듈 칩: 그 모듈을 펼쳐 고정하고 보이게 한다
  const chip = e.target.closest('[data-mod]');
  if (chip) {
    const ix = mpIndex(s);
    const id = chip.dataset.mod;
    if (!ix?.mods[id]) return;
    const open = mpOpenSet(s);
    for (let p = ix.mods[id].scope; p && ix.mods[p]; p = ix.mods[p].scope) open.add(p);
    ui.mpPin = null;
    renderModules();
    mpPin(id);
    mpHolder(id)?.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' });
    return;
  }
  // 커맨드 패널 카드를 고르면 그 카드가 언급한 모듈을 보인다
  if (e.target.closest('.cmd-pane .card[data-id]') && ui.mpPin) {
    ui.mpPin = null;
    if ($('#mp-detail')) $('#mp-detail').hidden = true;
  }
  if (!e.target.closest('#modhost')) return;
  const ix = mpIndex(s);
  const t = e.target;
  if (t.closest('[data-mp-tog]')) {
    const id = t.closest('[data-mp-tog]').dataset.mpTog;
    const open = mpOpenSet(s);
    open.has(id) ? open.delete(id) : open.add(id);
    if (ui.rememberOpen) savePref(`overseer.mpopen.${mpNorm(s.cwd)}`, JSON.stringify([...open]));
    renderModules();
  } else if (t.closest('[data-mp-expand]')) {
    const open = mpOpenSet(s);
    const nests = Object.values(ix.mods).filter(m => m.nested).map(m => m.name);
    if (nests.every(n => open.has(n))) open.clear(); else nests.forEach(n => open.add(n));
    if (ui.rememberOpen) savePref(`overseer.mpopen.${mpNorm(s.cwd)}`, JSON.stringify([...open]));
    renderModules();
  } else if (t.closest('[data-mp-throw]')) {
    ui.mpThrow = !ui.mpThrow;
    $('#mp-throw').hidden = !ui.mpThrow;
    if (ui.mpThrow) $('#mp-throw [name=resp]').focus();
  } else if (t.closest('[data-mp-cancel]')) {
    ui.mpThrow = false;
    $('#mp-throw').hidden = true;
  } else if (t.closest('[data-mp-uncard]')) {
    mpQueue(s).cards.splice(Number(t.closest('[data-mp-uncard]').dataset.mpUncard), 1);
    mpSaved(s);
  } else if (t.closest('[data-mp-close]')) {
    mpPin(ui.mpPin);
  } else if (t.closest('[data-mp-unq]')) {
    delete mpQueue(s)[t.closest('[data-mp-unq]').dataset.mpUnq][ui.mpPin];
    mpSaved(s);
  } else if (t.closest('[data-mp-act]')) {
    MP.editing = { id: ui.mpPin, kind: t.closest('[data-mp-act]').dataset.mpAct };
    mpShowDetail(s, ui.mpPin);
  } else if (t.closest('[data-mp-inline]')) {
    const ok = t.closest('[data-mp-inline]').dataset.mpInline === 'ok';
    const text = ($('#mp-detail [data-mp-text]')?.value || '').trim();
    if (ok && text) mpQueue(s)[MP.editing.kind][MP.editing.id] = text;
    MP.editing = null;
    if (ok && text) mpSaved(s); else mpShowDetail(s, ui.mpPin);
  } else if (t.closest('#mp-map .node:not(.ghost), #mp-map .nest-head')) {
    mpPin(t.closest('[data-mod-id]').dataset.modId);
  }
});

document.addEventListener('submit', e => {
  if (e.target.id !== 'mp-throw') return;
  e.preventDefault();
  const s = cur();
  const f = e.target;
  const resp = f.resp.value.trim();
  if (!resp) { f.resp.focus(); return; }
  mpQueue(s).cards.push({ name: f.name.value.trim(), resp });
  ui.mpThrow = false;
  mpSaved(s);
});

// 모듈과 커맨드 패널 카드 위에 마우스를 잠시 올려 두면 미리 보인다
document.addEventListener('pointerover', e => {
  const s = cur();
  if (!s || !$('#mp-map')) return;
  const node = e.target.closest('#mp-map .node:not(.ghost), #mp-map .nest-head');
  if (node) { mpHover(`m:${node.dataset.modId}`, { mod: node.dataset.modId }); return; }
  const card = e.target.closest('.cmd-pane .card[data-id]');
  const item = card && findItem(s, card.dataset.id);
  if (item) { mpHover(`c:${item.id}`, { mods: itemModules(s, item) }); return; }
  mpHover(null);
});

window.addEventListener('resize', () => requestAnimationFrame(mpRepaint));
