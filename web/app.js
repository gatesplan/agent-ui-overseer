// Overseer 화면. 왼쪽은 모듈 패널(module-panel.js), 오른쪽은 커맨드 패널이다
// 커맨드 패널은 현재 턴의 사안 카드와 보내기 버튼. 보류한 사안은 막을 씌워 맨 아래에 둔다
// 지난 턴은 접힌 띠로 두고, 펼치면 모듈 패널 위에 턴 기둥으로 보인다. 카드를 누르면 파생·언급으로 이어진 카드만 밝힌다
'use strict';

// close: 보류함에서 닫음. 에이전트에게 보내지 않는 패널 처리
const LABEL = { answer: '답변', approve: '승인', revise: '수정', hold: '보류', reject: '기각', confirm: '확인', close: '닫음' };
// 사안 종류별 처리 버튼. 두 번째 값은 의견 필수 여부
const ACTIONS = {
  질문: [['answer', true], ['hold', false], ['reject', true]],
  // 수정: 방향은 맞고 수정안을 반영해 다시 제안받는다. 기각(이 방향은 아님)과 기록을 나눈다
  제안: [['approve', false], ['revise', true], ['hold', false], ['reject', true]],
  // 보고는 확인만. 덧붙일 말은 확인의 의견칸에 쓴다
  보고: [['confirm', false]],
};
const PLACEHOLDER = {
  answer: '답변 (필수)', approve: '조건이나 고칠 점 (선택). 반영해서 바로 진행한다', hold: '보류 메모 (선택, 전송 안 함)',
  revise: '수정안 (필수). 반영한 제안을 다시 받는다',
  reject: '기각 사유 (필수). 사유가 없으면 에이전트가 다음 판단을 못 한다', confirm: '덧붙일 말 (선택)',
};
// 보존 표시. 사안 종류 라벨 뒤에 붙는다. 승인하거나 답하면 영속 지식에 들어간다
const TAGS = { W: '용어', D: '결정 기록' };
// 정리 요청: 다음 세션에도 유효한 용어와 결정을 보존 사안으로 올리게 한다
// 걸러내는 기준은 규약(docs/item-protocol.md 보존 사안)에 두고, 문구는 짧게 둔다
const WRAPUP = '정리: 이 세션에서 내가 결정한 것 중 기록이 없으면 다음 세션이 다르게 판단할 것만 [D], [W] 사안으로 올려 줘. 근거 사안 ID를 붙여서.';
// 정리 턴 표시. 문구가 바뀌어도 예전 정리 턴을 알아보도록 줄 머리로 찾는다
const WRAPUP_LINE = /^정리: /m;
// 턴 안 정렬: 보고, 질문, 제안. 규약 밖 종류는 맨 뒤
const KIND_ORDER = { 보고: 0, 질문: 1, 제안: 2 };
const FONT_KEYS = { cur: '커맨드 카드', prev: '지난 턴 카드', head: '턴 머리', map: '모듈 카드' };
const FONT_DEFAULT = { cur: 16, prev: 14, head: 14, map: 12 };

const blank = { decisions: {}, sent: {}, log: [], extra: '', wrapup: false, running: null, turns: [], summary: {}, summarySent: {}, alive: true, map: null, modules: null };
// 실제 모드: 패널 서버(scripts 의 overseer)가 있으면 그 탭을 쓴다. 없으면(serve_mock) 목업 데이터를 쓴다
let LIVE = false;
let sessions = [];

function mockSessions() {
  const list = window.MOCK.sessions.map(s => ({
    ...blank, ...s,
    decisions: Object.fromEntries(Object.entries(s.decisions).map(([k, [a, n]]) => [k, { action: a, note: n }])),
    sent: Object.fromEntries((s.sent || []).map(id => [id, { action: s.decisions[id][0], note: s.decisions[id][1] }])),
    log: [],
  }));
  list.push({ ...blank, id: 'fmp', project: 'fishmathpics', agent: 'codex', status: 'idle', log: [] });
  return list;
}

// 서버 탭 상태를 화면 세션으로. 작성 중인 처리, 의견, 추가 지시는 화면이 주인이라 처음 한 번만 서버 초안에서 읽는다
function fromServer(t, prev) {
  const d = t.draft || {};
  return {
    ...blank, ...t,
    turns: t.turns.map(x => ({ ...x, wrapup: WRAPUP_LINE.test(x.prompt) })),
    decisions: prev ? prev.decisions : (d.decisions || {}),
    summary: prev ? prev.summary : (d.summary || {}),
    extra: prev ? prev.extra : (d.extra || ''),
    wrapup: prev ? prev.wrapup : !!d.wrapup,
    // 모듈 패널에서 한 일(보낼 것)과 받아 둔 지도는 탭 알림이 와도 이어 간다
    map: prev ? prev.map : (d.map || null),
    modules: prev ? prev.modules : null,
    _mpIndex: prev ? prev._mpIndex : null,
    _mpGood: prev ? prev._mpGood : null,
    _mpLoading: prev ? prev._mpLoading : false,
    log: [],
  };
}

function pref(key, fallback) { try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; } }
function savePref(key, value) { try { localStorage.setItem(key, value); } catch { /* 저장 못 해도 동작엔 지장 없음 */ } }

