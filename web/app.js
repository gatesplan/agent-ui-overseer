// Overseer 목업. 턴을 좌에서 우로 흐르는 기둥으로, 사안을 카드로, 파생·언급 관계를 선으로 그린다
// 마지막 턴 기둥에서 바로 처리하고, 화살표 너머 NEXT INPUT 기둥에서 승인과 전송 시안을 본다
'use strict';

const LABEL = { answer: '답변', approve: '승인', hold: '보류', reject: '기각', confirm: '확인' };
// 사안 종류별 처리 버튼. 두 번째 값은 의견 필수 여부
const ACTIONS = {
  질문: [['answer', true], ['hold', false], ['reject', true]],
  제안: [['approve', false], ['hold', false], ['reject', true]],
  보고: [['confirm', false], ['answer', true]],
};
const PLACEHOLDER = {
  answer: '답변 (필수)', approve: '조건이나 덧붙일 말 (선택)', hold: '보류 메모 (선택, 전송 안 함)',
  reject: '기각 사유 (필수). 사유가 없으면 에이전트가 다음 판단을 못 한다', confirm: '덧붙일 말 (선택)',
};
// 턴 안 정렬: 보고, 질문, 제안. 규약 밖 종류는 맨 뒤
const KIND_ORDER = { 보고: 0, 질문: 1, 제안: 2 };
const FONT_KEYS = { cur: '현재 카드', prev: '이전 카드', draft: '시안' };
const FONT_DEFAULT = { cur: 14, prev: 13, draft: 13 };

const blank = { decisions: {}, sent: {}, log: [], extra: '', running: null, turns: [], summary: {}, summarySent: {} };
const sessions = window.MOCK.sessions.map(s => ({
  ...blank, ...s,
  decisions: Object.fromEntries(Object.entries(s.decisions).map(([k, [a, n]]) => [k, { action: a, note: n }])),
  sent: Object.fromEntries((s.sent || []).map(id => [id, { action: s.decisions[id][0], note: s.decisions[id][1] }])),
  log: [],
}));
sessions.push(
  { ...blank, id: 'pm', project: 'project-manager', agent: 'claude', status: 'working', log: [] },
  { ...blank, id: 'fmp', project: 'fishmathpics', agent: 'codex', status: 'idle', log: [] },
);

function pref(key, fallback) { try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; } }
function savePref(key, value) { try { localStorage.setItem(key, value); } catch { /* 저장 못 해도 동작엔 지장 없음 */ } }

const ui = {
  cur: sessions[0].id, term: false, open: new Set(), promptOpen: new Set(), drawer: null,
  theme: pref('overseer.theme', 'future-industry'),
  refs: pref('overseer.refs', '1') === '1',
  fs: Object.fromEntries(Object.keys(FONT_KEYS).map(k => [k, Number(pref(`overseer.fs.${k}`, FONT_DEFAULT[k]))])),
};
const $ = sel => document.querySelector(sel);
const cur = () => sessions.find(s => s.id === ui.cur);
const sorted = items => [...items].sort((a, b) => (KIND_ORDER[a.kind] ?? 9) - (KIND_ORDER[b.kind] ?? 9));
const allItems = s => s.turns.flatMap(t => sorted(t.items));
const findItem = (s, id) => allItems(s).find(i => i.id === id);
const actionsFor = item => ACTIONS[item.kind] || ACTIONS['질문'];
const pad = n => String(n).padStart(2, '0');
const turnOf = id => Number(id.split('-')[0]);

function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function inline(s) {
  return esc(s).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
}
function md(text) {
  const out = [];
  let list = null;
  for (const line of text.split('\n')) {
    const m = line.match(/^\s*[-*]\s+(.*)$/);
    if (m) { (list ||= []).push(`<li>${inline(m[1])}</li>`); continue; }
    if (list) { out.push(`<ul>${list.join('')}</ul>`); list = null; }
    if (line.trim()) out.push(`<p>${inline(line)}</p>`);
  }
  if (list) out.push(`<ul>${list.join('')}</ul>`);
  return out.join('');
}

