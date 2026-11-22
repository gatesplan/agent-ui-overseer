// 스펙 패널: 모듈 패널 자리에서 [모듈 | 스펙] 으로 바꿔 보는 구성요소별 동작 트리
// 프로젝트 아래 용어와 구성요소, 구성요소 아래 위에서부터 설명, 하위 구성요소, 목업, 하는 것, 하지 않는 것. 화면에 보이는 한 줄이 그 항목의 전부다
// 설명은 그 구성요소가 무엇인지 적는 글이고, 하는 것(기능)은 만들어야 할 동작이다
// 하는 것 오른쪽에는 그것이 실행되면 이어서 일어나는 일(then)을 "이어서" 줄로 잇는다
// 사람은 보는 방식을 바꾸고(선택, 접기, 화면 이동과 확대), 개체를 더블클릭해 글을 고치거나 고른 개체 아래에 자식을 더한다
// 개체를 끌어 다른 개체 위에 놓으면 자식째 그 아래로 옮긴다. 구성요소를 빈 곳에 놓으면 화면 배치만 하위째 옮긴다
// 개체를 고른 뒤에는 방향키로 옮겨 다니고 Enter 로 접고 편다
// 고치거나 더하거나 지우거나 옮긴 것은 서버가 spec.json 에 쓰고, 보내기에 [스펙 수정] [스펙 추가] [스펙 삭제] [스펙 이동] 줄로 실려 에이전트에게 간다
// 누른다고 창이 뜨지 않는다. 목업은 새 탭으로 연다
// 패널에서 한 고치기, 더하기, 삭제, 옮기기는 Ctrl+Z 로 되돌리고 Ctrl+Shift+Z 로 다시 한다. 에이전트가 MCP 로 고친 것은 되돌리지 않는다
// module-panel.js 다음, app.js 보다 먼저 읽힌다. app.js 의 전역(ui, sessions, cur, esc, LIVE, pref, savePref, api, saveDraft, refreshLive)은 함수 안에서만 쓴다
'use strict';

const SP_ROOT_W = 320, SP_COMP_W = 250, SP_COMP_H = 44, SP_ROW_W = 300, SP_ROW_H = 36;
const SP_GAP_ROOT = 96, SP_GAP = 64, SP_THEN_GAP = 72, SP_COMP_GAP = 26, SP_SUB_GAP = 14, SP_GROUP_GAP = 8;
const SP_HOME = { panX: 16, panY: 22, zoom: 1 };
// 탭별 보기, 프로젝트별 화면 위치와 끌어 옮긴 자리, 끌기 상태, 탭별 실행취소 기록, 서버에 쓰는 중인 요청 수
const SP = { view: {}, cam: {}, off: {}, drag: null, dragMoved: false, hist: {}, writing: 0 };

const SP_ICON = {
  root: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="13"/><path d="M8 21h8M12 17v4M7 9l3 2-3 2M12 13h4"/></svg>',
  term: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v16H5.5A1.5 1.5 0 0 1 4 18.5z"/><path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H13v16h5.5a1.5 1.5 0 0 0 1.5-1.5z"/></svg>',
  comp: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2 3 7v10l9 5 9-5V7z"/><path d="M3 7l9 5 9-5M12 12v10"/></svg>',
  do: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  dont: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><path d="M6 6l12 12"/></svg>',
  desc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 6.5h14M5 12h14M5 17.5h9"/></svg>',
  mock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16"/><path d="M3 9h18M7 6.5h.01M10 6.5h.01"/></svg>',
};
const SP_LEGEND = `<div class="sp-legend">
  <span><b class="lg-term"></b>용어</span><span><b class="lg-comp"></b>구성요소</span><span><b class="lg-desc"></b>설명</span>
  <span><b class="lg-mock"></b>목업 (새 탭으로 열림)</span><span><b class="lg-do"></b>하는 것</span><span><b class="lg-dont"></b>하지 않는 것</span></div>`;

// 보기 전환 ------------------------------------------------------------------

// 왼쪽 패널에 무엇을 보일지. 이 탭에서 고른 것 > 이 폴더에서 마지막으로 본 것 > 모듈
function spView(s) {
  return SP.view[s.id] ?? pref(`overseer.leftview.${mpNorm(s.cwd)}`, 'mod');
}
function spSetView(s, view) {
  SP.view[s.id] = view;
  savePref(`overseer.leftview.${mpNorm(s.cwd)}`, view);
}
// 두 패널의 머리줄 맨 앞에 같은 단추를 둔다
function spToggleHTML(view) {
  return `<div class="sp-seg2" role="group" aria-label="왼쪽 패널 보기"><button type="button" class="${view === 'mod' ? 'on' : ''}" data-sp-view="mod">모듈</button><button type="button" class="${view === 'spec' ? 'on' : ''}" data-sp-view="spec">스펙</button></div>`;
}

// 스펙 받아 오기 ----------------------------------------------------------------

// 프로젝트 루트의 spec.json. 처음 한 번 받고, 그 뒤 바뀐 것은 spec 알림으로 온다
function spLoad(s) {
  if (s.spec || s._spLoading) return;
  if (!LIVE) {
    s.spec = window.MOCK_SPEC ? { status: 'ok', spec: window.MOCK_SPEC } : { status: 'none' };
    return;
  }
  s._spLoading = true;
  const id = s.id;
  // 받는 사이 탭 알림으로 세션 객체가 새로 만들어질 수 있어 끝날 때 id 로 다시 찾는다
  const done = spec => {
    const t = sessions.find(x => x.id === id);
    if (!t) return;
    t.spec = spec;
    t._spLoading = false;
    if (id === ui.cur && spView(t) === 'spec') renderModules();
  };
  // 화면이 서버보다 새것일 수 있다. 예전 서버는 이 경로를 모른다
  fetch(`/api/tabs/${id}/spec`).then(r => r.ok ? r.json() : null)
    .then(data => done(data?.spec || { status: 'error', message: '서버가 스펙을 모른다. 패널 서버를 다시 띄운다' }))
    .catch(() => done({ status: 'error', message: '서버에 닿지 않는다' }));
}

// 탭 알림 연결이 다시 붙으면 부른다. 서버가 새로 떴으면 받아 둔 스펙(실패 포함)이 낡았고 바뀜 알림 대상에서도 빠졌으니 다시 받는다
function spReset() {
  sessions.forEach(s => { s.spec = null; s._spIx = null; s._spLoading = false; });
  const s = cur();
  if (s && spView(s) === 'spec') renderModules();
}

// 서버 알림: spec.json 이 바뀌면(생기거나 지워진 것 포함) 같은 폴더를 연 탭 모두에 적용한다
function onSpecEvent(msg) {
  let hit = false;
  sessions.filter(s => mpNorm(s.cwd) === mpNorm(msg.cwd)).forEach(s => { s.spec = msg.spec; if (s.id === ui.cur) hit = true; });
  if (hit && spView(cur()) === 'spec') renderModules();
}