const ui = {
  cur: null, active: null, term: false, open: new Set(), promptOpen: new Set(), drawer: null,
  // /clear 앞 턴까지 펼쳐 보는 탭
  showOld: new Set(),
  theme: pref('overseer.theme', 'future-industry'),
  refs: pref('overseer.refs', '1') === '1',
  // 지난 턴 펼침, 보류 막을 걷은 사안, 추가 지시 칸
  past: false, unveil: new Set(), extraOpen: false,
  // 띄우면서 터미널 창을 연 탭. 시작 훅이 오면 접고, 사용자가 직접 여닫으면 그대로 둔다
  autoTerm: null,
  // 모듈 패널: 고정한 모듈, 탭별 펼친 중첩 모듈, 책임 카드 창
  mpPin: null, mpOpen: {}, mpThrow: false,
  peekDelay: Number(pref('overseer.peek', '0.5')),
  vocabFaint: pref('overseer.vocab', '1') === '1',
  showBlast: pref('overseer.blast', '1') === '1',
  rememberOpen: pref('overseer.mpremember', '1') === '1',
  fs: Object.fromEntries(Object.keys(FONT_KEYS).map(k => [k, Number(pref(`overseer.fs.${k}`, FONT_DEFAULT[k]))])),
};
const $ = sel => document.querySelector(sel);
const cur = () => sessions.find(s => s.id === ui.cur);
const sorted = items => [...items].sort((a, b) => (KIND_ORDER[a.kind] ?? 9) - (KIND_ORDER[b.kind] ?? 9));
const allItems = s => s.turns.flatMap(t => sorted(t.items));
const findItem = (s, id) => allItems(s).find(i => i.id === id);
// 카드 요소. 커맨드 패널(c-)이 먼저, 없으면 지난 턴(p-)
const cardEl = id => id && (document.getElementById(`c-${id}`) || document.getElementById(`p-${id}`));
const actionsFor = item => ACTIONS[item.kind] || ACTIONS['질문'];
const pad = n => String(n).padStart(2, '0');
const turnOf = id => Number(id.split('-')[0]);
const label = item => `[${item.kind}]${item.tag ? `[${item.tag}]` : ''}`;
// 보존 사안의 근거 줄: `근거: #1-2, #1-4`
const BASIS = /^근거:(.*)$/m;
// 보존 사안의 대체 대상 줄: `대체: D-3`
const REPLACES = /^대체:\s*([DW]-\d+).*$/m;
const basisOf = item => item.tag ? [...((item.body.match(BASIS) || [])[1] || '').matchAll(/#(\d+-\d+)/g)].map(m => m[1]) : [];

function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function inline(s) {
  return esc(s).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
}
function md(text) {
  const out = [];
  let list = null;
  let rows = null;
  const flush = () => {
    if (list) { out.push(`<ul>${list.join('')}</ul>`); list = null; }
    if (rows) { out.push(table(rows)); rows = null; }
  };
  for (const line of text.split('\n')) {
    if (/^\s*\|/.test(line)) {
      if (list) flush();
      (rows ||= []).push(line);
      continue;
    }
    if (rows) flush();
    const m = line.match(/^\s*[-*]\s+(.*)$/);
    if (m) { (list ||= []).push(`<li>${inline(m[1])}</li>`); continue; }
    flush();
    if (line.trim()) out.push(`<p>${inline(line)}</p>`);
  }
  flush();
  return out.join('');
}

// 마크다운 표. 둘째 줄이 구분 줄(|---|:--:|)이면 첫 줄이 머리, 구분 줄의 콜론으로 정렬한다
// 카드 폭이 좁아 넘치면 표만 가로로 스크롤한다
function cells(line) {
  const s = line.trim().replace(/^\|/, '').replace(/(^|[^\\])\|$/, '$1');
  return s.split(/(?<!\\)\|/).map(c => c.trim().replace(/\\\|/g, '|'));
}
function table(lines) {
  const rows = lines.map(cells);
  const sep = rows.length > 1 && rows[1].every(c => /^:?-+:?$/.test(c));
  const align = sep ? rows[1].map(c => c.endsWith(':') ? (c.startsWith(':') ? 'center' : 'right') : '') : [];
  const td = (tag, row) => row.map((c, k) => `<${tag}${align[k] ? ` style="text-align:${align[k]}"` : ''}>${inline(c)}</${tag}>`).join('');
  const head = sep ? `<thead><tr>${td('th', rows[0])}</tr></thead>` : '';
  const body = (sep ? rows.slice(2) : rows).map(r => `<tr>${td('td', r)}</tr>`).join('');
  return `<div class="md-table"><table>${head}<tbody>${body}</tbody></table></div>`;
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
// /clear 앞의 턴은 처리가 끝났으니 접는다. 보류에서 꺼내 다시 처리 중인 사안이 있는 턴은 보인다
function visibleTurns(s) {
  if (!s.cleared || ui.showOld.has(s.id)) return s.turns;
  return s.turns.filter(t => t.turn > s.cleared || t.items.some(i => ['todo', 'ready'].includes(statusOf(s, i))));
}
// 접힌 턴의 사안으로 가야 하면 앞 턴을 펼친다
function reveal(s, id) {
  if (s && !visibleTurns(s).some(t => t.turn === turnOf(id))) ui.showOld.add(s.id);
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
  return s.alive && !s.starting && !s.running && done === total && !!compose(s);
}

// 관계: 출처(parent), 보존 사안의 근거(basis), 본문에서 앞 턴 사안을 #ID 로 언급한 것(ref)
function edgesOf(s) {
  const ids = new Set(allItems(s).map(i => i.id));
  const edges = [];
  for (const i of allItems(s)) {
    if (i.parent && ids.has(i.parent)) edges.push({ from: i.parent, to: i.id, type: 'parent' });
    const basis = basisOf(i).filter(r => ids.has(r));
    basis.forEach(r => edges.push({ from: r, to: i.id, type: 'basis' }));
    const refs = new Set([...i.body.matchAll(/#(\d+-\d+)/g)].map(m => m[1]));
    for (const r of refs) {
      if (r !== i.parent && !basis.includes(r) && ids.has(r) && turnOf(r) < turnOf(i.id)) edges.push({ from: r, to: i.id, type: 'ref' });
    }
  }
  return edges;
}

// 선택한 사안과 이어진 사안: 출처 쪽으로 거슬러 오른 것 전부와 파생 쪽으로 내려간 것 전부
function relatedOf(s, id) {
  const edges = edgesOf(s).filter(e => ui.refs || e.type !== 'ref');
  const walk = (from, to) => {
    const seen = new Set();
    const queue = [id];
    while (queue.length) {
      const x = queue.shift();
      for (const e of edges) {
        if (e[from] === x && !seen.has(e[to])) { seen.add(e[to]); queue.push(e[to]); }
      }
    }
    return seen;
  };
  return new Set([id, ...walk('to', 'from'), ...walk('from', 'to')]);
}

// 전송 메시지
function summaryNote(s) { return s.running ? '' : (s.summary[s.turns.length] || '').trim(); }

// 덧붙인 말 없이 확인만 한 사안. 한 줄 `확인: #a, #b` 로 묶어 보낸다. 에이전트가 하나씩 답하며 늘어지지 않게
function bareConfirm(s, i) {
  const d = s.decisions[i.id];
  return isReady(s, i) && d.action === 'confirm' && !d.note.trim();
}

function compose(s) {
  const lines = [];
  if (summaryNote(s)) lines.push(`종합 의견에 대해: ${summaryNote(s)}`);
  const confirmed = allItems(s).filter(i => bareConfirm(s, i)).map(i => `#${i.id}`);
  for (const i of allItems(s).filter(i => isReady(s, i) && !bareConfirm(s, i))) {
    const d = s.decisions[i.id];
    const head = `${isHeld(s, i.id) ? '보류 해제: ' : ''}#${i.id} ${label(i)} ${i.title}`;
    const tail = d.action === 'hold' ? '보류' : `${LABEL[d.action]}${d.note.trim() ? `: ${d.note.trim()}` : ''}`;
    lines.push(`${head} → ${tail}`);
  }
  if (confirmed.length) lines.push(`확인: ${confirmed.join(', ')} 사안 종료됨.`);
  lines.push(...mapLines(s));
  if (s.wrapup) lines.push(WRAPUP);
  if (s.extra.trim()) lines.push(s.extra.trim());
  return lines.join('\n');
}

// 렌더 조각
function renderTabs() {
  // 사용자를 기다리는 탭이 있으면 브라우저 탭 제목에도 표시한다. 다른 창을 보고 있어도 알 수 있게
  const waiting = sessions.filter(s => s.status === 'attention').length;
  document.title = waiting ? `(${waiting}) 확인 필요 · Overseer` : 'Overseer';
  $('#tabs').innerHTML = sessions.map(s => {
    const n = allItems(s).filter(i => statusOf(s, i) === 'todo').length;
    return `<button class="tab ${s.id === ui.cur ? 'on' : ''}" data-tab="${s.id}" title="${esc(s.cwd || s.project)}${s.args ? `\nclaude ${esc(s.args)}` : ''}">
      <span class="dot ${s.status}"></span>${esc(s.project)} <span class="agent">${s.agent}</span>
      ${n ? `<span class="badge">${n}</span>` : ''}${LIVE ? `<span class="tab-x" data-close="${s.id}" title="탭 닫기 (세션 종료)">×</span>` : ''}</button>`;
  }).join('') + `<button class="tab add" data-newtab title="${LIVE ? '새 세션' : '새 세션 (목업)'}">+</button>`;
}

function stateChip(s, item) {
  const st = statusOf(s, item);
  const d = st === 'done' || st === 'held' ? s.sent[item.id] : s.decisions[item.id];
  if (!d || !d.action) return '';
  return `<span class="state s-${d.action} ${st === 'done' || st === 'held' ? 'sent' : ''}">${LABEL[d.action]}</span>`;
}

// 보존 사안을 승인하거나 답해서 보냈으면 영속 지식에 들어간 것으로 본다
// 실제 모드에서는 아카이브의 기록 번호를 보인다. 뒤에 대체된 기록이면 대체됨
function keptBadge(s, item) {
  const rec = (s.records || []).find(r => r.tab_id === s.id && r.item_id === item.id);
  if (rec) {
    return rec.status === 'active' ? `<span class="kept" title="${esc(rec.text)}">보존 ${rec.ref}</span>`
      : `<span class="kept old" title="뒤의 기록으로 대체됨">대체됨 ${rec.ref}</span>`;
  }
  const d = s.sent[item.id];
  return item.tag && d && ['approve', 'answer'].includes(d.action) ? '<span class="kept">보존됨</span>' : '';
}

// 보존 사안의 형식 경고. [D] 는 한 줄 60자, [W] 는 `용어: 뜻` 에 뜻 20자 안팎(30자 넘으면 경고)
function keepWarnings(item) {
  const warn = [];
  if (item.tag === 'D' && item.title.length > 60) warn.push(`결정이 60자를 넘는다 (${item.title.length}자)`);
  if (item.tag === 'W') {
    const i = item.title.indexOf(':');
    if (i < 0) warn.push('`용어: 뜻` 형식이 아니다');
    else if (item.title.slice(i + 1).trim().length > 30) warn.push(`뜻이 길다 (${item.title.slice(i + 1).trim().length}자, 20자 안팎)`);
  }
  return warn.map(w => `<div class="bs warn">${esc(w)}</div>`).join('');
}

// 대체 대상: `대체: D-3` 이 가리키는 기록을 옆에 보여 준다. 없거나 이미 대체된 기록이면 경고
function replaceBlock(s, item) {
  const ref = (item.body.match(REPLACES) || [])[1];
  if (!ref || !LIVE) return '';
  const own = (s.records || []).find(r => r.tab_id === s.id && r.item_id === item.id);
  const target = (s.records || []).find(r => r.ref === ref);
  let row;
  if (!target) row = `<div class="bs warn">${ref} 없는 기록</div>`;
  else if (target.status !== 'active' && !(own && target.replaced_by === own.id)) row = `<div class="bs warn">${ref} 이미 대체된 기록: ${esc(target.text)}</div>`;
  else row = `<div class="bs"><span class="iid">${ref}</span> ${esc(target.text)}${target.note ? `<span class="bd">메모: ${esc(target.note)}</span>` : ''}</div>`;
  return `<div class="basis"><div class="basis-label">대체 대상</div>${row}</div>`;
}

// 보존 사안의 근거: 인용한 사안에 사용자가 실제로 보낸 결정을 옆에 보여 준다
// 근거가 없거나 사용자 결정이 없는 사안을 인용했으면 경고한다. 에이전트가 가정으로 올린 기록을 걸러 내려는 것
function basisBlock(s, item) {
  if (!item.tag) return '';
  const ids = basisOf(item);
  const rows = ids.map(id => {
    const src = findItem(s, id);
    if (!src) return `<div class="bs warn">#${id} 찾을 수 없는 사안</div>`;
    const d = s.sent[id];
    if (!d) return `<div class="bs warn"><span class="iid">#${id}</span> ${esc(src.title)}<span class="bd">사용자 결정 없음</span></div>`;
    return `<div class="bs"><span class="iid">#${id}</span> ${esc(src.title)}<span class="bd a-${d.action}">${LABEL[d.action]}${d.note ? `: ${esc(d.note)}` : ''}</span></div>`;
  });
  if (!ids.length) rows.push('<div class="bs warn">근거 사안 없음. 사용자 결정 없이 올린 기록일 수 있다</div>');
  return `<div class="basis"><div class="basis-label">근거 결정</div>${rows.join('')}${keepWarnings(item)}</div>${replaceBlock(s, item)}`;
}

function decideBlock(s, item) {
  if (!editable(s, item.id)) {
    const sd = s.sent[item.id];
    return `<div class="sent-note"><b>${LABEL[sd.action]}</b>${sd.note ? ` · ${esc(sd.note)}` : ''}</div>`;
  }
  const d = s.decisions[item.id] || { action: '', note: '' };
  const need = d.action && needsNote(item, d.action);
  return `<div class="decide">
    <div class="seg">${actionsFor(item).map(([a], n) =>
      `<button class="a-${a} ${d.action === a ? 'on' : ''}" data-act="${a}" data-id="${item.id}">${LABEL[a]}<kbd>${n + 1}</kbd>${n ? '' : '<span class="kbd-or">|</span><kbd>Enter</kbd>'}</button>`).join('')}</div>
    ${d.action ? `<textarea class="note ${need ? 'required' : ''}" data-note="${item.id}" placeholder="${esc(PLACEHOLDER[d.action])}">${esc(d.note)}</textarea>
    <div class="hint" data-hint="${item.id}">${need && !d.note.trim() ? '내용을 적어야 전송된다' : ''}</div>` : ''}
  </div>`;
}

// 선택된 카드 머리 오른쪽 끝에만 보이는 선택 해제 버튼
const UNPICK = `<button class="unpick" data-unpick title="선택 해제 (Esc)" aria-label="선택 해제"><svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="8" cy="8" r="6"/><path d="M3.8 12.2 12.2 3.8"/></svg></button>`;

// 현재 턴 카드는 늘 펼쳐 두고 접지 않는다. 이전 턴 카드만 머리를 눌러 접고 편다
// veil: 커맨드 패널 맨 아래의 보류 카드. 카드 모양 그대로 흐린 막을 씌운다
function card(s, item, isCur, prefix = 'c', veil = false) {
  const open = isCur || ui.open.has(item.id);
  const mods = itemModules(s, item);
  const held = veil ? `<div class="veil"><div class="veil-title"><span>TURN ${pad(turnOf(item.id))}</span> - ${esc(item.title)}</div>
      <div class="veil-why ${s.sent[item.id]?.note ? '' : 'none'}">${esc(s.sent[item.id]?.note || '보류 이유 없음')}</div>
      <div class="veil-btns"><button data-unhold="${item.id}" title="막을 걷고 다시 처리를 고른다">꺼내기</button><button data-closeheld="${item.id}" title="에이전트에게 보내지 않고 끝낸다">닫기</button></div></div>` : '';
  return `<article class="card k-${esc(item.kind)} st-${statusOf(s, item)} ${open ? 'open' : ''} ${isCur ? 'fixed' : ''} ${veil ? 'held-card' : ''}" id="${prefix}-${item.id}" data-id="${item.id}">
    <div class="card-head" ${isCur ? '' : `data-toggle="${item.id}"`}>
      <div class="meta">
        <span class="kind k-${esc(item.kind)}">${esc(item.kind)}</span>${item.tag ? `<kbd class="tag" title="${TAGS[item.tag] || ''}">${esc(item.tag)}</kbd>` : ''}
        <span class="iid">#${item.id}</span>
        ${item.parent ? `<button class="parent" data-jump="${item.parent}" title="출처 사안">← #${item.parent}</button>` : ''}
        <span class="spacer"></span>${keptBadge(s, item)}${stateChip(s, item)}${isCur ? '' : '<span class="chev">›</span>'}${UNPICK}
      </div>
      <div class="title">${esc(item.title)}</div>
      ${mods.length ? `<div class="mods">${mods.map(m => `<button data-mod="${esc(m)}" title="모듈 패널에서 보기">${esc(m)}</button>`).join('')}</div>` : ''}
    </div>
    <div class="card-body"><div class="md">${md(item.tag ? item.body.replace(BASIS, '').replace(REPLACES, '') : item.body)}</div>${basisBlock(s, item)}${veil ? '' : decideBlock(s, item)}</div>${held}
  </article>`;
}

// 턴 머리의 입력문은 두 줄까지만. ⋮ 를 누르면 펼친다
// 짧아서 ⋮ 가 없어도 그 자리를 비워 둔다. 기둥마다 머리 높이가 같아야 카드 줄이 맞는다
function promptBlock(turn, text) {
  const open = ui.promptOpen.has(turn);
  const long = text.split('\n').length > 2 || text.length > 70;
  return `<div class="col-prompt ${open ? 'open' : ''}">${esc(text)}</div>
    ${long ? `<button class="more ${open ? 'open' : ''}" data-prompt="${turn}" title="${open ? '접기' : '펼치기'}">⋮</button>` : '<span class="more none">⋮</span>'}`;
}

// 종합 의견 카드: 응답에서 첫 사안 앞에 쓴 글. 피드백은 선택이고 승인 조건에 들지 않는다
// 사안 카드처럼 선택할 수 있다. 선택 id 는 sum-<턴>. 이어진 사안은 없다
function summaryCard(s, t, isCur, prefix = 'c') {
  if (!t.preamble) return '';
  const sent = s.summarySent[t.turn];
  const input = isCur && !s.running
    ? `<textarea class="note" data-summary="${t.turn}" placeholder="종합 의견에 대한 피드백 (선택)">${esc(s.summary[t.turn] || '')}</textarea>`
    : sent ? `<div class="sent-note"><b>피드백</b> · ${esc(sent)}</div>` : '';
  return `<article class="card summary" id="${prefix}-sum-${t.turn}" data-id="sum-${t.turn}">
    <div class="card-head"><div class="meta"><span class="kind k-종합">종합 의견</span><span class="spacer"></span>
      ${isCur ? '<kbd class="hk" title="Home 키로 이동">Home</kbd>' : ''}
      ${sent ? '<span class="state s-confirm sent">피드백</span>' : ''}${UNPICK}</div></div>
    <div class="card-body"><div class="md">${md(t.preamble)}</div>${input}</div>
  </article>`;
}

function column(s, t, isCur, prefix = 'c') {
  const todo = t.items.filter(i => statusOf(s, i) === 'todo').length;
  return `<section class="col ${isCur ? 'col-cur' : 'col-prev'}" data-col="${t.turn}">
    <header class="col-head">
      <div class="col-title"><b>TURN ${pad(t.turn)}${t.wrapup ? '<i class="wrap-tag">정리</i>' : ''}${t.after ? `<i class="wrap-tag" title="이 턴 앞에서 에이전트 맥락이 바뀌었다">${esc(t.after)}</i>` : ''}${t.parts > 1 ? `<i class="wrap-tag" title="작업 중에 넣은 입력까지 이어서 처리해 응답이 ${t.parts}번 나온 턴">응답 ${t.parts}</i>` : ''}</b><span>사안 ${t.items.length}${todo ? ` · 미처리 ${todo}` : ''}</span></div>
      ${promptBlock(t.turn, t.prompt)}
    </header>
    <div class="col-items">${summaryCard(s, t, isCur, prefix)}${sorted(t.items).map(i => card(s, i, isCur, prefix)).join('')}</div>
  </section>`;
}

// 커맨드 패널의 카드 열. 현재 턴 사안, 다른 턴에서 아직 처리할 사안(보류에서 꺼낸 것 포함), 맨 아래에 보류한 사안
// last: 지금 맥락의 마지막 턴. 맥락을 지운 뒤 아직 응답이 없으면 null 이고 앞 맥락에서 남은 사안만 보인다
function commandColumn(s, last) {
  const here = new Set(last ? last.items.map(i => i.id) : []);
  const veiled = i => statusOf(s, i) === 'held' && !ui.unveil.has(i.id);
  const others = allItems(s).filter(i => !here.has(i.id) && !veiled(i)
    && (['todo', 'ready'].includes(statusOf(s, i)) || ui.unveil.has(i.id)));
  // 보류함에서 닫은 사안은 에이전트에게 보내지 않고 끝낸 것이라 보이지 않는다
  const closed = i => s.sent[i.id]?.action === 'close';
  const live = [...(last ? sorted(last.items) : []).filter(i => !veiled(i) && !closed(i)), ...others];
  const held = allItems(s).filter(veiled);
  const todo = live.filter(i => statusOf(s, i) === 'todo').length;
  const head = last
    ? `<div class="col-title"><b>TURN ${pad(last.turn)}${last.wrapup ? '<i class="wrap-tag">정리</i>' : ''}${last.after ? `<i class="wrap-tag" title="이 턴 앞에서 에이전트 맥락이 바뀌었다">${esc(last.after)}</i>` : ''}${last.parts > 1 ? `<i class="wrap-tag" title="작업 중에 넣은 입력까지 이어서 처리해 응답이 ${last.parts}번 나온 턴">응답 ${last.parts}</i>` : ''}</b><span>사안 ${last.items.length}${todo ? ` · 미처리 ${todo}` : ''}</span></div>
      ${promptBlock(last.turn, last.prompt)}`
    : `<div class="col-title"><b>TURN ${pad(s.turns.length + 1)}</b><span>${todo ? `앞 맥락 미처리 ${todo}` : ''}</span></div>`;
  const empty = !last && !live.length
    ? `<div class="empty">${s.running ? '에이전트 작업 중. 턴이 끝나면 사안 카드가 생긴다' : s.turns.length ? '맥락을 지웠다' : '아직 사안 없음'}<br>
      <small>${s.running ? '' : s.turns.length ? '아래 지시 칸이나 터미널 창에서 입력한다'
        : '아래 지시 칸이나 터미널 창에서 첫 입력을 한다. 시작 확인 창은 터미널에서 처리한다'}</small></div>` : '';
  return `<section class="col col-cur" data-col="cmd">
    <header class="col-head">${head}</header>
    <div class="col-items">${last ? summaryCard(s, last, true) : ''}${empty}${live.map(i => card(s, i, true)).join('')}${held.length
      ? `<div class="held-sep">보류 ${held.length}</div>${held.map(i => card(s, i, true, 'c', true)).join('')}` : ''}</div>
  </section>`;
}

async function closeHeld(id) {
  const s = cur();
  if (LIVE) { await api(`/api/tabs/${s.id}/close-held`, 'POST', { ids: [id] }); return; }
  s.sent[id] = { action: 'close', note: '' };
  render();
}

// 꺼내기: 막을 걷고 처리할 카드 쪽으로 올린다. 처리를 고르면 다음 메시지에 '보류 해제:' 로 실린다
function unhold(id) {
  ui.unveil.add(id);
  ui.active = id;
  render();
  raise(id);
  flash(cardEl(id));
}

// 보내기 줄: 정리 요청, 추가 지시, /clear, 보내기. 작업 중이면 보낸 메시지를 접어 보인다
function sendLabel(s) {
  const { done, total } = progress(s);
  const maps = mapCount(s);
  if (s.starting) return '시작 대기';
  return `보내기<span class="send-n">${total ? `${done}/${total}` : ''}${maps ? ` · 지도 ${maps}` : ''}</span>`;
}

// fresh: 처리할 카드가 없는 새 맥락(첫 실행, /clear 뒤). 지시 칸을 늘 열어 두고 거기서 첫 입력을 한다
function sendBar(s, fresh = false) {
  if (!s.alive) {
    return `<div class="send-bar"><div class="run-line">세션 꺼짐. 작성 중인 처리는 그대로 남는다</div>
      <button class="primary send" data-resume="${s.id}">이어서 띄우기</button></div>`;
  }
  const run = s.running ? `<details class="run-line"><summary><span class="dot working"></span>TURN ${pad(s.turns.length + 1)} 에이전트 작업 중</summary>
    <div class="run-msg">${esc(s.running)}</div></details>` : '';
  const extra = fresh
    ? `<textarea class="note" data-extra placeholder="에이전트에게 보낼 지시. 보내기로 터미널에 입력된다">${esc(s.extra)}</textarea>`
    : ui.extraOpen || s.extra.trim()
    ? `<textarea class="note" data-extra placeholder="추가 지시 (선택). 카드와 상관없는 지시. 보낼 메시지 끝에 붙는다">${esc(s.extra)}</textarea>` : '';
  return `<div class="send-bar">${run}${extra}
    <div class="send-row">
      <button class="wrapup ${s.wrapup ? 'on' : ''}" id="btn-wrapup" title="다음 세션에도 유효한 용어와 결정을 보존 사안으로 올리게 한다">정리 요청 ${s.wrapup ? '켬' : '끔'}</button>
      ${fresh ? '' : `<button class="bar-btn ${ui.extraOpen ? 'on' : ''}" data-extra-toggle title="카드와 상관없는 지시를 덧붙인다">+ 지시</button>`}
      <button class="clear-ctx" id="btn-clear" title="고른 처리를 패널에만 저장하고 에이전트 맥락을 지운다. 에이전트에게는 보내지 않는다">/clear</button>
      <button class="primary send" id="btn-send" ${canSend(s) ? '' : 'disabled'}>${sendLabel(s)}</button>
    </div></div>`;
}

// 권한 요청 도구 입력의 한 줄 요약
function toolSummary(p) {
  const i = p.tool_input || {};
  return i.command || i.file_path || i.notebook_path || i.url || i.pattern || i.path || JSON.stringify(i);
}

// 에이전트가 사용자를 기다리느라 멈췄을 때 흐름 위에 띄우는 띠
// 권한 요청은 여기서 바로 허용·거부한다. 그 밖의 확인은 터미널에서 한다
function attentionBar(s) {
  if (!LIVE || !s) return '';
  if (s.permission) {
    const p = s.permission;
    return `<div class="attn perm">
      <div class="attn-head"><span class="attn-tag">권한 요청</span><b>${esc(p.tool_name || '')}</b>
        <code class="attn-cmd">${esc(toolSummary(p))}</code></div>
      <details class="attn-more"><summary>입력 전체</summary><pre>${esc(JSON.stringify(p.tool_input, null, 2))}</pre></details>
      <div class="attn-actions">
        <input class="attn-note" data-perm-note placeholder="거부 사유 (선택). 에이전트에게 전해진다" value="${esc(ui.permNote || '')}">
        <button class="attn-allow" data-perm="allow" data-rid="${p.request_id}">허용</button>
        <button class="attn-deny" data-perm="deny" data-rid="${p.request_id}">거부</button>
        <button data-perm="terminal" data-rid="${p.request_id}" title="원래 확인 창을 터미널에 띄운다">터미널에서</button>
      </div></div>`;
  }
  // 띄운 뒤 시작 훅이 아직 오지 않았다. 폴더 신뢰 같은 시작 확인 창이 터미널에 떠 있을 수 있다
  if (s.starting) {
    return `<div class="attn"><div class="attn-head"><span class="attn-tag">시작 중</span><span>시작 확인 창이 떠 있으면 터미널에서 처리한다. 그때까지 패널에서 보낼 수 없다</span>
      <button data-open-term>터미널 열기</button></div></div>`;
  }
  if (s.attention) {
    return `<div class="attn"><div class="attn-head"><span class="attn-tag">터미널 확인 필요</span><span>${esc(s.attention.message || '')}</span>
      <button data-open-term>터미널 열기</button></div></div>`;
  }
  return '';
}

async function decidePermission(rid, behavior) {
  const s = cur();
  const message = behavior === 'deny' ? (ui.permNote || '').trim() : '';
  if (await api(`/api/tabs/${s.id}/permission`, 'POST', { request_id: rid, behavior, message })) {
    ui.permNote = '';
    // 터미널에서 처리하기로 했으면 확인 창이 뜰 터미널을 연다
    if (behavior === 'terminal') { ui.term = true; render(); }
  }
}

function renderMain(s) {
  if (!s) return `<div class="empty">열린 세션 없음<br><small>위의 + 로 작업 폴더를 골라 claude 를 띄운다</small></div>`;
  const bar = extra => `<header class="pane-bar"><span class="pane-name">커맨드 패널</span><span class="pane-info">턴 ${s.turns.length} · 사안 ${allItems(s).length}</span>
      ${extra}
      ${LIVE ? `<button class="pane-rec ${ui.drawer === 'records' ? 'on' : ''}" data-drawer="records" title="이 프로젝트의 결정 기록과 용어">기록 ${(s.records || []).filter(r => r.status === 'active').length}</button>` : ''}
      <button class="pane-gear ${ui.drawer === 'flow' ? 'on' : ''}" data-drawer="flow" title="커맨드 패널 설정">${GEAR}</button></header>`;
  if (!s.turns.length && !(LIVE && s.alive)) {
    const msg = !s.alive ? '세션 꺼짐' : '아직 사안 없음';
    const sub = !LIVE ? 'MOCK / 연결된 세션 아님' : `<button class="primary" data-resume="${s.id}">이어서 띄우기</button>`;
    return `<section class="cmd-pane">${bar('')}${attentionBar(s)}<div class="empty">${msg}<br><small>${sub}</small></div></section>`;
  }
  // 지금 맥락의 턴. /clear 뒤 아직 응답이 없으면 앞 맥락의 마지막 턴은 가운데 칸에 두지 않는다
  const tail = s.turns[s.turns.length - 1];
  const last = tail && (!s.cleared || tail.turn > s.cleared || ui.showOld.has(s.id)) ? tail : null;
  const fresh = !last && !roundItems(s).length;
  const shown = visibleTurns(s);
  const past = shown.filter(t => t !== last);
  const folded = s.turns.length - shown.length;
  const old = s.cleared && (folded || ui.showOld.has(s.id))
    ? `<button class="pane-rec pane-old ${ui.showOld.has(s.id) ? 'on' : ''}" data-oldturns title="마지막 /clear 앞의 턴">${folded ? `이전 맥락 ${folded}턴 보기` : '이전 맥락 접기'}</button>` : '';
  return `<button class="past-strip ${ui.past ? 'on' : ''}" data-past title="${ui.past ? '지난 턴 접기' : '지난 턴 펼치기'}" ${past.length ? '' : 'disabled'}><span>지난 턴 · ${past.length}</span></button>
    <section class="cmd-pane">
      ${bar(old)}
      ${attentionBar(s)}
      ${commandColumn(s, last)}
      ${sendBar(s, fresh)}
    </section>
    ${ui.past && past.length ? `<div class="past-flow"><div class="flow" id="flow"><div class="flow-inner" id="flow-inner">${past.map(t => column(s, t, false, 'p')).join('')}</div></div></div>` : ''}`;
}

const GEAR = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`;

// 아카이브 보기: 이 프로젝트의 결정 기록과 용어. 유효한 것 먼저, 대체된 것은 흐리게 뒤에
// 출처 사안이 이 탭에 있으면 눌러서 그 카드로 간다
function recordsHTML(s) {
  const records = (s && s.records) || [];
  const refOf = id => records.find(r => r.id === id)?.ref || '?';
  const row = r => {
    const status = r.status === 'active' ? (r.replaces ? `${refOf(r.replaces)} 대체` : '')
      : `대체됨 → ${refOf(r.replaced_by)}`;
    const source = r.tab_id === s.id ? `<button class="parent" data-jump="${esc(r.item_id)}" title="출처 사안으로">#${esc(r.item_id)}</button>`
      : `<span title="다른 탭에서 승인">다른 탭 #${esc(r.item_id || '')}</span>`;
    return `<div class="rec ${r.status}">
      <div class="rec-head"><span class="rec-ref">${r.ref}</span><span class="rec-text">${esc(r.text)}</span></div>
      ${r.note ? `<div class="rec-note">메모: ${esc(r.note)}</div>` : ''}
      <div class="rec-meta">${[status, source, (r.created_at || '').slice(0, 10)].filter(Boolean).join(' · ')}</div>
    </div>`;
  };
  const order = (a, b) => (a.status !== 'active') - (b.status !== 'active') || a.kind.localeCompare(b.kind) || a.num - b.num;
  const section = (title, list, empty = true) => {
    if (!list.length && !empty) return '';
    return `<div class="rec-sec">${title} <small>${list.filter(r => r.status === 'active').length}</small></div>${list.sort(order).map(row).join('') || '<div class="rec-empty">없음</div>'}`;
  };
  const own = records.filter(r => !r.inherited);
  return `<div class="ps-title">결정 기록과 용어<button class="x" data-drawer="records" title="닫기">×</button></div>
    <div class="rec-intro">${esc(s?.project || '')} 에서 승인한 보존 사안. 유효한 것은 세션 시작 때 에이전트에게 들어간다</div>
    ${section('결정 기록', own.filter(r => r.kind === 'D'))}${section('용어', own.filter(r => r.kind === 'W'))}
    ${section('상위 폴더 기록 <small>이 프로젝트에도 적용</small>', records.filter(r => r.inherited), false)}`;
}

// 오른쪽에서 밀려 나오는 설정창. flow: 커맨드 패널 설정, map: 모듈 패널 설정, global: 전역 설정, records: 아카이브 보기
function drawerHTML() {
  if (ui.drawer === 'records') return recordsHTML(cur());
  if (ui.drawer === 'global') {
    return `<div class="ps-title">전역 설정<button class="x" data-drawer="global" title="닫기">×</button></div>
      <label class="ps-row"><span>테마</span><select id="theme-select">
        <option value="future-industry" ${ui.theme === 'future-industry' ? 'selected' : ''}>FutureIndustry</option>
        <option value="base" ${ui.theme === 'base' ? 'selected' : ''}>Base</option></select></label>
      <div class="ps-row muted"><span>사안 규약</span><code>docs/item-protocol.md</code></div>
      <div class="ps-row muted"><span>캡처 저장</span><code>data/captures/</code></div>`;
  }
  const font = k => `<div class="ps-row"><span>${FONT_KEYS[k]} 글자${k === 'map' ? ' <small>카드 너비도 함께 바뀐다</small>' : ''}</span>
    <span class="stepper"><button data-fs="${k}" data-delta="-1">−</button><b>${ui.fs[k]}</b><button data-fs="${k}" data-delta="1">+</button></span></div>`;
  const check = (key, on, label, sub) => `<label class="ps-row"><span>${label} <small>${sub}</small></span><input type="checkbox" data-pref="${key}" ${on ? 'checked' : ''}></label>`;
  if (ui.drawer === 'map') {
    return `<div class="ps-title">모듈 패널 설정<button class="x" data-drawer="map" title="닫기">×</button></div>${font('map')}
      <div class="ps-row"><span>미리보기 지연 <small>마우스를 올려 두고 임시 강조까지</small></span>
        <span class="stepper"><button data-peek="-0.1">−</button><b>${ui.peekDelay.toFixed(1)}초</b><button data-peek="0.1">+</button></span></div>
      ${check('vocab', ui.vocabFaint, 'l0 공용 모듈로 가는 선 옅게', '선택했을 때만 진하게 보인다')}
      ${check('blast', ui.showBlast, '이번 턴 영향 범위 표시', '이번 턴이 고친 모듈에 기대는 모듈을 옅게 칠한다')}
      ${check('remember', ui.rememberOpen, '펼친 중첩 모듈 기억', '다시 열어도 펼친 상태를 유지한다')}
      <div class="ps-row muted"><span>지도 출처</span><code>lnt map --json</code></div>`;
  }
  return `<div class="ps-title">커맨드 패널 설정<button class="x" data-drawer="flow" title="닫기">×</button></div>${font('cur')}${font('prev')}${font('head')}
    ${check('refs', ui.refs, '언급도 관련으로 보기', '본문에서 #ID 로 언급한 사안도 함께 밝힌다')}`;
}

function renderDrawer() {
  const d = $('#drawer');
  if (ui.drawer) d.innerHTML = drawerHTML();
  d.classList.toggle('open', !!ui.drawer);
  d.classList.toggle('wide', ui.drawer === 'records');
  document.querySelectorAll('[data-drawer]').forEach(b => b.classList.toggle('on', b.dataset.drawer === ui.drawer));
}

function renderTerm(s) {
  if (LIVE) { showTerm(s); return; }
  $('#term-title').textContent = `${s.project} · ${s.agent}`;
  const parts = s.turns.flatMap(t => [`<span class="prompt">&gt; ${esc(t.prompt)}</span>`, esc(t.text)]);
  s.log.forEach(m => parts.push(`<span class="prompt">&gt; ${esc(m)}</span>`));
  $('#term-body').innerHTML = parts.join('\n\n') || '<span class="prompt">&gt; </span>';
}

// 기둥마다 따로 세로 스크롤한다. 다시 그릴 때 기둥별 위치와 정렬용 여백을 되살린다
function colScrolls() {
  return Object.fromEntries([...document.querySelectorAll('.col[data-col]')].map(c => {
    const box = c.querySelector('.col-items, .col-body');
    return [c.dataset.col, { top: box.scrollTop, padTop: box.style.paddingTop, padBottom: box.style.paddingBottom }];
  }));
}

function render({ keepScroll = true } = {}) {
  const s = cur();
  const prev = $('#flow');
  const scroll = keepScroll && prev ? prev.scrollLeft : null;
  const cols = keepScroll ? colScrolls() : {};
  document.documentElement.dataset.theme = ui.theme;
  if (ui.cur) savePref('overseer.tab', ui.cur);
  renderTabs();
  $('#main').innerHTML = renderMain(s);
  $('#term').hidden = !ui.term;
  $('#toggle-term').classList.toggle('on', ui.term);
  if (s || LIVE) renderTerm(s);
  renderDrawer();

  const flow = $('#flow');
  // 지난 턴 흐름은 오른쪽이 기준점이라 scrollLeft 0 이 오른쪽 끝(최근)이다
  if (flow) flow.scrollLeft = scroll ?? 0;
  if (MP.tab !== ui.cur) renderModules();
  document.querySelectorAll('.col[data-col]').forEach(c => {
    const saved = cols[c.dataset.col];
    if (!saved) return;
    const box = c.querySelector('.col-items, .col-body');
    box.style.paddingTop = saved.padTop;
    box.style.paddingBottom = saved.padBottom;
    box.scrollTop = saved.top;
  });
  showFocus();
}

// 선택 표시. 화면은 스크롤하지 않고, 이어진 카드만 밝히고 나머지는 흐린다
function showFocus() {
  light(ui.active);
  align(ui.active);
}

function light(id) {
  const main = $('#main');
  main.querySelectorAll('.lit, .active').forEach(el => el.classList.remove('lit', 'active'));
  main.classList.toggle('dim', !!id);
  mpRepaint();
  if (!id) return;
  const related = relatedOf(cur(), id);
  main.querySelectorAll('.card[data-id]').forEach(el => { if (related.has(el.dataset.id)) el.classList.add('lit'); });
  main.querySelectorAll(`.card[data-id="${CSS.escape(id)}"]`).forEach(el => el.classList.add('active'));
}

// 다른 턴 기둥에서 이어진 카드를 순서대로 한데 모으고, 그 첫 카드를 선택한 카드 높이에 맞춘다
// 선택한 카드의 기둥과 가로 위치는 건드리지 않는다
function align(id) {
  const boxes = [...document.querySelectorAll('#flow .col-items')];
  const active = cardEl(id);
  const home = active?.closest('.col-items');
  // 선택한 카드의 기둥은 여백도 두어야 카드가 제자리에 있다
  boxes.forEach(box => {
    [...box.children].forEach(c => { c.style.order = ''; });
    if (box !== home) box.style.paddingTop = box.style.paddingBottom = '';
  });
  if (!active) return;
  const related = relatedOf(cur(), id);
  const top = active.getBoundingClientRect().top;
  for (const box of boxes) {
    if (box === home) continue;
    const cards = [...box.children];
    const rel = cards.filter(c => related.has(c.dataset.id));
    if (!rel.length) continue;
    // 첫 관련 카드 자리에 관련 카드를 모은다. 그 앞뒤의 다른 카드 순서는 그대로
    const first = cards.indexOf(rel[0]);
    const rest = cards.filter(c => !rel.includes(c));
    [...rest.slice(0, first), ...rel, ...rest.slice(first)].forEach((c, i) => { c.style.order = i; });

    const view = box.getBoundingClientRect();
    const y = Math.max(top, view.top) - view.top;
    let want = rel[0].getBoundingClientRect().top - view.top + box.scrollTop - y;
    // 위로 모자라면 위 여백을, 아래로 모자라면 아래 여백을 늘려 맞춘다
    if (want < 0) { box.style.paddingTop = `${-want}px`; want = 0; }
    padFor(box, want);
    box.scrollTop = want;
  }
}

// 기둥을 want 까지 스크롤할 수 있게 아래 여백을 늘린다
// 카드가 적어 기둥이 넘치지 않을 때도 맞도록 여백을 카드 끝에서부터 잰다
function padFor(box, want) {
  const view = box.getBoundingClientRect();
  const end = Math.max(...[...box.children].map(c => c.getBoundingClientRect().bottom)) - view.top + box.scrollTop;
  const need = want + box.clientHeight - end;
  if (need > parseFloat(getComputedStyle(box).paddingBottom)) box.style.paddingBottom = `${need}px`;
}

function flash(el) {
  if (!el) return;
  el.classList.remove('flash');
  void el.offsetWidth;
  el.classList.add('flash');
}

async function send() {
  const s = cur();
  if (!s || !canSend(s)) return;
  const msg = compose(s);
  const ready = allItems(s).filter(i => isReady(s, i));
  if (LIVE) {
    const decisions = ready.map(i => ({ id: i.id, action: s.decisions[i.id].action, note: s.decisions[i.id].note.trim() }));
    if (summaryNote(s)) decisions.push({ id: `sum-${s.turns.length}`, action: 'feedback', note: summaryNote(s) });
    const res = await api(`/api/tabs/${s.id}/send`, 'POST', { message: msg, decisions });
    if (!res) return;
  }
  ready.forEach(i => { s.sent[i.id] = { ...s.decisions[i.id] }; ui.open.delete(i.id); });
  if (summaryNote(s)) { s.summarySent[s.turns.length] = summaryNote(s); s.summary[s.turns.length] = ''; }
  s.log.push(msg);
  s.running = msg;
  s.extra = '';
  s.wrapup = false;
  s.status = 'working';
  ui.extraOpen = false;
  ui.unveil.clear();
  mapClear(s);
  saveDraft(s);
  render();
  renderModules();
}

// 결정 저장 후 /clear: 고른 처리는 패널에만 남기고 에이전트에게 보내지 않는다. 곧 지울 맥락이라 보낼 이유가 없다
// 미처리 사안은 보류로 넘긴다. 추가 지시와 모듈 패널에서 한 일은 지우지 않고 남겨 새 세션에 보낼 수 있게 한다
async function clearContext() {
  const s = cur();
  if (!s || !s.alive || s.starting || s.running) return;
  const ready = allItems(s).filter(i => isReady(s, i));
  const todo = roundItems(s).filter(i => !isReady(s, i));
  const keep = todo.filter(i => i.tag).length;
  const msg = ['에이전트 맥락을 지운다(/clear). 처리한 결정은 패널에만 저장하고 에이전트에게 보내지 않는다.'];
  if (todo.length) msg.push(`미처리 ${todo.length}건${keep ? `(보존 사안 ${keep}건)` : ''}은 보류로 넘긴다.`);
  if (!confirm(msg.join('\n'))) return;
  if (LIVE) {
    const decisions = ready.map(i => ({ id: i.id, action: s.decisions[i.id].action, note: s.decisions[i.id].note.trim() }));
    if (summaryNote(s)) decisions.push({ id: `sum-${s.turns.length}`, action: 'feedback', note: summaryNote(s) });
    const res = await api(`/api/tabs/${s.id}/clear`, 'POST', { decisions });
    if (!res) return;
  }
  ready.forEach(i => { s.sent[i.id] = { ...s.decisions[i.id] }; ui.open.delete(i.id); });
  todo.forEach(i => { s.sent[i.id] = { action: 'hold', note: '' }; ui.open.delete(i.id); });
  ui.unveil.clear();
  if (summaryNote(s)) { s.summarySent[s.turns.length] = summaryNote(s); s.summary[s.turns.length] = ''; }
  s.wrapup = false;
  saveDraft(s);
  render();
}

// 새로 선택한 카드를 그 기둥 머리의 가로선 바로 아래로 옮긴다. 그 기둥만 스크롤한다
// 끝 쪽 카드라 더 내려갈 데가 없으면 아래 여백을 늘린다. 다른 기둥은 스크롤 이벤트로 따라온다
function raise(id) {
  const card = cardEl(id);
  if (!card) return;
  const box = card.closest('.col-items');
  const over = card.getBoundingClientRect().top - box.getBoundingClientRect().top;
  if (!over) return;
  padFor(box, box.scrollTop + over);
  box.scrollBy({ top: over, behavior: 'smooth' });
}

// 출처 버튼: 화면은 움직이지 않는다. 출처 카드를 펼쳐 깜빡인다. 선택 정렬로 출처가 같은 높이에 온다
function jumpTo(id) {
  reveal(cur(), id);
  ui.open.add(id);
  // 커맨드 패널에 없는 사안이면 지난 턴을 펼친다
  if (!document.getElementById(`c-${id}`)) ui.past = true;
  render();
  flash(cardEl(id));
}

// 입력 중에는 전체를 다시 그리지 않고 바뀐 부분만 고친다
function refreshLive(s, id) {
  if (id) {
    const item = findItem(s, id);
    const need = needsNote(item, s.decisions[id].action);
    document.querySelectorAll(`#main .card[data-id="${CSS.escape(id)}"]`).forEach(el => {
      el.className = el.className.replace(/st-\w+/, `st-${statusOf(s, item)}`);
      const hint = el.querySelector('[data-hint]');
      if (hint) hint.textContent = need && !s.decisions[id].note.trim() ? '내용을 적어야 전송된다' : '';
    });
  }
  if ($('#btn-send')) {
    $('#btn-send').disabled = !canSend(s);
    $('#btn-send').innerHTML = sendLabel(s);
  }
  renderTabs();
}

function applyFonts() {
  for (const [k, v] of Object.entries(ui.fs)) document.documentElement.style.setProperty(`--fs-${k}`, `${v}px`);
  requestAnimationFrame(() => { showFocus(); mpRepaint(); });
}

document.addEventListener('click', e => {
  if (ui.drawer && !e.target.closest('#drawer, [data-drawer]')) { ui.drawer = null; renderDrawer(); }
  if (e.target.closest('[data-unpick]')) { unpick(); return; }
  // 카드를 누르면 선택, 흐름의 빈 곳을 누르면 해제
  // 보류 막 위의 꺼내기·닫기는 카드를 고르지 않는다. 고르면 그 카드를 맨 위로 올리느라 남은 보류 카드가 밀려난다
  const picked = !e.target.closest('.veil') && e.target.closest('.card[data-id]');
  // 이미 선택된 카드 안을 누를 때는 옮기지 않는다. 누른 자리가 손 밑에서 달아나지 않게
  const fresh = picked && picked.dataset.id !== ui.active;
  if (picked) { ui.active = picked.dataset.id; showFocus(); }
  else if (e.target.closest('#flow, .cmd-pane .col-items') && !e.target.closest('.card')) { ui.active = null; showFocus(); }
  act(e);
  // 버튼 처리로 다시 그려진 뒤에 옮긴다. 먼저 하면 다시 그리면서 스크롤이 끊긴다
  if (fresh) raise(ui.active);
});

function unpick() {
  ui.active = null;
  showFocus();
}

// 키보드
// Tab / Shift+Tab: 세션 탭 이동, Ctrl+Shift+Enter: 승인 및 작업 (입력 중에도 동작)
// 위아래 방향키: 같은 기둥 안 카드 이동, Home: 현재 턴 종합 의견, 숫자키: 선택한 카드의 처리 버튼
// 그 밖의 글자 키: 선택한 카드의 입력창에 바로 입력 시작
// Enter: 선택한 카드의 첫 번째 처리를 고르고 다음 카드로 (의견이 필요한 처리면 입력칸으로)
// Ctrl+Enter: 카드 입력칸에서 입력을 마치고 다음 카드로
// Esc: 입력창에서 벗어나기, 그다음 선택 해제
document.addEventListener('keydown', e => {
  // 터미널 창 안의 키는 전부 claude 로 간다. Tab, Esc 도 거기서 쓰인다
  if (e.target.closest?.('#term, dialog')) return;
  const typing = e.target.closest?.('textarea, input, select');
  if (e.key === 'Tab' && !e.ctrlKey && !e.altKey) {
    e.preventDefault();
    switchTab(e.shiftKey ? -1 : 1);
    return;
  }
  if (e.key === 'Enter' && e.ctrlKey && e.shiftKey) {
    e.preventDefault();
    send();
    return;
  }
  // 카드 입력칸에서 Ctrl+Enter: 입력을 마치고 같은 기둥의 다음 카드로
  if (e.key === 'Enter' && e.ctrlKey && !e.shiftKey && !e.altKey && typing?.closest('.card')) {
    e.preventDefault();
    typing.blur();
    step(1);
    return;
  }
  if (e.key === 'Escape') {
    if (typing) { e.target.blur(); return; }
    if (ui.drawer) { ui.drawer = null; renderDrawer(); return; }
    if (mpEsc()) return;
    if (ui.past) { ui.past = false; render(); return; }
    if (ui.active) unpick();
    return;
  }
  if (typing || e.ctrlKey || e.altKey || e.metaKey) return;
  if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
    e.preventDefault();
    step(e.key === 'ArrowDown' ? 1 : -1);
  } else if (e.key === 'Home') {
    e.preventDefault();
    // 현재 턴의 맨 앞 카드로. 종합 의견이 있으면 그것, 없으면 첫 사안
    ui.active = null;
    step(1);
  } else if (e.key === 'Enter' && ui.active) {
    // 첫 번째 처리(보고 확인, 제안 승인)를 고르고 다음 카드로. 의견이 필요한 처리(질문 답변)면 입력칸으로
    e.preventDefault();
    const s = cur();
    const item = findItem(s, ui.active);
    if (item && editable(s, item.id)) {
      const [action, needNote] = actionsFor(item)[0];
      const d = s.decisions[item.id] ||= { action: '', note: '' };
      d.action = action;
      saveDraft(s);
      render();
      if (needNote && !d.note.trim()) {
        document.querySelector(`[data-note="${item.id}"]`)?.focus();
        return;
      }
    }
    step(1);
  } else if (/^[1-9]$/.test(e.key) && ui.active) {
    // 기본 동작을 막지 않으면 새로 열려 포커스를 받은 입력창에 숫자가 찍힌다
    e.preventDefault();
    cardEl(ui.active)?.querySelectorAll('.seg button')[Number(e.key) - 1]?.click();
    // 입력창에 붙잡지 않는다. 방향키로 바로 다음 카드로 갈 수 있고, 글자를 치면 그때 입력이 시작된다
    if (document.activeElement?.dataset?.note) document.activeElement.blur();
  } else if ((e.key.length === 1 || e.key === 'Process') && ui.active) {
    // 그 밖의 글자 키는 선택한 카드의 입력창으로 보낸다. 기본 동작을 막지 않아 누른 글자가 그대로 들어간다
    const note = cardEl(ui.active)?.querySelector('textarea');
    if (!note) return;
    note.focus();
    note.setSelectionRange(note.value.length, note.value.length);
  }
});

function switchTab(dir) {
  if (!sessions.length) return;
  const i = sessions.findIndex(s => s.id === ui.cur);
  ui.cur = sessions[(i + dir + sessions.length) % sessions.length].id;
  ui.active = null;
  render({ keepScroll: false });
}

// 선택한 카드에서 위아래로 한 칸. 선택이 없으면 현재 턴의 첫 카드부터
function step(dir) {
  const active = cardEl(ui.active);
  const box = active ? active.closest('.col-items') : document.querySelector('.col-cur .col-items');
  if (!box) return;
  // 보류 막이 씌워진 카드는 건너뛴다
  const cards = [...box.querySelectorAll(':scope > .card[data-id]:not(.held-card)')];
  const next = active ? cards[cards.indexOf(active) + dir] : cards[0];
  if (!next) return;
  ui.active = next.dataset.id;
  showFocus();
  raise(ui.active);
}

function act(e) {
  const t = e.target.closest('[data-unhold],[data-closeheld],[data-perm],[data-open-term],[data-close],[data-newtab],[data-resume],[data-tab],[data-jump],[data-act],[data-toggle],[data-prompt],[data-drawer],[data-fs],[data-peek],[data-oldturns],[data-past],[data-extra-toggle],#toggle-term,#btn-send,#btn-wrapup,#btn-clear');
  if (!t) return;
  const s = cur();
  if (t.dataset.unhold) { unhold(t.dataset.unhold); }
  else if (t.dataset.closeheld) { closeHeld(t.dataset.closeheld); }
  else if (t.dataset.perm) { decidePermission(t.dataset.rid, t.dataset.perm); }
  else if ('openTerm' in t.dataset) { ui.term = true; ui.autoTerm = null; render(); }
  else if (t.dataset.close) { closeTab(t.dataset.close); }
  else if ('newtab' in t.dataset) { if (LIVE) openTab(); }
  else if (t.dataset.resume) { resumeTab(t.dataset.resume); }
  else if (t.dataset.drawer) {
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
  else if (t.dataset.peek) {
    ui.peekDelay = Math.round(Math.min(2, Math.max(0.1, ui.peekDelay + Number(t.dataset.peek))) * 10) / 10;
    savePref('overseer.peek', String(ui.peekDelay));
    t.parentElement.querySelector('b').textContent = `${ui.peekDelay.toFixed(1)}초`;
  }
  else if ('past' in t.dataset) { ui.past = !ui.past; render(); }
  else if ('extraToggle' in t.dataset) {
    ui.extraOpen = !ui.extraOpen;
    render();
    if (ui.extraOpen) document.querySelector('[data-extra]')?.focus();
  }
  else if (t.dataset.tab) { ui.cur = t.dataset.tab; ui.active = null; ui.mpPin = null; ui.past = false; ui.unveil.clear(); render({ keepScroll: false }); }
  else if (t.dataset.jump) { e.stopPropagation(); jumpTo(t.dataset.jump); }
  else if ('oldturns' in t.dataset) { ui.showOld.has(s.id) ? ui.showOld.delete(s.id) : ui.showOld.add(s.id); render(); }
  else if (t.dataset.prompt) {
    const n = Number(t.dataset.prompt);
    ui.promptOpen.has(n) ? ui.promptOpen.delete(n) : ui.promptOpen.add(n);
    render();
  }
  else if (t.dataset.act) {
    const d = s.decisions[t.dataset.id] ||= { action: '', note: '' };
    d.action = d.action === t.dataset.act ? '' : t.dataset.act;
    saveDraft(s);
    render();
    document.querySelector(`[data-note="${t.dataset.id}"]`)?.focus();
  }
  else if (t.dataset.toggle) {
    const id = t.dataset.toggle;
    ui.open.has(id) ? ui.open.delete(id) : ui.open.add(id);
    document.getElementById(`c-${id}`).classList.toggle('open');
    showFocus();
  }
  else if (t.id === 'toggle-term') { ui.term = !ui.term; ui.autoTerm = null; render(); }
  else if (t.id === 'btn-send') { send(); }
  else if (t.id === 'btn-wrapup') { s.wrapup = !s.wrapup; saveDraft(s); render(); }
  else if (t.id === 'btn-clear') { clearContext(); }
}

document.addEventListener('input', e => {
  if ('permNote' in e.target.dataset) { ui.permNote = e.target.value; return; }
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
  } else {
    return;
  }
  saveDraft(s);
});

document.addEventListener('change', e => {
  const map = { vocab: ['vocabFaint', 'overseer.vocab'], blast: ['showBlast', 'overseer.blast'], remember: ['rememberOpen', 'overseer.mpremember'] }[e.target.dataset.pref];
  if (map) {
    ui[map[0]] = e.target.checked;
    savePref(map[1], e.target.checked ? '1' : '0');
    mpRepaint();
  } else if (e.target.dataset.pref === 'refs') {
    ui.refs = e.target.checked;
    savePref('overseer.refs', ui.refs ? '1' : '0');
    showFocus();
  } else if (e.target.id === 'theme-select') {
    ui.theme = e.target.value;
    savePref('overseer.theme', ui.theme);
    document.documentElement.dataset.theme = ui.theme;
    requestAnimationFrame(showFocus);
  }
});

// 선택한 카드의 기둥을 스크롤하면 다른 기둥의 관련 카드도 높이를 따라온다. scroll 은 버블링이 없어 캡처로 받는다
let alignFrame = 0;
document.addEventListener('scroll', e => {
  const active = ui.active && document.getElementById(`c-${ui.active}`);
  if (!active || e.target !== active.closest('.col-items') || alignFrame) return;
  alignFrame = requestAnimationFrame(() => { alignFrame = 0; align(ui.active); });
}, true);

// URL 해시로 초기 화면 지정: #term, #drawer
if (location.hash.includes('term')) ui.term = true;
if (location.hash.includes('drawer')) ui.drawer = 'flow';

// 실제 모드 ---------------------------------------------------------------

// https 로 열면(원격 접속) WebSocket 도 암호화한다
const WS = location.protocol === 'https:' ? 'wss:' : 'ws:';

async function api(path, method = 'GET', body) {
  try {
    const res = await fetch(path, { method, headers: { 'Content-Type': 'application/json' }, body: body && JSON.stringify(body) });
    // 서버가 모르는 경로면 aiohttp 가 `405: Method Not Allowed` 같은 글로 답한다. 서버를 다시 띄우지 않았을 때 생긴다
    const text = await res.text();
    let data = null;
    try { data = JSON.parse(text); } catch { /* 아래에서 글 그대로 알린다 */ }
    if (!res.ok || !data) {
      alert(data?.error || `요청 실패: ${text.trim() || res.status}${res.status === 404 || res.status === 405 ? '\n서버가 이 기능을 모른다. 서버를 다시 띄웠는지 확인' : ''}`);
      return null;
    }
    return data;
  } catch (err) {
    alert(`서버에 닿지 않는다: ${err.message}`);
    return null;
  }
}

// 작성 중인 처리는 잠시 모았다가 서버에 남긴다. 패널을 다시 켜도 이어서 쓴다
const draftTimers = {};
function saveDraft(s) {
  if (!LIVE || !s) return;
  clearTimeout(draftTimers[s.id]);
  draftTimers[s.id] = setTimeout(() => {
    fetch(`/api/tabs/${s.id}/draft`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decisions: s.decisions, summary: s.summary, extra: s.extra, wrapup: s.wrapup, map: s.map }),
    }).catch(() => {});
  }, 400);
}

// 처음 보는 사안 중 미처리인 것만 펼친다. 사용자가 접은 카드는 다시 펴지 않는다
const seen = new Set();
function openNew(s) {
  allItems(s).forEach(i => {
    const key = `${s.id}/${i.id}`;
    if (seen.has(key)) return;
    seen.add(key);
    if (statusOf(s, i) === 'todo') ui.open.add(i.id);
  });
}

function termSize() {
  const t = ui.cur && terms[ui.cur];
  return t ? { rows: t.term.rows, cols: t.term.cols } : { rows: 40, cols: 120 };
}

// 새 탭 설정 창. 드라이브마다 루트 Projects 폴더 안의 프로젝트를 보여 준다
// 입력은 검색어. 목록에 없는 이름이면 새 폴더 만들기, 드라이브 문자로 시작하면 그 경로를 바로 연다
// 권한 확인 생략은 열 때마다 켠 상태로 시작한다
const picker = { roots: [], defaultRoot: '', options: [], sel: 0, createRoot: '' };
const isPath = q => /^[a-zA-Z]:[\\/]/.test(q) || q.startsWith('\\\\');

function pickerOptions(q) {
  const key = q.trim().toLowerCase();
  if (isPath(q.trim())) return [{ type: 'path', cwd: q.trim() }];
  const opened = new Set(sessions.map(s => (s.cwd || '').toLowerCase()));
  const dirs = picker.roots.flatMap(r => r.dirs.map(d => ({ type: 'dir', cwd: d.path, name: d.name, group: d.group, root: r.root, opened: opened.has(d.path.toLowerCase()) })));
  // 묶음 폴더 안의 프로젝트는 묶음 이름으로도 찾는다
  const hits = key ? dirs.filter(d => `${d.group || ''}/${d.name}`.toLowerCase().includes(key)) : dirs;
  // 정확히 같은 이름이 만들 위치에 이미 있으면 새로 만들기는 보이지 않는다
  const exists = dirs.some(d => !d.group && d.root === picker.createRoot && d.name.toLowerCase() === key);
  return key && !exists ? [...hits, { type: 'create', name: q.trim() }] : hits;
}

function renderPicker() {
  const q = $('#newtab [name=q]').value;
  picker.options = pickerOptions(q);
  picker.sel = Math.min(picker.sel, Math.max(0, picker.options.length - 1));
  let lastRoot = null;
  const rows = picker.options.map((o, i) => {
    const on = i === picker.sel ? 'on' : '';
    if (o.type === 'path') return `<div class="nt-opt ${on}" data-opt="${i}">경로로 열기 <code>${esc(o.cwd)}</code></div>`;
    if (o.type === 'create') {
      const roots = picker.roots.length ? picker.roots.map(r => r.root) : [picker.defaultRoot];
      const select = roots.length > 1
        ? `<select data-create-root>${roots.map(r => `<option ${r === picker.createRoot ? 'selected' : ''}>${esc(r)}</option>`).join('')}</select>`
        : `<code>${esc(roots[0])}</code>`;
      return `<div class="nt-opt create ${on}" data-opt="${i}">+ 새 폴더 만들기 ${select}<code>\\${esc(o.name)}</code></div>`;
    }
    const head = o.root !== lastRoot ? `<div class="nt-root">${esc(o.root)}</div>` : '';
    lastRoot = o.root;
    const name = o.group ? `<span class="nt-group">${esc(o.group)} /</span>${esc(o.name)}` : esc(o.name);
    return `${head}<div class="nt-opt ${o.group ? 'nested' : ''} ${on}" data-opt="${i}">${name}${o.opened ? '<small>열려 있음</small>' : ''}</div>`;
  });
  const empty = picker.roots.length ? '맞는 폴더 없음' : `드라이브 루트에 Projects 폴더가 없다. 이름을 입력하면 ${esc(picker.defaultRoot)} 에 만든다`;
  $('#nt-list').innerHTML = rows.join('') || `<div class="nt-empty">${empty}</div>`;
  $('#nt-list .nt-opt.on')?.scrollIntoView({ block: 'nearest' });
}

async function askNewTab() {
  const data = await api('/api/projects');
  if (!data) return null;
  picker.roots = data.roots;
  picker.defaultRoot = data.default_root;
  picker.createRoot = data.default_root;
  picker.sel = 0;
  const dlg = $('#newtab');
  const form = dlg.querySelector('form');
  form.q.value = '';
  form.skip.checked = true;
  renderPicker();
  dlg.showModal();
  form.q.focus();
  return new Promise(resolve => {
    const finish = ok => {
      const o = picker.options[picker.sel];
      dlg.close();
      if (!ok || !o) return resolve(null);
      const base = { skip_permissions: form.skip.checked };
      resolve(o.type === 'create' ? { ...base, create: { root: picker.createRoot, name: o.name } } : { ...base, cwd: o.cwd });
    };
    form.q.oninput = () => { picker.sel = 0; renderPicker(); };
    form.q.onkeydown = e => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        picker.sel = Math.max(0, Math.min(picker.options.length - 1, picker.sel + (e.key === 'ArrowDown' ? 1 : -1)));
        renderPicker();
      } else if (e.key === 'Enter' && !e.isComposing) {
        e.preventDefault();
        finish(true);
      }
    };
    form.onsubmit = e => e.preventDefault();
    $('#nt-list').onclick = e => {
      const row = e.target.closest('[data-opt]');
      if (!row || e.target.closest('select')) return;
      picker.sel = Number(row.dataset.opt);
      renderPicker();
      form.q.focus();
    };
    $('#nt-list').ondblclick = e => { if (e.target.closest('[data-opt]') && !e.target.closest('select')) finish(true); };
    $('#nt-list').onchange = e => { if (e.target.dataset.createRoot !== undefined) { picker.createRoot = e.target.value; renderPicker(); } };
    dlg.querySelector('[data-nt=open]').onclick = () => finish(true);
    dlg.querySelector('[data-nt=cancel]').onclick = () => finish(false);
    dlg.oncancel = e => { e.preventDefault(); finish(false); };
  });
}

async function openTab() {
  const opts = await askNewTab();
  if (!opts) return;
  const t = await api('/api/tabs', 'POST', { ...opts, ...termSize() });
  if (!t) return;
  upsert(t);
  ui.cur = t.id;
  ui.active = null;
  // 시작 확인 창은 터미널에서 처리한다. 정상으로 시작하면 접는다
  ui.term = true;
  ui.autoTerm = t.id;
  render({ keepScroll: false });
}

async function resumeTab(id) {
  const t = await api(`/api/tabs/${id}/resume`, 'POST', termSize());
  if (!t) return;
  upsert(t);
  ui.term = true;
  ui.autoTerm = t.id;
  render();
}

async function closeTab(id) {
  const s = sessions.find(x => x.id === id);
  if (s?.alive && !confirm(`${s.project} 세션을 끝내고 탭을 닫는다`)) return;
  if (await api(`/api/tabs/${id}`, 'DELETE')) removeTab(id);
}

function upsert(t) {
  const i = sessions.findIndex(s => s.id === t.id);
  const s = fromServer(t, i >= 0 ? sessions[i] : null);
  if (i >= 0) sessions[i] = s; else sessions.push(s);
  openNew(s);
  return s;
}

function removeTab(id) {
  sessions = sessions.filter(s => s.id !== id);
  terms[id]?.dispose();
  delete terms[id];
  if (ui.cur === id) { ui.cur = sessions[0]?.id ?? null; ui.active = null; ui.mpPin = null; }
  render({ keepScroll: false });
}

// 다시 그려도 입력하던 칸과 커서 자리를 되살린다
function renderKeepFocus() {
  const f = document.activeElement;
  const sel = f?.dataset?.note ? `[data-note="${f.dataset.note}"]`
    : f?.dataset?.summary ? `[data-summary="${f.dataset.summary}"]`
    : f && 'extra' in (f.dataset || {}) ? '[data-extra]'
    : f && 'permNote' in (f.dataset || {}) ? '[data-perm-note]' : null;
  const range = sel && [f.selectionStart, f.selectionEnd];
  render();
  const el = sel && document.querySelector(sel);
  if (el) { el.focus(); el.setSelectionRange(...range); }
}

// 탭 상태 알림. 끊기면 다시 붙는다
function listen() {
  const ws = new WebSocket(`${WS}//${location.host}/ws/events`);
  ws.onmessage = e => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'closed') { if (sessions.some(s => s.id === msg.id)) removeTab(msg.id); return; }
    if (msg.type === 'modules') { onModulesEvent(msg); return; }
    if (msg.type !== 'tab') return;
    const was = sessions.find(s => s.id === msg.tab.id)?.starting;
    upsert(msg.tab);
    autoFold(msg.tab, was);
    if (!ui.cur) ui.cur = msg.tab.id;
    if (msg.tab.id === ui.cur) renderKeepFocus(); else renderTabs();
  };
  ws.onclose = () => setTimeout(listen, 1000);
}