// 사안 상태
function needsNote(item, action) {
  const a = actionsFor(item).find(([k]) => k === action);
  return a ? a[1] : false;
}
function isValid(item, d) { return d && d.action && (!needsNote(item, d.action) || d.note.trim()); }
function isHeld(s, id) { return s.sent[id]?.action === 'hold'; }
// 전송 대기: 안 보낸 것 중 처리 완료, 또는 보류했던 것을 다른 처리로 바꾼 것
function isReady(s, item) {
  const d = s.decisions[item.id];
  if (!isValid(item, d)) return false;
  if (!s.sent[item.id]) return true;
  return isHeld(s, item.id) && d.action !== 'hold';
}
function editable(s, id) { return !s.sent[id] || isHeld(s, id); }
function statusOf(s, item) {
  if (isReady(s, item)) return 'ready';
  if (isHeld(s, item.id)) return 'held';
  return s.sent[item.id] ? 'done' : 'todo';
}
// 이번에 처리할 사안: 아직 안 보낸 것 + 보류에서 바꾼 것
function roundItems(s) { return allItems(s).filter(i => ['todo', 'ready'].includes(statusOf(s, i))); }
function heldItems(s) { return allItems(s).filter(i => statusOf(s, i) === 'held'); }
function progress(s) {
  const round = roundItems(s);
  return { done: round.filter(i => statusOf(s, i) === 'ready').length, total: round.length };
}
// 전부 처리했고 보낼 내용이 있어야 승인 가능
function canSend(s) {
  const { done, total } = progress(s);
  return done === total && !!compose(s);
}