// 목업 주소. 스킴이 있으면(https: 등) 그대로 열고, 없으면 프로젝트 안 파일 경로라 패널 서버가 내준다
// 목업 모드에서는 web/ 기준 상대 경로 그대로 연다
function spHref(s, href) {
  if (!href) return '#';
  if (!LIVE || /^[a-z][a-z0-9+.-]+:/i.test(href)) return href;
  const [, path, rest] = href.replace(/\\/g, '/').match(/^([^?#]*)(.*)$/);
  const rel = path.replace(/^(\.?\/)+/, '').split('/').map(encodeURIComponent).join('/');
  return `/api/tabs/${encodeURIComponent(s.id)}/files/${rel}${rest}`;
}

// 받은 스펙을 노드로 편다. 노드 이름은 구성요소 이름을 이은 경로라 접은 상태가 순서 변경에도 따라간다
function spIndex(s) {
  if (s._spIx?.src === s.spec) return s._spIx;
  const spec = s.spec?.status === 'ok' ? s.spec.spec : null;
  if (!spec) return null;
  const index = {};
  // p 는 스펙 JSON 안의 자리(['components', 0, 'does', 1] 처럼 키와 순번). 고치거나 더할 때 서버에 그대로 보낸다
  const root = { id: 'root', kind: 'root', p: [], t: spec.title || '', b: spec.summary || '' };
  index.root = root;
  root.w = (spec.terms || []).map((w, i) => (index[`w:${i}`] = { id: `w:${i}`, kind: 'term', p: ['terms', i], word: w.word, meaning: w.meaning, t: `${w.word}: ${w.meaning}`, parent: root }));
  const comp = (c, parent, path, p) => {
    const n = { id: `c:${path}`, kind: 'comp', p, t: c.name, parent };
    index[n.id] = n;
    const leaf = (kind, tag, key) => (x, i) => {
      const l = typeof x === 'string' ? { t: x } : { t: x.name, href: spHref(s, x.href) };
      Object.assign(l, { id: `${n.id}:${tag}${i}`, kind, p: [...p, key, i], parent: n });
      index[l.id] = l;
      return l;
    };
    // 하는 것은 이어서 일어나는 일(th)을 달고 다닌다. 그 노드 이름은 부모 이름 뒤에 .순번. tp 는 글이 놓인 자리
    const doLeaf = (x, id, parent, lp) => {
      const l = { id, kind: 'do', p: lp, tp: typeof x === 'string' ? lp : [...lp, 'text'], t: typeof x === 'string' ? x : x.text, parent };
      index[id] = l;
      l.th = (typeof x === 'string' ? [] : x.then || []).map((y, j) => doLeaf(y, `${id}.${j}`, l, [...lp, 'then', j]));
      return l;
    };
    n.d = (c.descs || []).map(leaf('desc', 'd', 'descs'));
    n.m = (c.mocks || []).map(leaf('mock', 'm', 'mocks'));
    n.f = (c.does || []).map((x, i) => doLeaf(x, `${n.id}:f${i}`, n, [...p, 'does', i]));
    n.n = (c.donts || []).map(leaf('dont', 'n', 'donts'));
    n.c = (c.children || []).map((k, i) => comp(k, n, `${path}/${k.name}`, [...p, 'children', i]));
    return n;
  };
  root.c = (spec.components || []).map((c, i) => comp(c, root, c.name, ['components', i]));
  const stats = { terms: root.w.length, comps: 0, desc: 0, do: 0, dont: 0, mock: 0 };
  (function walk(list) { list.forEach(c => { stats.comps++; stats.desc += c.d.length; stats.do += spCountDo(c.f); stats.dont += c.n.length; stats.mock += c.m.length; walk(c.c); }); })(root.c);
  return (s._spIx = { src: s.spec, root, index, stats });
}
const spCountDo = list => list.reduce((k, l) => k + 1 + spCountDo(l.th), 0);
// 구성요소 아래 개체 수(하위 구성요소 아래까지)
const spCountSub = c => c.d.length + c.m.length + spCountDo(c.f) + c.n.length + c.c.reduce((k, s) => k + 1 + spCountSub(s), 0);
const spSame = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// 보낼 것: 사용자가 고치거나 더하거나 지우거나 옮긴 개체 ------------------------------------------------
// 파일은 이미 바뀌었다. 에이전트가 알도록 다음 보내기에 한 줄씩 싣는다
// [스펙 수정] 기능 (좌측 패널 > 스펙 패널): "옛 글" → "새 글", [스펙 추가] 구성요소 (프로젝트): "헤더"
// [스펙 이동] 기능 (좌측 패널 > 스펙 패널): "글" → 이어서 기능 (커맨드 패널 > "다른 기능")

// 줄에 쓰는 자리: 그 개체까지 이어진 구성요소 이름
const spCrumb = n => { const names = []; for (let c = n; c && c.kind !== 'root'; c = c.parent) if (c.kind === 'comp') names.unshift(c.t); return names.join(' > '); };
const spDoWhere = parent => parent.kind === 'do' ? { label: '이어서 기능', crumb: `${spCrumb(parent)} > "${parent.t}"` } : { label: '기능', crumb: spCrumb(parent) };
// 구성요소 아래 한 줄 개체의 이름
const SP_LEAF_LABEL = { desc: '설명', dont: '하지 않는 것', mock: '목업' };
function spWhereOf(n) {
  if (n.kind === 'term') return { label: '용어', crumb: '' };
  if (n.kind === 'comp') return { label: '구성요소', crumb: spCrumb(n.parent) || '프로젝트' };
  if (n.kind === 'do') return spDoWhere(n.parent);
  return { label: SP_LEAF_LABEL[n.kind], crumb: spCrumb(n.parent) };
}
// 고른 개체(parent) 아래에 더할 자식의 자리
function spWhereNew(parent, kind) {
  if (kind === 'term') return { label: '용어', crumb: '' };
  if (kind === 'component') return { label: '구성요소', crumb: spCrumb(parent) || '프로젝트' };
  if (kind === 'do') return spDoWhere(parent);
  return { label: SP_LEAF_LABEL[kind], crumb: spCrumb(parent) };
}
const spWhereText = w => `${w.label}${w.crumb ? ` (${w.crumb})` : ''}`;

// 줄의 자리는 보낼 때 지금 스펙에서 다시 읽는다. 구성요소 이름을 바꿔도 그 아래에 더한 줄이 새 이름을 따른다
// 개체를 찾지 못했거나(에이전트가 옮겼다) 글이 달라졌으면 적어 둘 때의 자리를 쓴다. 지운 개체는 적어 둔 자리 그대로다
const spFind = (s, p) => Object.values(spIndex(s)?.index || {}).find(x => spSame(x.p, p));
function spWhereNow(s, e) {
  if (!e.p || e.op === 'remove') return e;
  const n = spFind(s, e.p);
  return n && n.t === e.text ? spWhereOf(n) : e;
}

// 옮긴 줄은 옮기기 전 자리(from)를 적어 둘 때 그대로 쓰고, 옮긴 자리만 지금 스펙에서 다시 읽는다
function specLines(s) {
  return (s.specq || []).map(e => {
    const where = spWhereText(spWhereNow(s, e));
    if (e.op === 'add') return `[스펙 추가] ${where}: "${e.text}"`;
    if (e.op === 'remove') return `[스펙 삭제] ${where}: "${e.text}"`;
    if (e.op === 'move') return `[스펙 이동] ${spWhereText(e.from)}: "${e.text}" → ${where}`;
    return `[스펙 수정] ${where}: "${e.old}" → "${e.text}"`;
  });
}
const specCount = s => (s.specq || []).length;
// 보내고 나면 줄을 비운다. 그 전에 한 일을 되돌리면 그때의 줄 목록으로 돌아가지 않고 새 줄로 알린다
function specClear(s) { s.specq = []; spHist(s.id).gen++; }

// 같은 개체를 여러 번 고치면 한 줄로 합친다(처음 글 → 마지막 글). 더한 개체를 고치면 더한 줄의 글이 바뀐다. 처음 글로 돌아오면 줄을 뺀다
function spNote(id, e) {
  const s = sessions.find(x => x.id === id);
  if (!s) return;
  const q = (s.specq ||= []);
  const prev = q.find(x => x.key === e.key);
  if (!prev) q.push(e);
  else if (prev.op === 'add') prev.text = e.text;
  else if (e.text === prev.old) q.splice(q.indexOf(prev), 1);
  else prev.text = e.text;
  saveDraft(s);
  refreshLive(s, null);
}

// 지운 개체(n). 이번 보내기에서 더한 개체면 더한 줄만 뺀다. 고친 개체면 고치기 전 글을 지운 것으로 알린다
// 옮긴 개체면 옮긴 줄을 빼고 옮기기 전 자리에서 지운 것으로 알린다(에이전트는 옮긴 것을 아직 모른다)
// 지운 자리 뒤 형제들은 순번이 하나씩 당겨지므로 그 줄들의 자리도 당긴다. 지운 줄은 자리로 찾지 않는다(다른 개체가 그 자리에 온다)
function spNoteRemove(id, n, where) {
  const s = sessions.find(x => x.id === id);
  if (!s) return;
  const q = (s.specq ||= []);
  const prev = q.find(x => x.key === spKey({ p: n.p }));
  if (prev) q.splice(q.indexOf(prev), 1);
  const moved = q.find(x => x.key === spKey({ op: 'move', p: n.p }));
  if (moved) q.splice(q.indexOf(moved), 1);
  if (prev?.op !== 'add') q.push({ op: 'remove', key: null, ...(moved?.from || where), text: prev?.op === 'edit' ? prev.old : n.t });
  spShiftQ(q, n.p, -1);
  saveDraft(s);
  refreshLive(s, null);
}

// 옮긴 개체. m: { from: 옮기기 전 자리, to: 옮긴 자리, fromWhere, where, text }
// 그 개체와 그 아래를 가리키던 줄은 새 자리를 따라가고, 빠진 자리와 끼운 자리 뒤 형제를 가리키던 줄은 순번을 옮긴다
// 이번 보내기에서 더한 개체면 더한 줄이 새 자리로 알린다. 이미 옮긴 개체면 그 줄의 옮긴 자리만 바꾸고, 처음 자리로 돌아왔으면 줄을 뺀다
function spNoteMove(id, m) {
  const s = sessions.find(x => x.id === id);
  if (!s) return;
  const q = (s.specq ||= []);
  const inside = q.filter(e => e.p && spSame(e.p.slice(0, m.from.length), m.from));
  const rest = q.filter(e => !inside.includes(e));
  spShiftQ(rest, m.from, -1);
  spShiftQ(rest, m.to, 1);
  inside.forEach(e => { e.p = [...m.to, ...e.p.slice(m.from.length)]; e.key = spKey(e); });
  const added = q.find(e => e.op === 'add' && spSame(e.p, m.to));
  const prev = q.find(e => e.key === spKey({ op: 'move', p: m.to }));
  if (prev) {
    if (spWhereText(prev.from) === spWhereText(m.where)) q.splice(q.indexOf(prev), 1);
    else Object.assign(prev, { label: m.where.label, crumb: m.where.crumb });
  } else if (!added) {
    q.push({ op: 'move', p: m.to, key: spKey({ op: 'move', p: m.to }), from: m.fromWhere, ...m.where, text: m.text });
  }
  saveDraft(s);
  refreshLive(s, null);
}

// 줄을 찾는 열쇠는 개체 자리다. 옮긴 줄은 같은 개체를 고친 줄과 따로 찾도록 앞에 표시를 붙인다
const spKey = e => (e.op === 'move' ? 'mv:' : '') + JSON.stringify(e.p);

// 자리 p 에서 개체가 빠지거나(d = -1) 끼워지면(d = 1) 같은 목록에서 그 뒤에 오는 형제를 가리키는 줄의 자리를 옮긴다
function spShiftQ(q, p, d) {
  const k = p.length - 1, base = p.slice(0, k);
  for (const e of q) {
    if (!e.p || e.p.length <= k || !spSame(e.p.slice(0, k), base) || e.p[k] < p[k] + (d < 0 ? 1 : 0)) continue;
    e.p = [...e.p.slice(0, k), e.p[k] + d, ...e.p.slice(k + 1)];
    e.key = spKey(e);
  }
}

// 접은 상태와 화면 위치는 프로젝트마다 둔다. 접은 상태와 확대 배율은 브라우저에 남긴다(처음엔 100%)
function spCollapsed(s) {
  const key = `overseer.spcol.${mpNorm(s.cwd)}`;
  if (!SP.col || SP.colKey !== key) {
    let saved = [];
    try { saved = JSON.parse(pref(key, '[]')); } catch { /* 깨진 값은 버린다 */ }
    SP.col = new Set(saved);
    SP.colKey = key;
  }
  return SP.col;
}
function spSaveCollapsed() { savePref(SP.colKey, JSON.stringify([...SP.col])); }
const spZoomKey = s => `overseer.spzoom.${mpNorm(s.cwd)}`;
const spClampZoom = z => Math.max(0.3, Math.min(1.6, z));
const spCam = s => (SP.cam[mpNorm(s.cwd)] ||= { ...SP_HOME, zoom: spClampZoom(Number(pref(spZoomKey(s), SP_HOME.zoom)) || SP_HOME.zoom) });
const spSaveZoom = s => savePref(spZoomKey(s), String(spCam(s).zoom));
const spOff = s => (SP.off[mpNorm(s.cwd)] ||= {});

// 그리기 ----------------------------------------------------------------------

function renderSpec(s, host) {
  // 고치는 동안은 다시 그리지 않는다. 끝나면 그린다. 다른 탭으로 옮기면 고치던 것은 버린다
  if (SP.editing) {
    if (SP.editing.sid === s.id && host.contains(SP.editing.el)) return;
    SP.editing.done = true;
    SP.editing = null;
  }
  spLoad(s);
  const ix = spIndex(s);
  const st = ix?.stats;
  const col = spCollapsed(s);
  const info = !s.spec ? '불러오는 중' : st
    ? `용어 ${st.terms} · 구성요소 ${st.comps} · 설명 ${st.desc} · 목업 ${st.mock} · 하는 것 ${st.do} · 하지 않는 것 ${st.dont}` : '';
  const empty = !s.spec ? '스펙을 불러오는 중' : s.spec.status === 'error' ? esc(s.spec.message || '스펙을 받지 못했다') : '이 프로젝트에는 스펙이 아직 없다';
  const nq = specCount(s);
  const queued = nq ? `<span class="sp-q" title="다음 보내기에 실려 에이전트에게 간다&#10;${esc(specLines(s).join('\n'))}">알릴 수정 ${nq}</span>` : '';
  host.innerHTML = `<section class="sp-pane">
    <header class="pane-bar">${spToggleHTML('spec')}<span class="pane-name">스펙 패널</span>${queued}<span class="pane-info">${info}</span>
      ${ix ? `<button class="bar-btn" data-sp-act="all">${col.size ? '모두 펼치기' : '모두 접기'}</button>
        <button class="bar-btn" data-sp-act="out" aria-label="축소">−</button><span class="sp-zoom" id="sp-zoom"></span>
        <button class="bar-btn" data-sp-act="in" aria-label="확대">+</button><button class="bar-btn" data-sp-act="home">원위치</button>` : ''}</header>
    ${ix ? SP_LEGEND : ''}
    <div class="sp-vp" id="sp-vp">${ix ? '<div class="sp-layer" id="sp-layer"></div>' : `<div class="empty">${empty}</div>`}</div>
  </section>`;
  if (ix) spDrawTree(s);
}

function spDrawTree(s) {
  const ix = spIndex(s);
  const layer = $('#sp-layer');
  if (!ix || !layer) return;
  const col = spCollapsed(s), off = spOff(s), sel = SP.sel;
  const segs = [], nodes = [];
  const r1 = v => Math.round(v * 10) / 10;
  // 끄는 중이면 놓을 수 있는 개체와 지금 놓일 개체를 표시한다. 구성요소를 끌 때는 움직일 때마다 다시 그리므로 여기서 붙인다
  // 누르기만 하고 아직 움직이지 않았으면(moved: false) 표시하지 않는다. false 를 그대로 두면 drop?.has 가 터져 레이어가 빈 채로 남는다
  const drop = SP.drag?.moved ? SP.drag.targets : null;
  const cls = (base, n) => base + (sel === n.id ? ' sel' : '') + (drop?.has(n.id) ? ` drop-ok${SP.drag.hot === n.id ? ' drop-hot' : ''}` : '');
  const seg = (x, y, w, h, k) => { if (w > 0 && h > 0) segs.push(`<i class="sp-seg${k}" style="left:${r1(x)}px;top:${r1(y)}px;width:${r1(w)}px;height:${r1(h)}px"></i>`); };
  // k 는 선의 종류. '' 은 품는 관계, ' then' 은 이어서 일어나는 관계
  const elbow = (p, t, gap, k = '') => {
    const mx = p.x + gap / 2;
    seg(p.x, p.y - 0.75, mx - p.x, 1.5, k);
    seg(mx - 0.75, Math.min(p.y, t.y) - 0.75, 1.5, Math.abs(t.y - p.y) + 1.5, k);
    const x1 = Math.min(mx, t.x), x2 = Math.max(mx, t.x);
    seg(x1, t.y - 0.75, x2 - x1, 1.5, k);
  };
  const pos = (x, y, w, h) => `left:${r1(x)}px;top:${r1(y)}px;width:${w}px;height:${h}px;--w:${w}px`;
  const label = n => n.kind === 'term' ? `<b>${esc(n.word)}</b>${esc(n.t.slice(n.word.length))}` : esc(n.t);
  const row = (n, kc, x, y, w, h, extra = '') => nodes.push(
    `<button type="button" class="${cls(`sp-n sp-row ${kc}`, n)}" data-sp-id="${esc(n.id)}" style="${pos(x, y, w, h)}" title="${esc(n.t)}"><span class="ic">${SP_ICON[n.kind]}</span><span class="t">${label(n)}</span>${extra}</button>`);
  // 목업 라벨은 링크다. 누르면 새 탭으로 열린다
  const mockRow = (m, x, y) => nodes.push(
    `<a class="sp-n sp-row sp-mock" href="${esc(m.href || '#')}" target="_blank" rel="noopener" draggable="false" data-sp-id="${esc(m.id)}" style="${pos(x, y, SP_ROW_W, SP_ROW_H)}" title="${esc(m.t)}"><span class="ic">${SP_ICON.mock}</span><span class="t">${esc(m.t)}</span><span class="go">새 탭 ↗</span></a>`);
  // 하는 것과 그것에 이어서 일어나는 일. 이어지는 일은 오른쪽에 쌓고, 차지한 높이를 돌려준다. 접으면 이어지는 일을 숨긴다
  const doRow = (n, x, y) => {
    const shut = col.has(n.id);
    row(n, 'sp-do', x, y, SP_ROW_W, SP_ROW_H,
      n.th.length ? spFold(shut) + (shut ? `<span class="sp-bd col">+${spCountDo(n.th)}</span>` : '') : '');
    if (!n.th.length || shut) return SP_ROW_H;
    const tx = x + SP_ROW_W + SP_THEN_GAP, a = { x: x + SP_ROW_W, y: y + SP_ROW_H / 2 };
    nodes.push(`<span class="sp-then" style="left:${r1(a.x + SP_THEN_GAP / 2)}px;top:${r1(a.y - 17)}px">이어서</span>`);
    let ty = y;
    n.th.forEach(t => {
      elbow(a, { x: tx, y: ty + SP_ROW_H / 2 }, SP_THEN_GAP, ' then');
      ty += doRow(t, tx, ty);
    });
    return ty - y;
  };

  const lay = (c, x, ly, ax, ay, pa, gap) => {
    const o = off[c.id] || { dx: 0, dy: 0 };
    const ox = ax + o.dx, oy = ay + o.dy, X = x + ox, Y = ly + oy;
    elbow(pa, { x: X, y: Y + SP_COMP_H / 2 }, gap);
    const shut = col.has(c.id);
    row(c, 'sp-comp', X, Y, SP_COMP_W, SP_COMP_H,
      (spCountSub(c) ? spFold(shut) : '') + (shut ? `<span class="sp-bd col">+${spCountSub(c)}</span>` : ''));
    if (shut) return SP_COMP_H;
    const cx = x + SP_COMP_W + SP_GAP, anchor = { x: X + SP_COMP_W, y: Y + SP_COMP_H / 2 };
    let cy = ly;
    const rows = (list, kc, draw) => {
      if (!list.length) return;
      if (cy > ly) cy += SP_GROUP_GAP;
      list.forEach(n => {
        const rx = cx + ox, ry = cy + oy;
        elbow(anchor, { x: rx, y: ry + SP_ROW_H / 2 }, SP_GAP);
        cy += draw ? draw(n, rx, ry) : (row(n, kc, rx, ry, SP_ROW_W, SP_ROW_H), SP_ROW_H);
      });
    };
    // 위에서부터 설명, 하위 구성요소, 목업, 하는 것, 하지 않는 것
    rows(c.d, 'sp-desc');
    c.c.forEach(sub => {
      if (cy > ly) cy += SP_SUB_GAP;
      cy += lay(sub, cx, cy, ox, oy, anchor, SP_GAP);
    });
    rows(c.m, 'sp-mock', (m, x, y) => (mockRow(m, x, y), SP_ROW_H));
    rows(c.f, 'sp-do', doRow);
    rows(c.n, 'sp-dont');
    return Math.max(SP_COMP_H, cy - ly);
  };

  const root = ix.root, rootShut = col.has('root');
  nodes.push(`<button type="button" class="${cls('sp-n sp-root', root)}" data-sp-id="root" style="left:0;top:0;width:${SP_ROOT_W}px"><span class="ic">${SP_ICON.root}</span><span class="rb"><span class="rt">${esc(root.t)}</span><span class="rd"></span><span class="rx">${esc(root.b)}</span></span>${root.c.length + root.w.length ? spFold(rootShut) : ''}${rootShut ? `<span class="sp-bd col">+${root.c.length + root.w.length}</span>` : ''}</button>`);
  if (!rootShut) {
    // 용어가 구성요소보다 위에 온다
    const cx = SP_ROOT_W + SP_GAP_ROOT, anchor = { x: SP_ROOT_W, y: 56 };
    let y = 0;
    root.w.forEach(w => {
      elbow(anchor, { x: cx, y: y + SP_ROW_H / 2 }, SP_GAP_ROOT);
      row(w, 'sp-term', cx, y, SP_ROW_W, SP_ROW_H);
      y += SP_ROW_H;
    });
    if (root.w.length) y += SP_COMP_GAP;
    root.c.forEach(c => { y += lay(c, cx, y, 0, 0, anchor, SP_GAP_ROOT) + SP_COMP_GAP; });
  }
  layer.innerHTML = segs.join('') + nodes.join('');
  spApplyCam(s);
  spPlaceActs(s);
}
// 접고 펴는 단추. 더블클릭은 글 고치기에 쓴다
const spFold = shut => `<span class="sp-fold" data-sp-fold title="${shut ? '펼치기' : '접기'}">${shut ? '▸' : '▾'}</span>`;

function spApplyCam(s) {
  const cam = spCam(s), layer = $('#sp-layer'), z = $('#sp-zoom');
  if (layer) layer.style.transform = `translate(${cam.panX}px, ${cam.panY}px) scale(${cam.zoom})`;
  if (z) z.textContent = Math.round(cam.zoom * 100) + '%';
}
function spZoomAt(s, z2, mx, my) {
  const cam = spCam(s);
  z2 = spClampZoom(z2);
  cam.panX = mx - (mx - cam.panX) * z2 / cam.zoom;
  cam.panY = my - (my - cam.panY) * z2 / cam.zoom;
  cam.zoom = z2;
  spApplyCam(s);
  spSaveZoom(s);
}
// 선택은 테두리만 바꾼다. 트리를 다시 그리면 눌린 요소가 사라져 더블클릭이 닿지 않는다
// 스펙 개체를 고르면 커맨드 패널의 카드 선택을 푼다. 방향키와 Enter 를 어느 패널이 받을지가 선택으로 갈린다
function spSelect(id) {
  SP.sel = id;
  if (id && ui.active) unpick();
  document.querySelectorAll('#sp-layer .sp-n.sel').forEach(el => el.classList.remove('sel'));
  if (id) document.querySelector(`#sp-layer [data-sp-id="${CSS.escape(id)}"]`)?.classList.add('sel');
  const s = cur();
  if (s) spPlaceActs(s);
}

// 고치기와 더하기 ----------------------------------------------------------------

// 고른 개체 아래에 자식을 더하는 단추. 프로젝트에는 용어와 구성요소, 구성요소에는 설명과 구성요소와 기능과 금지(하지 않는 것), 기능에는 이어서 일어나는 기능
// 목업은 단추로 더하지 않는다. 어떻게 만들지 설명이 따라야 해서 사용자의 지시로 에이전트가 만들어 등록한다
const SP_ADDS = {
  root: [['term', '+ 용어'], ['component', '+ 구성요소']],
  comp: [['desc', '+ 설명'], ['component', '+ 구성요소'], ['do', '+ 기능'], ['dont', '+ 금지']],
  do: [['do', '+ 이어서 기능']],
};
const SP_ADD_HINT = { term: '새 용어 (낱말: 뜻)', component: '새 구성요소 이름', desc: '새 설명 (이 구성요소가 무엇인지)', do: '새 기능', dont: '새 금지 (하지 않는 것)' };
// 지울 수 있는 개체: 자식이 하나도 없는 구성요소, 이어서 기능이 없는 기능, 설명, 하지 않는 것, 용어. 프로젝트와 목업은 아니다
function spCanRemove(n) {
  if (n.kind === 'comp') return !(n.c.length || n.d.length || n.f.length || n.n.length || n.m.length);
  if (n.kind === 'do') return !n.th.length;
  return ['desc', 'dont', 'term'].includes(n.kind);
}
const spNodeEl = id => document.querySelector(`#sp-layer [data-sp-id="${CSS.escape(id)}"]`);

// 레이어 안에서의 자리. 레이어의 확대와 상관없는 배치 좌표다
function spBox(el) {
  const layer = $('#sp-layer');
  let x = 0, y = 0;
  for (let e = el; e && e !== layer; e = e.offsetParent) { x += e.offsetLeft; y += e.offsetTop; }
  return { x, y, w: el.offsetWidth, h: el.offsetHeight };
}

// 고른 개체 바로 아래에 더하기 단추와, 자식이 없으면 삭제 단추를 띄운다. 고르기는 다시 그리지 않으므로 단추만 옮긴다
// 고치거나 개체를 끄는 동안은 띄우지 않는다
function spPlaceActs(s) {
  $('#sp-acts')?.remove();
  const n = SP.sel && spIndex(s)?.index[SP.sel];
  const adds = (n && SP_ADDS[n.kind]) || [], del = n && spCanRemove(n);
  const el = (adds.length || del) && !SP.editing && !(SP.drag?.moved && SP.drag.targets) && spNodeEl(n.id);
  if (!el) return;
  const b = spBox(el);
  $('#sp-layer').insertAdjacentHTML('beforeend', `<div class="sp-acts" id="sp-acts" style="left:${b.x}px;top:${b.y + b.h + 4}px">${
    adds.map(([k, t]) => `<button type="button" data-sp-add="${k}">${t}</button>`).join('')}${
    del ? '<button type="button" class="sp-del" data-sp-remove title="이 개체를 spec.json 에서 지운다. 자식이 있는 개체는 지울 수 없다">삭제</button>' : ''}</div>`);
}

// 개체 자리에 입력칸을 띄운다. Enter 나 다른 곳을 누르면 save(글), Esc 는 취소. 빈 글이거나 그대로면 저장하지 않는다
// 한글 조합 중의 Enter 는 조합을 마치는 데 쓴다
function spOpenEditor(s, box, value, placeholder, save) {
  $('#sp-acts')?.remove();
  const el = document.createElement('input');
  el.className = 'sp-edit';
  el.value = value;
  el.placeholder = placeholder;
  Object.assign(el.style, { left: `${box.x}px`, top: `${box.y}px`, width: `${Math.max(box.w, SP_ROW_W)}px`, height: `${Math.max(box.h, SP_ROW_H)}px` });
  $('#sp-layer').appendChild(el);
  const ed = SP.editing = { sid: s.id, el, done: false };
  const finish = async ok => {
    if (ed.done) return;
    ed.done = true;
    const text = el.value.trim();
    if (ok && text && text !== value.trim()) await save(text);
    if (SP.editing === ed) SP.editing = null;
    el.remove();
    renderModules();
  };
  el.addEventListener('keydown', e => {
    e.stopPropagation();
    if (e.isComposing || e.keyCode === 229) return;
    if (e.key === 'Enter') { e.preventDefault(); finish(true); }
    else if (e.key === 'Escape') { e.preventDefault(); finish(false); }
  });
  el.addEventListener('blur', () => finish(true));
  el.focus();
  el.select();
}

// 서버에 쓰고 받은 스펙으로 바꾼다. 실패하면 api 가 까닭을 띄우고 null
async function spWrite(id, body) {
  if (!LIVE) { alert('목업에서는 스펙을 고칠 수 없다'); return null; }
  let res;
  SP.writing++;
  try { res = await api(`/api/tabs/${id}/spec`, 'POST', body); } finally { SP.writing--; }
  const s = sessions.find(x => x.id === id);
  if (!res || !s) return null;
  s.spec = res.spec;
  s._spIx = null;
  return res;
}

// 더블클릭한 개체의 글을 고친다. 프로젝트는 누른 곳에 따라 제목이나 요약, 용어는 `낱말: 뜻` 을 한 칸에서 고친다. 목업 라벨은 링크라 고치지 않는다
function spStartEdit(s, n, el, target) {
  let part = el, value = n.t, changes, key = JSON.stringify(n.p), where;
  if (n.kind === 'root') {
    const sum = !!target.closest('.rx');
    part = el.querySelector(sum ? '.rx' : '.rt');
    value = sum ? n.b : n.t;
    key = JSON.stringify([sum ? 'summary' : 'title']);
    where = { label: sum ? '요약' : '제목', crumb: '' };
    changes = text => [{ path: [sum ? 'summary' : 'title'], old: value, new: text }];
  } else if (n.kind === 'term') {
    where = spWhereOf(n);
    changes = text => {
      const k = text.search(/[:：]/);
      const word = (k < 0 ? text : text.slice(0, k)).trim(), meaning = k < 0 ? n.meaning : text.slice(k + 1).trim();
      return [['word', n.word, word], ['meaning', n.meaning, meaning]].filter(([, a, b]) => a !== b).map(([f, a, b]) => ({ path: [...n.p, f], old: a, new: b }));
    };
  } else {
    where = spWhereOf(n);
    const path = n.kind === 'comp' ? [...n.p, 'name'] : n.kind === 'do' ? n.tp : n.p;
    changes = text => [{ path, old: n.t, new: text }];
  }
  spOpenEditor(s, spBox(part), value, '', async text => {
    const list = changes(text);
    if (!list.length) return;
    const before = spQ(s.id);
    if (!await spWrite(s.id, { op: 'edit', changes: list })) return;
    const note = { op: 'edit', key, p: JSON.parse(key), ...where, old: value, text };
    spNote(s.id, note);
    spRecord(s.id, before, {
      back: spEditStep(list.map(c => ({ path: c.path, old: c.new, new: c.old })), { ...note, old: text, text: value }, n.p),
      fwd: spEditStep(list, note, n.p),
    });
  });
}

// 고른 개체 아래에 자식을 더한다. 입력칸은 그 개체 바로 아래에 뜬다. 더한 자식을 고르고 부모가 접혀 있으면 편다
// 용어는 `낱말: 뜻` 한 칸으로 받는다. 낱말이나 뜻이 비면 더하지 않는다
function spStartAdd(s, kind) {
  const n = SP.sel && spIndex(s)?.index[SP.sel];
  const el = n && spNodeEl(n.id);
  if (!el) return;
  const b = spBox(el);
  const where = spWhereNew(n, kind);
  spOpenEditor(s, { x: b.x + 24, y: b.y + b.h + 4, w: SP_ROW_W, h: SP_ROW_H }, '', SP_ADD_HINT[kind], async text => {
    let item = text, expect = text;
    if (kind === 'term') {
      const k = text.search(/[:：]/);
      const word = k < 0 ? '' : text.slice(0, k).trim(), meaning = k < 0 ? '' : text.slice(k + 1).trim();
      if (!word || !meaning) { alert('용어는 `낱말: 뜻` 으로 쓴다'); return; }
      item = { word, meaning };
      expect = word;
      text = `${word}: ${meaning}`;
    }
    const before = spQ(s.id);
    const res = await spWrite(s.id, { op: 'add', path: n.p, expect: n.t, kind, text: item });
    if (!res) return;
    spNote(s.id, { op: 'add', key: JSON.stringify(res.path), p: res.path, ...where, text });
    spRecord(s.id, before, {
      back: spRemoveStep(res.path, expect, where, text),
      fwd: spAddStep(n.p, n.t, kind, item, res.path.at(-1), where, text),
    });
    const t = sessions.find(x => x.id === s.id);
    const added = t && Object.values(spIndex(t)?.index || {}).find(x => spSame(x.p, res.path));
    if (added) SP.sel = added.id;
    const col = spCollapsed(s);
    if (col.delete(n.id)) spSaveCollapsed();
  });
}

// 고른 개체를 지운다. 확인 창은 없다(spec.json 은 git 이 추적한다). 지운 뒤에는 부모를 고른다
async function spRemove(s) {
  const n = SP.sel && spIndex(s)?.index[SP.sel];
  if (!n || !spCanRemove(n)) return;
  const where = spWhereOf(n), expect = n.kind === 'term' ? n.word : n.t;
  const before = spQ(s.id);
  if (!await spWrite(s.id, { op: 'remove', path: n.p, expect })) return;
  SP.sel = n.parent?.id || null;
  spNoteRemove(s.id, n, where);
  const item = n.kind === 'term' ? { word: n.word, meaning: n.meaning } : n.t;
  spRecord(s.id, before, {
    back: spAddStep(n.parent.p, n.parent.t, SP_ADD_KIND[n.kind], item, n.p.at(-1), where, n.t),
    fwd: spRemoveStep(n.p, expect, where, n.t),
  });
  renderModules();
}

// 끌어 옮기기 ----------------------------------------------------------------------
// 개체를 다른 개체 위에 놓으면 자식째 그 아래 목록 끝으로 옮긴다. 놓을 수 있는 자리는 더하기와 같다
// 자기 아래, 지금 부모, 프로젝트는 놓을 자리가 아니다. 구성요소를 빈 곳에 놓으면 지금처럼 화면 배치만 옮긴다

// 종류마다 부모가 될 수 있는 개체
const SP_PARENTS = { comp: ['root', 'comp'], desc: ['comp'], do: ['comp', 'do'], dont: ['comp'], mock: ['comp'], term: ['root'] };
const spUnder = (t, n) => { for (let c = t; c; c = c.parent) if (c === n) return true; return false; };
function spDropTargets(s, n) {
  const ok = SP_PARENTS[n.kind] || [];
  return new Set(Object.values(spIndex(s)?.index || {}).filter(t => ok.includes(t.kind) && t !== n.parent && !spUnder(t, n)).map(t => t.id));
}

// 접은 상태는 노드 이름(구성요소 이름을 이은 경로와 순번)에 붙어 있어, 옮긴 개체와 그 아래의 것을 새 이름으로 옮겨 단다
function spRename(s, from, to) {
  const col = spCollapsed(s), off = spOff(s);
  const hit = id => id === from || ['/', ':', '.'].some(c => id.startsWith(from + c));
  let changed = false;
  [...col].filter(hit).forEach(id => { col.delete(id); col.add(to + id.slice(from.length)); changed = true; });
  if (changed) spSaveCollapsed();
  Object.keys(off).filter(id => id !== from && hit(id)).forEach(id => { off[to + id.slice(from.length)] = off[id]; delete off[id]; });
  delete off[from];
}

async function spMove(s, n, t) {
  const fromWhere = spWhereOf(n), expect = n.kind === 'term' ? n.word : n.t;
  const back = { path: n.parent.p, seen: n.parent.t, at: n.p.at(-1) };
  const before = spQ(s.id);
  const res = await spWrite(s.id, { op: 'move', path: n.p, expect, to: t.p, toExpect: t.t });
  const u = sessions.find(x => x.id === s.id);
  if (!res || !u) return;
  const moved = spFind(u, res.path);
  const where = moved ? spWhereOf(moved) : fromWhere;
  if (moved) spRename(u, n.id, moved.id);
  spNoteMove(u.id, { from: n.p, to: res.path, fromWhere, where, text: n.t });
  spRecord(u.id, before, {
    back: spMoveStep(res.path, expect, back.path, back.seen, back.at, where, fromWhere, n.t),
    fwd: spMoveStep(n.p, expect, t.p, t.t, undefined, fromWhere, where, n.t),
  });
  spReveal(u, res.path);
  renderModules();
}

// 실행취소 ----------------------------------------------------------------------
// 사용자가 이 패널에서 한 고치기, 더하기, 삭제만 되돌린다. 에이전트가 MCP 로 고친 것은 기록에 없다(git 으로 되돌린다)
// 기록은 탭마다 브라우저에만 둔다. 새로고침하면 사라진다. 새로 무엇을 하면 다시 할 것(redo)은 버린다
// 기록 하나는 서버에 보낼 되돌리기(back)와 다시 하기(fwd), 그 일을 하기 전과 뒤의 보낼 줄 목록(before, after)이다
// 그 사이 보내지 않았으면 줄 목록을 그때로 돌린다(더한 것을 되돌리면 더한 줄이 빠진다). 보냈으면 되돌린 쓰기를 새 줄로 알린다
// 그 사이 에이전트가 같은 개체를 고쳤으면 서버가 쓰지 않고 까닭을 띄운다. 그 기록은 버린다

// 지운 개체를 되살릴 때 쓰는 자식 종류
const SP_ADD_KIND = { comp: 'component', desc: 'desc', do: 'do', dont: 'dont', term: 'term' };
const spHist = id => (SP.hist[id] ||= { back: [], fwd: [], gen: 0 });
const spQ = id => JSON.parse(JSON.stringify(sessions.find(x => x.id === id)?.specq || []));

function spRecord(id, before, entry) {
  const h = spHist(id);
  h.back.push({ ...entry, gen: h.gen, before, after: spQ(id) });
  h.fwd = [];
}

// 쓰기 한 번: 서버에 보낼 것, 보낸 뒤라 새 줄로 알릴 때 쓸 줄, 끝나고 고를 개체의 자리
// shown 은 줄에 쓰는 글(용어는 `낱말: 뜻`)
const spEditStep = (changes, note, sel) => ({ body: { op: 'edit', changes }, note: t => spNote(t.id, note), sel: () => sel });
const spRemoveStep = (path, expect, where, shown) => ({
  body: { op: 'remove', path, expect },
  note: t => spNoteRemove(t.id, { p: path, t: shown }, where),
  sel: () => path.slice(0, -2),
});
const spAddStep = (path, expect, kind, item, at, where, shown) => ({
  body: { op: 'add', path, expect, kind, text: item, at },
  note: (t, res) => {
    spShiftQ(t.specq ||= [], res.path, 1);
    spNote(t.id, { op: 'add', key: JSON.stringify(res.path), p: res.path, ...where, text: shown });
  },
  sel: res => res.path,
});
// 옮기기는 옮긴 자리에서 옛 부모의 옛 순번(at)으로 되돌린다. 다시 할 때는 새 부모 목록 끝에 붙인다
const spMoveStep = (path, expect, to, toExpect, at, fromWhere, where, shown) => ({
  body: { op: 'move', path, expect, to, toExpect, at },
  note: (t, res) => spNoteMove(t.id, { from: path, to: res.path, fromWhere, where, text: shown }),
  sel: res => res.path,
});

// back 이면 마지막에 한 일을 되돌리고, 아니면 마지막에 되돌린 일을 다시 한다
async function spUndo(s, back) {
  const h = spHist(s.id), from = back ? h.back : h.fwd, to = back ? h.fwd : h.back;
  const e = from.at(-1);
  if (!e || SP.writing || SP.editing) return;
  const step = back ? e.back : e.fwd;
  const res = await spWrite(s.id, step.body);
  if (from.at(-1) === e) from.pop();
  const t = sessions.find(x => x.id === s.id);
  if (!res || !t) return;
  if (e.gen === h.gen) t.specq = JSON.parse(JSON.stringify(back ? e.before : e.after));
  else {
    const was = spQ(t.id);
    step.note(t, res);
    const now = spQ(t.id);
    Object.assign(e, { gen: h.gen, before: back ? now : was, after: back ? was : now });
  }
  to.push(e);
  saveDraft(t);
  refreshLive(t, null);
  spReveal(t, step.sel(res));
  renderModules();
}

// 되돌린 개체를 고르고, 접힌 조상은 펴서 보이게 한다
function spReveal(s, path) {
  const n = spFind(s, path);
  SP.sel = n?.id || null;
  if (n && ui.active) unpick();
  const col = spCollapsed(s);
  let opened = false;
  for (let c = n?.parent; c; c = c.parent) opened = col.delete(c.id) || opened;
  if (opened) spSaveCollapsed();
}

// Ctrl+Z: 되돌리기, Ctrl+Shift+Z: 다시 하기. 스펙 패널이 보일 때만 듣는다
// 글 입력칸과 터미널 안에서는 그쪽의 되돌리기에 맡긴다. 한글 입력 상태에서도 잡도록 자판 자리(KeyZ)로 본다
document.addEventListener('keydown', e => {
  if (!(e.ctrlKey || e.metaKey) || e.altKey || (e.code !== 'KeyZ' && e.key?.toLowerCase() !== 'z')) return;
  if (e.target.closest?.('#term, dialog, textarea, input, select, [contenteditable]')) return;
  const s = cur();
  if (!s || spView(s) !== 'spec' || !$('#sp-vp')?.offsetParent) return;
  e.preventDefault();
  spUndo(s, !e.shiftKey);
});

// 키보드로 고르고 접기 ----------------------------------------------------------------
// 스펙 패널에 고른 개체가 보이면 방향키와 Enter 는 스펙 패널이 받는다. 카드를 골랐거나 아무것도 고르지 않았으면 커맨드 패널이 받는다(app.js)
// ↑↓ 같은 부모 아래 형제 사이(끝에서 멈춘다), ← 부모, → 첫 자식(접혀 있으면 펴고), Enter 접기와 펴기, Esc 선택 풀기. 목업은 누르면 열리는 링크라 고르지 않는다

// 방향키로 오갈 자식. 화면에 놓인 순서대로다
function spNavKids(n) {
  if (n.kind === 'root') return [...n.w, ...n.c];
  if (n.kind === 'comp') return [...n.d, ...n.c, ...n.f, ...n.n];
  return n.kind === 'do' ? n.th : [];
}
// ▾ 단추가 붙는 개체. 구성요소는 목업만 있어도 접힌다
const spFoldable = n => n.kind === 'root' ? n.c.length + n.w.length > 0 : n.kind === 'comp' ? spCountSub(n) > 0 : n.kind === 'do' && n.th.length > 0;

function spToggleFold(s, id) {
  const col = spCollapsed(s);
  col.has(id) ? col.delete(id) : col.add(id);
  spSaveCollapsed();
  renderModules();
}

// 고른 개체가 화면 밖에 있으면 보이는 데까지만 화면을 옮긴다. 개체가 화면보다 크면 왼쪽 위를 맞춘다
function spFollow(s, id) {
  const el = spNodeEl(id), vp = $('#sp-vp');
  if (!el || !vp) return;
  const cam = spCam(s), b = spBox(el), m = 24, z = cam.zoom;
  const fit = (pan, at, size, view) => {
    const lo = pan + at * z, hi = lo + size * z;
    if (lo < m) return pan + m - lo;
    if (hi > view - m) return pan - Math.min(hi - (view - m), lo - m);
    return pan;
  };
  cam.panX = fit(cam.panX, b.x, b.w, vp.clientWidth);
  cam.panY = fit(cam.panY, b.y, b.h, vp.clientHeight);
  spApplyCam(s);
}

function spGo(s, id) {
  spSelect(id);
  spFollow(s, id);
}

// Esc(app.js 가 부른다): 스펙 패널에 보이는 고른 개체가 있으면 선택을 풀어 방향키를 카드에 돌려준다. 처리했으면 true
function spEsc() {
  const s = cur();
  if (!s || !SP.sel || spView(s) !== 'spec' || !$('#sp-vp')?.offsetParent || !spNodeEl(SP.sel)) return false;
  spSelect(null);
  return true;
}

document.addEventListener('keydown', e => {
  if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Enter'].includes(e.key)) return;
  if (e.ctrlKey || e.altKey || e.metaKey || e.shiftKey || e.isComposing) return;
  if (e.target.closest?.('#term, dialog, textarea, input, select, [contenteditable]')) return;
  const s = cur();
  if (!s || ui.active || SP.editing || spView(s) !== 'spec' || !$('#sp-vp')?.offsetParent) return;
  // 고른 개체가 접힌 조상 밑에 숨어 있으면 고른 것이 없는 셈이다
  const n = SP.sel && spIndex(s)?.index[SP.sel];
  if (!n || !spNodeEl(n.id)) return;
  // 카드 이동(app.js)과 눌린 단추의 클릭으로 번지지 않게 한다
  e.preventDefault();
  e.stopImmediatePropagation();
  const col = spCollapsed(s);
  if (e.key === 'Enter') { if (spFoldable(n)) spToggleFold(s, n.id); return; }
  if (e.key === 'ArrowLeft') { if (n.parent) spGo(s, n.parent.id); return; }
  if (e.key === 'ArrowRight') {
    const first = spNavKids(n)[0];
    if (!first) return;
    if (col.delete(n.id)) { spSaveCollapsed(); SP.sel = first.id; renderModules(); spFollow(s, first.id); }
    else spGo(s, first.id);
    return;
  }
  const sibs = n.parent ? spNavKids(n.parent) : [];
  const next = sibs[sibs.indexOf(n) + (e.key === 'ArrowDown' ? 1 : -1)];
  if (next) spGo(s, next.id);
});

// 조작 ----------------------------------------------------------------------

document.addEventListener('click', e => {
  const s = cur();
  if (!s) return;
  const v = e.target.closest('[data-sp-view]');
  if (v) {
    if (spView(s) !== v.dataset.spView) { spSetView(s, v.dataset.spView); renderModules(); }
    return;
  }
  const a = e.target.closest('[data-sp-act]');
  if (a) {
    const act = a.dataset.spAct, vp = $('#sp-vp');
    const r = vp ? vp.getBoundingClientRect() : { width: 0, height: 0 };
    if (act === 'in') spZoomAt(s, spCam(s).zoom * 1.15, r.width / 2, r.height / 2);
    if (act === 'out') spZoomAt(s, spCam(s).zoom / 1.15, r.width / 2, r.height / 2);
    if (act === 'home') { Object.assign(spCam(s), SP_HOME); spApplyCam(s); spSaveZoom(s); }
    // 모두 접기는 접을 수 있는 개체(하위 구성요소, 이어서 일이 달린 기능까지)를 다 접는다. 하나를 펴도 그 아래는 접힌 채다. 프로젝트는 펴 둔다
    if (act === 'all') {
      const col = spCollapsed(s), ix = spIndex(s);
      if (col.size) col.clear();
      else Object.values(ix?.index || {}).forEach(n => { if (n.kind !== 'root' && spFoldable(n)) col.add(n.id); });
      spSaveCollapsed();
      renderModules();
    }
    return;
  }
  const vp = e.target.closest('#sp-vp');
  if (!vp) return;
  if (SP.dragMoved) { SP.dragMoved = false; e.preventDefault(); return; }
  if (e.target.closest('.sp-edit')) return;
  const add = e.target.closest('[data-sp-add]');
  if (add) { spStartAdd(s, add.dataset.spAdd); return; }
  if (e.target.closest('[data-sp-remove]')) { spRemove(s); return; }
  // 하위가 있는 노드(프로젝트, 구성요소, 이어서 기능이 달린 기능)는 ▾ 단추로 접고 편다
  const fold = e.target.closest('[data-sp-fold]');
  if (fold) { spToggleFold(s, fold.closest('[data-sp-id]').dataset.spId); return; }
  const el = e.target.closest('[data-sp-id]');
  if (el && spIndex(s)?.index[el.dataset.spId]?.kind !== 'mock') spSelect(el.dataset.spId);
});

// 개체를 더블클릭하면 그 글을 그 자리에서 고친다
document.addEventListener('dblclick', e => {
  const s = cur();
  if (!s || e.target.closest('[data-sp-fold], .sp-acts, .sp-edit')) return;
  const el = e.target.closest('#sp-vp [data-sp-id]');
  const n = el && spIndex(s)?.index[el.dataset.spId];
  if (!n || n.kind === 'mock') return;
  e.preventDefault();
  spStartEdit(s, n, el, e.target);
});

// 빈 곳을 끌면 화면이 움직인다. 개체를 끌어 다른 개체 위에 놓으면 그 아래로 옮긴다
// 구성요소는 끄는 동안 하위째 따라 움직이고, 빈 곳에 놓으면 그 배치로 남는다. 다른 개체는 끄는 동안 사본이 따라온다
document.addEventListener('pointerdown', e => {
  const s = cur();
  const vp = s && e.button === 0 && e.target.closest('#sp-vp');
  if (!vp || !spIndex(s) || SP.editing || e.target.closest('.sp-acts, .sp-edit')) return;
  const el = e.target.closest('[data-sp-id]');
  const n = el && spIndex(s).index[el.dataset.spId];
  const cam = spCam(s);
  const at = { sx: e.clientX, sy: e.clientY, moved: false };
  if (n) {
    const targets = n.kind === 'root' ? new Set() : spDropTargets(s, n);
    const o = spOff(s)[n.id] || { dx: 0, dy: 0 };
    SP.drag = n.kind === 'comp' ? { ...at, mode: 'node', id: n.id, o: { ...o }, targets }
      : targets.size ? { ...at, mode: 'item', id: n.id, targets } : { ...at, mode: 'none' };
  } else {
    SP.drag = { ...at, mode: 'pan', px: cam.panX, py: cam.panY };
    vp.classList.add('grabbing');
  }
});

// 끄는 개체 밑에서 놓을 수 있는 개체. 끄는 구성요소와 그 하위, 사본은 놓을 자리가 아니라 건너뛴다
function spHotAt(d, x, y) {
  for (const el of document.elementsFromPoint(x, y)) {
    const id = el.closest?.('#sp-layer [data-sp-id]')?.dataset.spId;
    if (id && d.targets.has(id)) return id;
  }
  return null;
}
// 끌기를 처음 움직였을 때: 놓을 수 있는 개체를 표시하고, 구성요소가 아니면 따라올 사본을 띄운다
function spDragStart(s, d) {
  $('#sp-acts')?.remove();
  $('#sp-vp')?.classList.add('grabbing');
  d.targets.forEach(id => spNodeEl(id)?.classList.add('drop-ok'));
  if (d.mode !== 'item') return;
  const el = spNodeEl(d.id);
  if (!el) return;
  d.box = spBox(el);
  d.ghost = el.cloneNode(true);
  d.ghost.classList.remove('sel');
  d.ghost.classList.add('sp-ghost');
  delete d.ghost.dataset.spId;
  $('#sp-layer').appendChild(d.ghost);
  el.classList.add('dragging');
}
function spMarkHot(d, hot) {
  if (d.hot === hot) return;
  if (d.hot) spNodeEl(d.hot)?.classList.remove('drop-hot');
  d.hot = hot;
  if (hot) spNodeEl(hot)?.classList.add('drop-hot');
}

window.addEventListener('pointermove', e => {
  const d = SP.drag, s = cur();
  if (!d || !s) return;
  const dx = e.clientX - d.sx, dy = e.clientY - d.sy;
  if (!d.moved && Math.abs(dx) + Math.abs(dy) < 4) return;
  const first = !d.moved;
  d.moved = true;
  const cam = spCam(s);
  if (d.mode === 'pan') { cam.panX = d.px + dx; cam.panY = d.py + dy; spApplyCam(s); return; }
  if (d.mode === 'none') return;
  if (first) spDragStart(s, d);
  if (d.mode === 'node') {
    // 다시 그리면 표시가 cls 로 다시 붙는다. 그리기 전에 놓일 자리를 정한다
    spOff(s)[d.id] = { dx: d.o.dx + dx / cam.zoom, dy: d.o.dy + dy / cam.zoom };
    d.hot = spHotAt(d, e.clientX, e.clientY);
    spDrawTree(s);
    return;
  }
  if (d.ghost) Object.assign(d.ghost.style, { left: `${d.box.x + dx / cam.zoom}px`, top: `${d.box.y + dy / cam.zoom}px` });
  spMarkHot(d, spHotAt(d, e.clientX, e.clientY));
});

window.addEventListener('pointerup', () => {
  const d = SP.drag, s = cur();
  if (!d) return;
  SP.drag = null;
  $('#sp-vp')?.classList.remove('grabbing');
  SP.dragMoved = d.moved;
  if (d.mode === 'pan' && !d.moved) spSelect(null);
  if (!d.moved || !s || (d.mode !== 'node' && d.mode !== 'item')) return;
  d.ghost?.remove();
  document.querySelectorAll('#sp-layer .drop-ok, #sp-layer .dragging').forEach(el => el.classList.remove('drop-ok', 'drop-hot', 'dragging'));
  const ix = spIndex(s), n = ix?.index[d.id], t = d.hot && ix?.index[d.hot];
  if (n && t) {
    // 구성요소는 끈 만큼 비켜 그렸던 자리를 되돌리고 옮긴다
    if (d.mode === 'node') { spOff(s)[d.id] = d.o; spDrawTree(s); }
    spMove(s, n, t);
  } else if (d.mode === 'node') spDrawTree(s);
  else spPlaceActs(s);
});
document.getElementById('modhost').addEventListener('wheel', e => {
  const s = cur();
  const vp = s && e.target.closest('#sp-vp');
  if (!vp || !spIndex(s)) return;
  e.preventDefault();
  // 가로가 더 큰 휠(터치패드 가로 스와이프, Shift+휠)은 화면을 좌우로 옮기고, 세로 휠만 확대·축소한다
  // 가로 스와이프는 deltaY 가 0 이라 부호만 보면 이벤트마다 축소됐다
  const r = vp.getBoundingClientRect();
  if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
    const unit = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? r.width : 1;
    spCam(s).panX -= e.deltaX * unit;
    spApplyCam(s);
    return;
  }
  if (!e.deltaY) return;
  spZoomAt(s, spCam(s).zoom * (e.deltaY < 0 ? 1.1 : 1 / 1.1), e.clientX - r.left, e.clientY - r.top);
}, { passive: false });