// 띄우며 연 터미널 창은 시작 훅이 오면 접는다. 시작이 막혔으면(확인 창, 실패로 꺼짐) 펼친 채로 두어 이유를 보게 한다
function autoFold(t, was) {
  if (ui.autoTerm !== t.id || !was || t.starting) return;
  ui.autoTerm = null;
  if (t.alive && ui.cur === t.id) ui.term = false;
}

// 터미널 창: 탭마다 xterm 하나. 처음 볼 때 만들고 WebSocket 으로 PTY 에 붙인다
const terms = {};
function makeTerm(s) {
  const host = document.createElement('div');
  host.className = 'xterm-host';
  $('#term-body').appendChild(host);
  const term = new Terminal({
    fontFamily: '"Cascadia Code", Consolas, monospace', fontSize: 13, scrollback: 5000,
    theme: { background: getComputedStyle(document.documentElement).getPropertyValue('--term-bg').trim() || '#05080c' },
  });
  const fit = new FitAddon.FitAddon();
  term.loadAddon(fit);
  term.open(host);
  const ws = new WebSocket(`${WS}//${location.host}/ws/term/${s.id}`);
  const sendJSON = obj => { if (ws.readyState === 1) ws.send(JSON.stringify(obj)); };
  ws.onmessage = e => term.write(e.data);
  ws.onopen = () => sendJSON({ type: 'resize', rows: term.rows, cols: term.cols });
  term.onData(data => sendJSON({ type: 'input', data }));
  term.onResize(({ rows, cols }) => sendJSON({ type: 'resize', rows, cols }));
  return { host, term, fit, ws, dispose() { ws.onclose = null; ws.close(); term.dispose(); host.remove(); } };
}