// 관계: 출처(parent)는 실선, 본문에서 앞 턴 사안을 언급한 것은 점선
function edgesOf(s) {
  const ids = new Set(allItems(s).map(i => i.id));
  const edges = [];
  for (const i of allItems(s)) {
    if (i.parent && ids.has(i.parent)) edges.push({ from: i.parent, to: i.id, type: 'parent' });
    const refs = new Set([...i.body.matchAll(/#(\d+-\d+)/g)].map(m => m[1]));
    for (const r of refs) {
      if (r !== i.parent && ids.has(r) && turnOf(r) < turnOf(i.id)) edges.push({ from: r, to: i.id, type: 'ref' });
    }
  }
  return edges;
}

// 전송 메시지
function summaryNote(s) { return s.running ? '' : (s.summary[s.turns.length] || '').trim(); }

function compose(s) {
  const lines = [];
  if (summaryNote(s)) lines.push(`종합 의견에 대해: ${summaryNote(s)}`);
  for (const i of allItems(s).filter(i => isReady(s, i))) {
    const d = s.decisions[i.id];
    const head = `${isHeld(s, i.id) ? '보류 해제: ' : ''}#${i.id} [${i.kind}] ${i.title}`;
    const tail = d.action === 'hold' ? '보류' : `${LABEL[d.action]}${d.note.trim() ? `: ${d.note.trim()}` : ''}`;
    lines.push(`${head} → ${tail}`);
  }
  const keep = heldItems(s).map(i => `#${i.id}`);
  if (lines.length && keep.length) lines.push(`보류 유지: ${keep.join(', ')}`);
  if (s.extra.trim()) lines.push(s.extra.trim());
  return lines.join('\n');
}

// 렌더 조각
function renderTabs() {
  $('#tabs').innerHTML = sessions.map(s => {
    const n = allItems(s).filter(i => statusOf(s, i) === 'todo').length;
    return `<button class="tab ${s.id === ui.cur ? 'on' : ''}" data-tab="${s.id}">
      <span class="dot ${s.status}"></span>${esc(s.project)} <span class="agent">${s.agent}</span>
      ${n ? `<span class="badge">${n}</span>` : ''}</button>`;
  }).join('') + `<button class="tab add" title="새 세션 (목업)">+</button>`;
}

function stateChip(s, item) {
  const st = statusOf(s, item);
  const d = st === 'done' || st === 'held' ? s.sent[item.id] : s.decisions[item.id];
  if (!d || !d.action) return '';
  return `<span class="state s-${d.action} ${st === 'done' || st === 'held' ? 'sent' : ''}">${LABEL[d.action]}</span>`;
}

function decideBlock(s, item) {
  if (!editable(s, item.id)) {
    const sd = s.sent[item.id];
    return `<div class="sent-note"><b>${LABEL[sd.action]}</b>${sd.note ? ` · ${esc(sd.note)}` : ''}</div>`;
  }
  const d = s.decisions[item.id] || { action: '', note: '' };
  const need = d.action && needsNote(item, d.action);
  return `<div class="decide">
    <div class="seg">${actionsFor(item).map(([a]) =>
      `<button class="a-${a} ${d.action === a ? 'on' : ''}" data-act="${a}" data-id="${item.id}">${LABEL[a]}</button>`).join('')}</div>
    ${d.action ? `<textarea class="note ${need ? 'required' : ''}" data-note="${item.id}" placeholder="${esc(PLACEHOLDER[d.action])}">${esc(d.note)}</textarea>
    <div class="hint" data-hint="${item.id}">${need && !d.note.trim() ? '내용을 적어야 전송된다' : ''}</div>` : ''}
  </div>`;
}

function card(s, item) {
  return `<article class="card k-${esc(item.kind)} st-${statusOf(s, item)} ${ui.open.has(item.id) ? 'open' : ''}" id="c-${item.id}" data-id="${item.id}">
    <div class="card-head" data-toggle="${item.id}">
      <div class="meta">
        <span class="kind k-${esc(item.kind)}">${esc(item.kind)}</span>
        <span class="iid">#${item.id}</span>
        ${item.parent ? `<button class="parent" data-jump="${item.parent}" title="출처 사안">← #${item.parent}</button>` : ''}
        <span class="spacer"></span>${stateChip(s, item)}<span class="chev">›</span>
      </div>
      <div class="title">${esc(item.title)}</div>
    </div>
    <div class="card-body"><div class="md">${md(item.body)}</div>${decideBlock(s, item)}</div>
  </article>`;
}

// 턴 머리의 입력문은 두 줄까지만. ⋮ 를 누르면 펼친다
function promptBlock(turn, text) {
  const open = ui.promptOpen.has(turn);
  const long = text.split('\n').length > 2 || text.length > 70;
  return `<div class="col-prompt ${open ? 'open' : ''}">${esc(text)}</div>
    ${long ? `<button class="more ${open ? 'open' : ''}" data-prompt="${turn}" title="${open ? '접기' : '펼치기'}">⋮</button>` : ''}`;
}

// 종합 의견 카드: 응답에서 첫 사안 앞에 쓴 글. 피드백은 선택이고 승인 조건에 들지 않는다
function summaryCard(s, t, isCur) {
  if (!t.preamble) return '';
  const sent = s.summarySent[t.turn];
  const input = isCur && !s.running
    ? `<textarea class="note" data-summary="${t.turn}" placeholder="종합 의견에 대한 피드백 (선택)">${esc(s.summary[t.turn] || '')}</textarea>`
    : sent ? `<div class="sent-note"><b>피드백</b> · ${esc(sent)}</div>` : '';
  return `<article class="card summary" id="sum-${t.turn}">
    <div class="card-head"><div class="meta"><span class="kind k-종합">종합 의견</span><span class="spacer"></span>
      ${sent ? '<span class="state s-confirm sent">피드백</span>' : ''}</div></div>
    <div class="card-body"><div class="md">${md(t.preamble)}</div>${input}</div>
  </article>`;
}

function column(s, t, isCur) {
  const todo = t.items.filter(i => statusOf(s, i) === 'todo').length;
  return `<section class="col ${isCur ? 'col-cur' : 'col-prev'}" data-turn="${t.turn}">
    <header class="col-head">
      <div class="col-title"><b>TURN ${pad(t.turn)}</b><span>사안 ${t.items.length}${todo ? ` · 미처리 ${todo}` : ''}</span></div>
      ${promptBlock(t.turn, t.prompt)}
    </header>
    <div class="col-items">${summaryCard(s, t, isCur)}${sorted(t.items).map(i => card(s, i)).join('')}</div>
  </section>`;
}

// 전송 시안. 처리 안 된 사안도 자리를 보여 줘서 입력에 따라 채워지는 게 보이게 한다
function draftHTML(s) {
  const lines = summaryNote(s) ? [`<div class="dl extra">종합 의견에 대해: ${esc(summaryNote(s))}</div>`] : [];
  lines.push(...roundItems(s).map(i => {
    const head = `${isHeld(s, i.id) ? '보류 해제: ' : ''}#${i.id} [${esc(i.kind)}] ${esc(i.title)}`;
    const d = s.decisions[i.id];
    if (isReady(s, i)) {
      const tail = d.action === 'hold' ? '보류' : `${LABEL[d.action]}${d.note.trim() ? `: ${esc(d.note.trim())}` : ''}`;
      return `<div class="dl ok"><span class="dh">${head}</span> → <span class="dt a-${d.action}">${tail}</span></div>`;
    }
    const tail = d?.action ? `${LABEL[d.action]}: 작성 중` : '미처리';
    return `<div class="dl wait"><span class="dh">${head}</span> → <span class="dt">${tail}</span></div>`;
  }));
  const keep = heldItems(s).map(i => `#${i.id}`);
  if (keep.length) lines.push(`<div class="dl keep">보류 유지: ${keep.join(', ')}</div>`);
  if (s.extra.trim()) lines.push(`<div class="dl extra">${esc(s.extra.trim())}</div>`);
  return lines.join('') || '<div class="dl wait">보낼 내용 없음</div>';
}

function progressHTML(s) {
  const { done, total } = progress(s);
  const pct = total ? Math.round(done / total * 100) : 100;
  return `<div class="prog-row"><span>처리 ${done} / ${total}</span><span>${done === total ? '모두 처리됨' : `남은 사안 ${total - done}`}</span></div>
    <div class="prog-bar"><i style="width:${pct}%"></i></div>`;
}

function nextColumn(s) {
  const next = pad(s.turns.length + 1);
  if (s.running) {
    return `<section class="col col-next col-run">
      <header class="col-head"><div class="col-title"><b>TURN ${next}</b><span class="working"><span class="dot working"></span>에이전트 작업 중</span></div></header>
      <div class="draft">${esc(s.running)}</div>
      <div class="run-ghost"></div><div class="run-ghost short"></div>
    </section>`;
  }
  return `<section class="col col-next">
    <header class="col-head"><div class="col-title"><b>NEXT INPUT</b><span>TURN ${next}</span></div></header>
    <div class="prog" id="prog">${progressHTML(s)}</div>
    <button class="primary send" id="btn-send" ${canSend(s) ? '' : 'disabled'}>승인 및 작업</button>
    <div class="draft-label">전송 시안</div>
    <div class="draft" id="draft">${draftHTML(s)}</div>
    <textarea class="note" data-extra placeholder="추가 지시 (선택). 시안 끝에 붙는다">${esc(s.extra)}</textarea>
  </section>`;
}

// 현재 턴에서 NEXT INPUT 으로 넘어가는 화살표. 화면 중간 높이에 머문다
function arrow(s) {
  const on = s.running || canSend(s);
  return `<div class="next-arrow ${on ? 'on' : ''}" id="next-arrow"><i></i></div>`;
}

function renderMain(s) {
  if (!s.turns.length) {
    return `<div class="empty">${s.status === 'working' ? '에이전트 작업 중. 턴이 끝나면 사안 기둥이 생긴다' : '아직 사안 없음'}<br><small>MOCK / 연결된 세션 아님</small></div>`;
  }
  const last = s.turns.length - 1;
  return `<section class="pane">
    <header class="pane-bar"><span class="pane-name">흐름</span><span class="pane-info">턴 ${s.turns.length} · 사안 ${allItems(s).length}</span>
      <button class="pane-gear ${ui.drawer === 'flow' ? 'on' : ''}" data-drawer="flow" title="흐름 설정">${GEAR}</button></header>
    <div class="flow" id="flow"><div class="flow-inner" id="flow-inner">
      <svg class="edges" id="edges"></svg>
      ${s.turns.map((t, i) => column(s, t, i === last)).join('')}${arrow(s)}${nextColumn(s)}
    </div></div>
  </section>`;
}