function showTerm(s) {
  $('#term-title').textContent = s ? `${s.project} · ${s.agent}` : '';
  $('#term-title').title = s?.cwd || '';
  $('.term-note').textContent = '키 입력은 그대로 claude 로 간다';
  $('#term-body').classList.add('live');
  Object.entries(terms).forEach(([id, t]) => { t.host.hidden = !s || id !== s.id; });
  if (!s || !ui.term) { ui.termShown = null; return; }
  const t = terms[s.id] ||= makeTerm(s);
  // 처음 보일 때만 터미널로 입력을 옮긴다. 다시 그릴 때마다 옮기면 카드 입력칸에서 포커스를 빼앗는다
  const fresh = ui.termShown !== s.id;
  ui.termShown = s.id;
  requestAnimationFrame(() => { t.fit.fit(); if (fresh) t.term.focus(); });
}

window.addEventListener('resize', () => {
  const t = ui.cur && terms[ui.cur];
  if (t && ui.term) t.fit.fit();
});

async function boot() {
  try {
    const res = await fetch('/api/tabs');
    if (res.ok) {
      LIVE = true;
      (await res.json()).forEach(upsert);
    }
  } catch { /* 목업 서버. API 가 없다 */ }
  if (!LIVE) {
    sessions = mockSessions();
    // 처음엔 미처리 사안만 펼쳐 둔다
    sessions.forEach(s => allItems(s).forEach(i => { if (statusOf(s, i) === 'todo') ui.open.add(i.id); }));
  } else {
    document.querySelector('.mock-tag').hidden = true;
    listen();
  }
  // 새로고침해도 보던 탭으로 돌아온다
  const last = pref('overseer.tab', '');
  ui.cur = sessions.some(s => s.id === last) ? last : sessions[0]?.id ?? null;
  applyFonts();
  render({ keepScroll: false });
  document.fonts?.ready.then(showFocus);
}
boot();