const GEAR = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`;

// 오른쪽에서 밀려 나오는 설정창. flow: 흐름 영역 설정, global: 전역 설정
function drawerHTML() {
  if (ui.drawer === 'global') {
    return `<div class="ps-title">전역 설정<button class="x" data-drawer="global" title="닫기">×</button></div>
      <label class="ps-row"><span>테마</span><select id="theme-select">
        <option value="future-industry" ${ui.theme === 'future-industry' ? 'selected' : ''}>FutureIndustry</option>
        <option value="base" ${ui.theme === 'base' ? 'selected' : ''}>Base</option></select></label>
      <div class="ps-row muted"><span>사안 규약</span><code>docs/item-protocol.md</code></div>
      <div class="ps-row muted"><span>캡처 저장</span><code>data/captures/</code></div>`;
  }
  const fonts = Object.entries(FONT_KEYS).map(([k, label]) => `<div class="ps-row"><span>${label} 글자</span>
    <span class="stepper"><button data-fs="${k}" data-delta="-1">−</button><b>${ui.fs[k]}</b><button data-fs="${k}" data-delta="1">+</button></span></div>`).join('');
  return `<div class="ps-title">흐름 설정<button class="x" data-drawer="flow" title="닫기">×</button></div>${fonts}
    <label class="ps-row"><span>언급 선 표시 <small>본문에서 #ID 로 언급한 관계</small></span>
      <input type="checkbox" data-pref="refs" ${ui.refs ? 'checked' : ''}></label>`;
}

function renderDrawer() {
  const d = $('#drawer');
  if (ui.drawer) d.innerHTML = drawerHTML();
  d.classList.toggle('open', !!ui.drawer);
  document.querySelectorAll('[data-drawer]').forEach(b => b.classList.toggle('on', b.dataset.drawer === ui.drawer));
}

function renderTerm(s) {
  $('#term-title').textContent = `${s.project} · ${s.agent}`;
  const parts = s.turns.flatMap(t => [`<span class="prompt">&gt; ${esc(t.prompt)}</span>`, esc(t.text)]);
  s.log.forEach(m => parts.push(`<span class="prompt">&gt; ${esc(m)}</span>`));
  $('#term-body').innerHTML = parts.join('\n\n') || '<span class="prompt">&gt; </span>';
}

let resizeObs = null;
function render({ keepScroll = true } = {}) {
  const s = cur();
  const prev = $('#flow');
  const scroll = keepScroll && prev ? [prev.scrollLeft, prev.scrollTop] : null;
  document.documentElement.dataset.theme = ui.theme;
  renderTabs();
  $('#main').innerHTML = renderMain(s);
  $('#term').hidden = !ui.term;
  $('#toggle-term').classList.toggle('on', ui.term);
  renderTerm(s);
  renderDrawer();

  const flow = $('#flow');
  if (!flow) return;
  if (scroll) [flow.scrollLeft, flow.scrollTop] = scroll;
  else flow.scrollLeft = flow.scrollWidth;
  resizeObs?.disconnect();
  resizeObs = new ResizeObserver(() => drawEdges());
  resizeObs.observe($('#flow-inner'));
  drawEdges();
}

// 선 그리기. 카드 머리 오른쪽에서 다음 카드 머리 왼쪽으로
function drawEdges() {
  const inner = $('#flow-inner');
  const svg = $('#edges');
  if (!inner || !svg) return;
  const box = inner.getBoundingClientRect();
  svg.setAttribute('width', inner.scrollWidth);
  svg.setAttribute('height', inner.scrollHeight);
  const anchor = (id, side) => {
    const head = document.querySelector(`#c-${CSS.escape(id)} .card-head`);
    if (!head) return null;
    const r = head.getBoundingClientRect();
    return { x: (side === 'out' ? r.right : r.left) - box.left, y: r.top + Math.min(r.height / 2, 22) - box.top };
  };
  const edges = edgesOf(cur()).filter(e => ui.refs || e.type !== 'ref');
  // 한 카드에 선이 여럿 붙으면 위아래로 벌린다
  const ports = (key) => {
    const groups = {};
    edges.forEach((e, i) => (groups[e[key]] ||= []).push(i));
    const off = {};
    for (const list of Object.values(groups)) {
      list.forEach((ei, k) => { off[ei] = Math.max(-18, Math.min(18, (k - (list.length - 1) / 2) * 8)); });
    }
    return off;
  };
  const outOff = ports('from');
  const inOff = ports('to');
  const LEAD = 10;
  svg.innerHTML = edges.map((e, i) => {
    const a = anchor(e.from, 'out');
    const b = anchor(e.to, 'in');
    if (!a || !b) return '';
    a.y += outOff[i];
    b.y += inOff[i];
    // 양 끝은 짧은 수평 직선, 사이만 곡선. 제어점을 길게 둬서 끝이 눕게 한다
    const x1 = a.x + LEAD;
    const x2 = b.x - LEAD;
    const dx = Math.max(28, (x2 - x1) * 0.55);
    return `<g class="edge e-${e.type}" data-from="${e.from}" data-to="${e.to}">
      <path d="M${a.x},${a.y} L${x1},${a.y} C${x1 + dx},${a.y} ${x2 - dx},${b.y} ${x2},${b.y} L${b.x - 6},${b.y}"/>
      <circle cx="${a.x}" cy="${a.y}" r="2.5"/><path class="tip" d="M${b.x - 7},${b.y - 3.5} L${b.x},${b.y} L${b.x - 7},${b.y + 3.5} Z"/></g>`;
  }).join('');
}

// 카드에 올리면 연결된 카드와 선만 밝힌다
function light(id) {
  const inner = $('#flow-inner');
  if (!inner) return;
  inner.querySelectorAll('.lit').forEach(el => el.classList.remove('lit'));
  inner.classList.toggle('dim', !!id);
  if (!id) return;
  const related = new Set([id]);
  inner.querySelectorAll('.edge').forEach(g => {
    if (g.dataset.from === id || g.dataset.to === id) {
      g.classList.add('lit');
      related.add(g.dataset.from); related.add(g.dataset.to);
    }
  });
  related.forEach(r => document.getElementById(`c-${r}`)?.classList.add('lit'));
}

function flash(el) {
  if (!el) return;
  el.classList.remove('flash');
  void el.offsetWidth;
  el.classList.add('flash');
}

function send() {
  const s = cur();
  if (!canSend(s)) return;
  const msg = compose(s);
  allItems(s).filter(i => isReady(s, i)).forEach(i => { s.sent[i.id] = { ...s.decisions[i.id] }; ui.open.delete(i.id); });
  if (summaryNote(s)) { s.summarySent[s.turns.length] = summaryNote(s); s.summary[s.turns.length] = ''; }
  s.log.push(msg);
  s.running = msg;
  s.extra = '';
  s.status = 'working';
  render();
  $('#flow').scrollLeft = $('#flow').scrollWidth;
}

function jumpTo(id) {
  ui.open.add(id);
  render();
  const el = document.getElementById(`c-${id}`);
  el?.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
  flash(el);
}

// 입력 중에는 전체를 다시 그리지 않고 바뀐 부분만 고친다
function refreshLive(s, id) {
  if (id) {
    const item = findItem(s, id);
    const el = document.getElementById(`c-${id}`);
    el.className = el.className.replace(/st-\w+/, `st-${statusOf(s, item)}`);
    const need = needsNote(item, s.decisions[id].action);
    el.querySelector('[data-hint]').textContent = need && !s.decisions[id].note.trim() ? '내용을 적어야 전송된다' : '';
  }
  if ($('#draft') && $('#prog')) {
    $('#draft').innerHTML = draftHTML(s);
    $('#prog').innerHTML = progressHTML(s);
    $('#btn-send').disabled = !canSend(s);
    $('#next-arrow').classList.toggle('on', canSend(s));
  }
  renderTabs();
}

function applyFonts() {
  for (const [k, v] of Object.entries(ui.fs)) document.documentElement.style.setProperty(`--fs-${k}`, `${v}px`);
  requestAnimationFrame(drawEdges);
}

document.addEventListener('click', e => {
  if (ui.drawer && !e.target.closest('#drawer, [data-drawer]')) { ui.drawer = null; renderDrawer(); }
  const t = e.target.closest('[data-tab],[data-jump],[data-act],[data-toggle],[data-prompt],[data-drawer],[data-fs],#toggle-term,#btn-send');
  if (!t) return;
  const s = cur();
  if (t.dataset.drawer) {
    ui.drawer = ui.drawer === t.dataset.drawer ? null : t.dataset.drawer;
    renderDrawer();
  }
  else if (t.dataset.fs) {
    const k = t.dataset.fs;
    ui.fs[k] = Math.min(22, Math.max(10, ui.fs[k] + Number(t.dataset.delta)));
    savePref(`overseer.fs.${k}`, String(ui.fs[k]));
    applyFonts();
    t.parentElement.querySelector('b').textContent = ui.fs[k];
  }
  else if (t.dataset.tab) { ui.cur = t.dataset.tab; render({ keepScroll: false }); }
  else if (t.dataset.jump) { e.stopPropagation(); jumpTo(t.dataset.jump); }
  else if (t.dataset.prompt) {
    const n = Number(t.dataset.prompt);
    ui.promptOpen.has(n) ? ui.promptOpen.delete(n) : ui.promptOpen.add(n);
    render();
  }
  else if (t.dataset.act) {
    const d = s.decisions[t.dataset.id] ||= { action: '', note: '' };
    d.action = d.action === t.dataset.act ? '' : t.dataset.act;
    render();
    document.querySelector(`[data-note="${t.dataset.id}"]`)?.focus();
  }
  else if (t.dataset.toggle) {
    const id = t.dataset.toggle;
    ui.open.has(id) ? ui.open.delete(id) : ui.open.add(id);
    document.getElementById(`c-${id}`).classList.toggle('open');
  }
  else if (t.id === 'toggle-term') { ui.term = !ui.term; render(); }
  else if (t.id === 'btn-send') { send(); }
});

document.addEventListener('input', e => {
  const s = cur();
  if (e.target.dataset.note) {
    s.decisions[e.target.dataset.note].note = e.target.value;
    refreshLive(s, e.target.dataset.note);
  } else if (e.target.dataset.summary) {
    s.summary[e.target.dataset.summary] = e.target.value;
    refreshLive(s, null);
  } else if ('extra' in e.target.dataset) {
    s.extra = e.target.value;
    refreshLive(s, null);
  }
});

document.addEventListener('change', e => {
  if (e.target.dataset.pref === 'refs') {
    ui.refs = e.target.checked;
    savePref('overseer.refs', ui.refs ? '1' : '0');
    drawEdges();
  } else if (e.target.id === 'theme-select') {
    ui.theme = e.target.value;
    savePref('overseer.theme', ui.theme);
    document.documentElement.dataset.theme = ui.theme;
    requestAnimationFrame(drawEdges);
  }
});

document.addEventListener('mouseover', e => {
  const c = e.target.closest('.card');
  light(c ? c.dataset.id : null);
});
window.addEventListener('resize', drawEdges);

// URL 해시로 초기 화면 지정: #term, #drawer
if (location.hash.includes('term')) ui.term = true;
if (location.hash.includes('drawer')) ui.drawer = 'flow';

// 처음엔 미처리 사안만 펼쳐 둔다
sessions.forEach(s => allItems(s).forEach(i => { if (statusOf(s, i) === 'todo') ui.open.add(i.id); }));
applyFonts();
render({ keepScroll: false });
document.fonts?.ready.then(drawEdges);
