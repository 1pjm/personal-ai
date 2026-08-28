/* 출원 안내 화면 — 특허를 모르는 사람이 여기만 보고 따라가도록 짠다.
   마당마다 (1) 무엇인지 (2) 무엇을 누르는지 (3) 지금 어떤 상태인지 를 함께 보인다. */

const $ = i => document.getElementById(i);
const 안전 = s => String(s ?? '').replace(/[&<>"]/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const 원 = n => Number(n || 0).toLocaleString('ko-KR') + '원';
const 아이콘 = n => `<svg class="i" aria-hidden="true"><use href="#i-${n}"/></svg>`;

let 건들 = [], 고른 = null, 보드 = '', 열쇠있음 = false, 현재 = 0;

const 마당들 = [
  ['어느 특허를 낼까요', '낼 것을 하나 고릅니다'],
  ['준비물 갖추기', '처음 한 번만 하면 되는 등록 세 가지'],
  ['원고 검사', '관청이 문제 삼을 곳을 미리 찾습니다'],
  ['서류 만들기', '관청에 낼 파일을 자동으로 만듭니다'],
  ['비용 확인', '얼마를 내야 하는지 셈해 봅니다'],
  ['특허로에 내기', '실제로 내는 차례입니다'],
  ['낸 뒤 진행 상황', '출원번호로 지금 어디까지 갔는지 봅니다'],
];

/* ── 뼈대 ─────────────────────────────────────────── */
$('steps').innerHTML = 마당들.map(([이름, 풀이], n) => `
  <details class="step" id="s${n}"${n === 0 ? ' open' : ''}>
    <summary onclick="펼침(${n})">
      <span class="no" aria-hidden="true">${n}</span>
      <span class="ttl">${안전(이름)}<small>${안전(풀이)}</small></span>
      <span class="pill" id="t${n}">아직</span>
    </summary>
    <div class="body" id="b${n}"></div>
  </details>`).join('');

$('rail').innerHTML = 마당들.map(([이름], n) =>
  `<button id="nav_${n}" onclick="가마당(${n})">
     <span class="n">${n}</span>${안전(이름)}</button>`).join('');

/* ── 오감 ─────────────────────────────────────────── */
async function api(길, 몸) {
  const r = await fetch(길, 몸 ? {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(몸)
  } : undefined);
  return r.json();
}
function 표(칸) { return '<div class="tw"><table>' + 칸 + '</table></div>'; }
function 알림(갈, 제, 풀) {
  const 그림 = { ok: 'ok', bad: 'stop', warn: 'warn' }[갈];
  return `<div class="note ${갈}">${아이콘(그림)}<div><b>${제}</b>${풀 ? `<p>${풀}</p>` : ''}</div></div>`;
}
function 다음단추(n, 글) {
  return `<div class="next"><button class="p" onclick="가마당(${n})">
    ${안전(글)} ${아이콘('next')}</button></div>`;
}

/* 마당 상태를 한 곳에서 바꾼다. 레일·알약·동그라미가 함께 움직인다 */
function 마당(n, 상태, 꼬리) {
  const e = $('s' + n), r = $('nav_' + n);
  if (상태) { e.dataset.s = 상태; r.dataset.s = 상태; }
  else { delete e.dataset.s; delete r.dataset.s; }
  const 그림 = 상태 === 'done' ? 'ok' : 상태 === 'stop' ? 'stop' : '';
  $('t' + n).innerHTML = (그림 ? 아이콘(그림) : '') + 안전(꼬리);
}

function 펼침(n) { 현재 = n; 레일칠(); }
function 레일칠() {
  마당들.forEach((_, n) => $('nav_' + n).setAttribute(
    'aria-current', n === 현재 ? 'step' : 'false'));
}
function 가마당(n) {
  현재 = n; 레일칠();
  const e = $('s' + n);
  e.open = true;
  window.scrollTo({
    top: e.getBoundingClientRect().top + window.scrollY
      - document.querySelector('header').offsetHeight - 12
  });
  띠();
}
function 다음마당() { 가마당(Math.min(현재 + 1, 마당들.length - 1)); }

/* 요약 — 넓으면 오른쪽에 서고 좁으면 아래에 붙는다 */
function 띠() {
  const c = 건들[고른], e = $('요약');
  if (!c) { e.hidden = true; 높이재기(); return; }
  const 남 = 날수(c.마감);
  $('요약속').innerHTML =
    `<div><dt>고른 특허</dt><dd>${안전(c.이름)}</dd></div>
     <div><dt>낼 돈</dt><dd>${원(c.수수료.실납부)}</dd></div>
     ${c.마감 ? `<div><dt>마감</dt><dd>${안전(c.마감)}${남 !== null ? ` · D-${남}` : ''}</dd></div>` : ''}`;
  const 끝 = 현재 >= 마당들.length - 1;
  $('요약다음').innerHTML = (끝 ? '처음으로' : '다음') + ' ' + 아이콘('next');
  $('요약다음').onclick = () => 가마당(끝 ? 0 : 현재 + 1);
  e.hidden = false;
  높이재기();
}

/* 좁은 창에서 아래에 붙을 때, 그 높이만큼 본문 아래를 띄운다.
   띄우지 아니하면 마지막 줄이 띠에 가린다 */
function 높이재기() {
  const e = $('요약'), h = document.querySelector('header');
  document.documentElement.style.setProperty('--hdh', (h.offsetHeight + 16) + 'px');
  document.documentElement.style.setProperty('--sidh',
    (e.hidden ? 40 : e.offsetHeight + 24) + 'px');
}
addEventListener('resize', 높이재기);

function 요약접기() {
  const e = $('요약'), 접힘 = e.classList.toggle('접힘');
  $('접기').setAttribute('aria-expanded', String(!접힘));
  $('접기').querySelector('.ㄱ').textContent = 접힘 ? '보이기' : '숨기기';
  try { localStorage.setItem('요약접힘', 접힘 ? '1' : ''); } catch (e) { }
  높이재기();
}
try {
  if (localStorage.getItem('요약접힘')) 요약접기();
} catch (e) { }

function 날수(iso) {
  if (!iso) return null;
  const d = new Date(iso + 'T00:00:00');
  if (isNaN(d)) return null;
  return Math.round((d - new Date(new Date().toDateString())) / 86400000);
}

/* ── 0. 어느 특허를 낼까요 ─────────────────────────── */
function 그리기0(r) {
  보드 = r.보드 !== undefined ? (r.보드 || '') : 보드;
  $('보드길').hidden = false;   // 주소는 누를 때 받는다. 미리 없어도 보인다
  if (r.열쇠 !== undefined) 열쇠있음 = r.열쇠;
  건들 = r.건들 || []; 고른 = null;
  const 최근 = (r.최근 || []).filter(x => x !== r.폴더);

  let h = '<p class="hint">특허 하나가 폴더 하나입니다. 원고가 든 폴더를 고르면 '
    + '그 안의 특허를 모두 찾아 보여 줍니다.</p>'
    + '<label for="dir">원고가 든 폴더</label>'
    + '<div class="row" style="margin-bottom:16px">'
    + `<input type="text" id="dir" value="${안전(r.폴더 || '')}"`
    + ' placeholder="예: C:\\문서\\내 특허" style="flex:1;min-width:220px">'
    + `<button onclick="찾기()">${아이콘('folder')} 찾아보기</button>`
    + '<button class="p" onclick="불러오기()">불러오기</button></div>';
  if (최근.length) {
    h += '<p class="hint" style="margin-bottom:6px">전에 열어 본 폴더</p>'
      + '<div class="row" style="margin-bottom:16px">'
      + 최근.map(x => `<button class="sm" title="${안전(x)}" onclick="가기(this.title)">
          ${아이콘('folder')} ${안전(x.split(/[\\/]/).pop())}</button>`).join('')
      + '</div>';
  }
  h += '<div class="cases" id="cases"></div>';
  $('b0').innerHTML = h;

  $('cases').innerHTML = 건들.length ? 건들.map((c, i) => `
    <button class="case" id="c${i}" aria-pressed="false" onclick="고르기(${i})">
      <b>${안전(c.이름)}</b>
      <span>${안전(c.제목).slice(0, 52)}…</span>
      <span class="meta">청구항 ${c.청구항}항 · 도면 ${c.도면}매${c.마감 ? ' · 마감 ' + 안전(c.마감) : ''}</span>
    </button>`).join('')
    : `<div class="empty">${안전(r.잘못 || '이 폴더에는 특허 원고가 없습니다.')}<br>
       patent_config.json 이 들어 있는 폴더를 고르세요. 몇 단계 아래에 있어도 찾아냅니다.</div>`;

  for (let n = 1; n < 마당들.length; n++) { $('s' + n).open = false; 마당(n, '', '아직'); $('b' + n).innerHTML = ''; }
  마당(0, 건들.length ? '' : 'stop', 건들.length ? `${건들.length}건 찾음` : '폴더를 고르세요');
  띠(); 레일칠();
}

async function 찾기() {
  const r = await api('/api/pick?dir=' + encodeURIComponent($('dir').value));
  if (r.폴더) { $('dir').value = r.폴더; 불러오기(); }
}
async function 가기(폴더) { $('dir').value = 폴더; 불러오기(); }
async function 불러오기() {
  $('cases').innerHTML = '<div class="empty"><span class="spin"></span>찾는 중</div>';
  그리기0(await api('/api/chdir', { 폴더: $('dir').value }));
}

function 고르기(i) {
  고른 = i;
  건들.forEach((_, j) => $('c' + j).setAttribute('aria-pressed', String(i === j)));
  마당(0, 'done', 건들[i].이름);
  그리기1(); 그리기3(); 그리기4(); 그리기5(); 그리기6();
  가마당(1);
  검사하기();
}

/* ── 1. 준비물 ────────────────────────────────────── */
function 그리기1() {
  const c = 건들[고른], 안된 = c.사전등록.filter(x => !x.됨);
  let h = '<p class="hint">특허를 처음 내는 분은 이 셋을 먼저 해야 합니다. '
    + '<b>한 번만 하면 그다음부터는 필요 없습니다.</b> 이미 하셨다면 값을 적어 두세요.</p>'
    + 표('<tr><th>할 일</th><th>했나요</th></tr>' + c.사전등록.map(x => `
      <tr${x.됨 ? '' : ' class="warn"'}>
        <td><a href="${x.자리}" target="_blank" rel="noopener">${안전(x.이름)} ${아이콘('out')}</a>
          <div class="src">${안전(x.근거)}</div></td>
        <td>${x.됨 ? 아이콘('ok') + ' 완료<div class="src">' + 안전(x.값) + '</div>'
      : 아이콘('warn') + ' <b>아직</b>'}</td></tr>`).join(''));
  h += 알림('warn', '인증서는 새로 만들 필요가 없습니다',
    '은행에서 쓰시는 공동인증서를 그대로 씁니다. 특허로에 한 번 등록해 두면 계속 쓸 수 있습니다.');
  h += 다음단추(2, '원고 검사로');
  마당(1, 안된.length ? 'stop' : 'done',
    안된.length ? `${안된.length}가지 남음` : '갖췄습니다');
  $('b1').innerHTML = h;
}

/* ── 2. 원고 검사 ─────────────────────────────────── */
async function 검사하기() {
  $('b2').innerHTML = '<div class="empty"><span class="spin"></span>원고를 검사하는 중입니다</div>';
  마당(2, '', '검사 중');
  const r = await api('/api/check?i=' + 고른);
  const c = 건들[고른];
  let h = r.성함
    ? 알림('ok', '관청이 문제 삼을 곳이 없습니다', '형식 검사를 모두 지났습니다. 다음 마당으로 가세요.')
    : 알림('bad', `먼저 고쳐야 할 것이 ${r.오류.length}가지 있습니다`,
      '이대로는 관청에 낼 수 없습니다. 아래를 하나씩 해결하세요.');

  h += r.오류.map(x => 알림('bad', 안전(x.뜻),
    안전(x.방법) + `<span class="src">${안전(x.원문)}</span>`)).join('');
  h += r.경고.map(x => 알림('warn', 안전(x.뜻), 안전(x.방법))).join('');

  if (c.막는값.length) {
    h += '<p class="hint" style="margin-top:20px">'
      + '<b>사람이 정해야 하는 값입니다.</b> 프로그램이 대신 정할 수 없습니다. '
      + '여기에 적고 저장하세요.</p>';
    h += c.막는값.map(n => {
      const 길 = n === '발명자 이름' ? 'inventors.0.name' : 'applicants.0.biz_no';
      const 도움 = n === '발명자 이름'
        ? '실제로 발명한 사람의 이름입니다. 회사가 내더라도 발명자는 사람 이름으로 적습니다. 빠뜨리면 등록된 뒤에도 무효가 될 수 있습니다.'
        : '사업자등록증에 있는 번호입니다. 000-00-00000 꼴로 적습니다.';
      const 예 = n === '발명자 이름' ? '예: 김철수' : '예: 123-45-67890';
      return `<div style="margin-bottom:14px">
        <label for="f_${길}">${안전(n)}</label>
        <input type="text" id="f_${길}" placeholder="${예}" style="max-width:320px">
        <div class="sub">${도움}</div></div>`;
    }).join('')
      + `<div class="row"><button class="p" onclick="채우기()">저장하고 다시 검사</button>
         <span id="fm" style="color:var(--go);font-weight:600"></span></div>`;
  }
  {
    h += `<div class="note warn" style="margin-top:20px">${아이콘('board')}<div>
      <b>더 자세히 손보려면</b>
      <p>청구항 대비, 단락번호 다시 매기기, 선행기술 조사까지 다루는
      전문가용 화면이 따로 있습니다. 표제 오른쪽에서도 언제든 열 수 있습니다.</p>
      <button class="sm" onclick="보드열기()" style="margin-top:8px">
        특허킷 메인보드 열기 ${아이콘('out')}</button></div></div>`;
  }
  h += 다음단추(3, '서류 만들기로');
  마당(2, r.성함 ? 'done' : 'stop', r.성함 ? '지났습니다' : `${r.오류.length}가지 고쳐야 함`);
  $('b2').innerHTML = h;
}

async function 채우기() {
  const 값 = {};
  document.querySelectorAll('[id^="f_"]').forEach(e => { 값[e.id.slice(2)] = e.value; });
  const r = await api('/api/fill', { i: 고른, 값 });
  건들[고른] = r.건;
  if (r.바꿈.length) { 그리기1(); 그리기5(); 검사하기(); }
  else $('fm').textContent = '적은 것이 없습니다';
}

/* ── 3. 서류 만들기 ───────────────────────────────── */
function 그리기3() {
  const c = 건들[고른];
  $('b3').innerHTML = '<p class="hint">관청에 낼 파일을 한 번에 만듭니다. '
    + '제출본, 워드 파일(DOCX), 도면 그림, 출원 준비서가 나옵니다.</p>'
    + `<div class="row"><button class="p" onclick="만들기()">
        ${아이콘('build')} 서류 만들기</button>
       <button onclick="폴더()">${아이콘('folder')} 만든 것 열어보기</button></div>`
    + '<div id="만든것" style="margin-top:16px"></div>'
    + 다음단추(4, '비용 확인으로');
  마당(3, c.준비서 ? 'done' : '', c.준비서 ? '만들어 두었습니다' : '아직');
}
async function 만들기() {
  $('만든것').innerHTML = '<div class="empty"><span class="spin"></span>'
    + '만드는 중입니다. 조금 걸립니다</div>';
  const r = await api('/api/build', { i: 고른 });
  건들[고른] = r.건;
  $('만든것').innerHTML = (r.줄 || []).map(x => 알림(x.ok ? 'ok' : 'bad', 안전(x.글),
    x.ok || !x.원문 ? '' : `<span class="src">${안전(x.원문)}</span>`)).join('')
    + (r.성함 ? '' : 알림('warn', '이것부터 고쳐야 서류가 나옵니다',
      `<button class="p sm" onclick="가마당(2)" style="margin-top:6px">
        2 원고 검사로 가서 고치기 ${아이콘('next')}</button>`));
  마당(3, r.성함 ? 'done' : 'stop', r.성함 ? '다 만들었습니다' : '막혔습니다');
  그리기4(); 그리기5(); 검사하기(); 띠();
}
async function 폴더() { await api('/api/folder', { i: 고른 }); }

/* ── 4. 비용 ──────────────────────────────────────── */
function 그리기4() {
  const s = 건들[고른].수수료;
  $('b4').innerHTML = '<p class="hint">특허를 낼 때 관청에 내는 돈입니다. '
    + '개인이나 중소기업은 70%를 깎아 줍니다.</p>'
    + 표(`<tr><th>기본 출원료 <div class="src">전자출원 · 국어</div></th>
          <td class="n">${원(s.기본)}</td></tr>
        <tr><th>면수 가산 <div class="src">${s.면수}면 · 20면 넘는 만큼</div></th>
          <td class="n">${원(s.가산)}</td></tr>
        <tr><th>감면 <div class="src">${안전(s.감면설명)}</div></th>
          <td class="n">−${원(s.감면액)}</td></tr>
        <tr><th>낼 돈</th><td class="n"><span class="won">${원(s.실납부)}</span></td></tr>`)
    + 알림('warn', '심사청구료는 따로이고 지금 안 내도 됩니다',
      `출원일부터 <b>3년 안에</b> 내면 됩니다. 지금 청구항 수로는 ${원(s.심사청구_참고)}
       입니다(감면 전). 이걸 끝내 안 내면 심사를 받지 못하고 취하한 것으로 봅니다.`)
    + '<p class="hint">면수는 어림한 값입니다. 정확한 금액은 특허로 결제 화면이 정본입니다.</p>'
    + 다음단추(5, '내는 차례로');
  마당(4, 'done', 원(s.실납부));
}

/* ── 5. 특허로에 내기 ─────────────────────────────── */
function 그리기5() {
  const c = 건들[고른], s = c.수수료;
  const 값 = [['발명의 명칭', c.제목], ['출원인', c.출원인], ['발명자', c.발명자],
  ['청구항 수', c.청구항 + '항'], ['도면', c.도면 + '매'], ['낼 돈', 원(s.실납부)]];
  $('b5').innerHTML =
    알림('warn', '여기부터는 사람이 눌러야 합니다',
      '특허청은 제출용 통로(API)를 열어 두지 않았고, 제출은 공동인증서로 서명하는 '
      + '법률행위입니다(특허법 제28조의3). 프로그램이 대신 낼 수 없습니다.')
    + '<p class="hint">아래 차례대로 하세요. 파란 글씨를 누르면 그 자리가 열립니다.</p>'
    + 표(`
      <tr><th>1</th><td><a href="https://patent.go.kr/smart/jsp/kiponet/ir/pctinfo/PctOnlineInstall.do"
        target="_blank" rel="noopener">전자출원 프로그램 설치 ${아이콘('out')}</a>
        <div class="sub">NK-Editor 와 NKEAPS 두 가지입니다. 처음 한 번만 깔면 됩니다.</div></td></tr>
      <tr><th>2</th><td>NK-Editor 를 열고 3마당에서 만든 <b>워드 파일</b>을 넣습니다.
        <div class="sub">「도구 → 제출파일 생성」 을 누르면 .HLZ 파일이 나옵니다.
        이것이 관청이 받는 형식입니다.</div></td></tr>
      <tr><th>3</th><td>NKEAPS 로 출원서 서식을 채웁니다.
        <div class="sub">아래 표의 값을 그대로 옮겨 적으세요.</div></td></tr>
      <tr><th>4</th><td>도면 ${c.도면}매를 붙입니다.</td></tr>
      <tr><th>5</th><td><a href="https://www.patent.go.kr/smart/jsp/kiponet/ma/websolution/OnlineWrite.do"
        target="_blank" rel="noopener">특허로에서 제출 ${아이콘('out')}</a>
        <div class="sub">인증서로 서명합니다.</div></td></tr>
      <tr><th>6</th><td>수수료 <b>${원(s.실납부)}</b> 을 결제합니다.</td></tr>
      <tr><th>7</th><td>접수증과 <b>출원번호</b>가 바로 나옵니다.
        <div class="sub">꼭 적어 두세요. 7마당에서 씁니다.</div></td></tr>`)
    + '<p class="hint" style="margin-top:20px"><b>서식에 옮겨 적을 값</b></p>'
    + 표(값.map(([k, v]) => `<tr><th>${안전(k)}</th><td>${안전(v)}</td></tr>`).join(''))
    + `<div class="row"><button onclick="베끼기()">${아이콘('copy')} 위 값 한꺼번에 복사</button>
       <span id="cp" style="color:var(--go);font-weight:600"></span></div>`
    + 다음단추(6, '낸 뒤 할 일로');
  마당(5, '', '사람이 합니다');
}
function 베끼기() {
  const c = 건들[고른];
  const t = `발명의 명칭: ${c.제목}\n출원인: ${c.출원인}\n발명자: ${c.발명자}\n`
    + `청구항 수: ${c.청구항}항\n도면: ${c.도면}매`;
  navigator.clipboard.writeText(t).then(() => {
    $('cp').textContent = '복사했습니다';
    setTimeout(() => $('cp').textContent = '', 2500);
  });
}

/* ── 6. 낸 뒤 진행 상황 ───────────────────────────── */
function 그리기6() {
  const c = 건들[고른];
  let h = '<p class="hint">출원번호를 받으셨으면 여기에 넣으세요. '
    + '관청 기록을 불러와 지금 어디까지 갔는지와 남은 기한을 보여 줍니다.</p>'
    + '<label for="ano">출원번호</label>'
    + '<div class="row" style="margin-bottom:16px">'
    + `<input type="text" id="ano" value="${안전(c.출원번호 || '')}"
        placeholder="예: 1020260142020" style="width:230px">`
    + `<button class="p" onclick="추적()">${아이콘('search')} 조회</button>`
    + '<span id="tm" style="color:var(--ink-soft)"></span></div>';
  if (!열쇠있음) {
    h += `<div class="note warn">${아이콘('warn')}<div>
      <b>KIPRIS 열쇠가 없습니다</b>
      <p>관청 기록을 부르려면 열쇠가 필요합니다.
      <a href="https://plus.kipris.or.kr" target="_blank" rel="noopener">plus.kipris.or.kr ${아이콘('out')}</a>
      에서 무료로 받습니다. 한 번만 넣어 두면 계속 씁니다.</p>
      <div class="row" style="margin-top:10px">
        <input type="password" id="kkey" placeholder="KIPRIS 인증키" style="width:290px">
        <button onclick="열쇠넣기()">저장</button></div>
      <p class="src" style="margin-top:8px">열쇠는 이 컴퓨터의 개인 폴더에만 둡니다.
      원고 폴더에 넣지 않으므로 배포 묶음을 남에게 보내도 따라가지 않습니다.</p>
      </div></div>`;
  }
  h += '<div id="진행">' + 기한만(c) + '</div>';
  마당(6, c.출원번호 ? 'done' : '', c.출원번호 ? '출원번호 있음' : '기한 3가지');
  $('b6').innerHTML = h;
}

function 기한만(c) {
  return '<p class="hint">출원한 뒤 놓치면 안 되는 기한입니다.</p>'
    + 표(`<tr><th>30일 안</th><td><b>공지예외 증명서류</b>
        <div class="sub">발명을 미리 공개한 적이 있으면 이것을 내야 그 공개가 없던 것으로
        다뤄집니다. <b>넘기면 되돌릴 수 없습니다.</b></div>
        <div class="src">특허법 제30조제2항</div></td></tr>
      <tr><th>1년 안</th><td><b>정식 명세서로 바꾸기</b>
        <div class="sub">임시명세서(가출원)로 냈다면 1년 안에 정식 명세서를 내야 합니다.
        ${c.마감 ? '지금 건의 마감은 <b>' + 안전(c.마감) + '</b> 입니다.' : ''}</div>
        <div class="src">특허법 제42조의2제2항</div></td></tr>
      <tr><th>3년 안</th><td><b>심사청구</b>
        <div class="sub">안 하면 취하한 것으로 봅니다.</div>
        <div class="src">특허법 제59조제2항</div></td></tr>`);
}

/* 메인보드 열기 — 누를 때 주소를 받아 연다.
   미리 href 에 박아 두면 아직 안 뜬 사이에 누른 사람이 지금 쪽을 다시 열게 된다 */
async function 보드열기() {
  const 글 = $('보드글');
  const 본디 = 글 ? 글.textContent : '';
  if (글) 글.textContent = '메인보드를 여는 중…';
  $('보드길').disabled = true;
  try {
    const r = await api('/api/board');
    보드 = r.보드 || '';
    if (보드) window.open(보드, '_blank', 'noopener');
    else alert('메인보드를 띄우지 못했습니다.\n'
      + '특허킷이 깔려 있는지 보세요 — 검은 창에 pip install patentkit');
  } finally {
    if (글) 글.textContent = 본디;
    $('보드길').disabled = false;
  }
}

async function 열쇠넣기() {
  const r = await api('/api/key', { 열쇠: $('kkey').value });
  열쇠있음 = r.있음; 그리기6();
  if (열쇠있음) 추적();
}

async function 추적() {
  const 번호 = $('ano').value.trim();
  if (!번호) { $('tm').textContent = '출원번호를 넣으세요'; return; }
  $('tm').innerHTML = '<span class="spin"></span>관청 기록을 부르는 중';
  const r = await api('/api/track?no=' + encodeURIComponent(번호));
  $('tm').textContent = '';
  if (r.잘못 === '열쇠없음') { 열쇠있음 = false; 그리기6(); return; }
  if (r.잘못) {
    $('진행').innerHTML = 알림('bad', '부르지 못했습니다', 안전(r.잘못)) + 기한만(건들[고른]);
    return;
  }
  await api('/api/fill', { i: 고른, 값: { 'filing.application_number': 번호 } });
  건들[고른].출원번호 = 번호;

  const 걸음 = [['출원', r.출원일], ['공개', r.공개일], ['등록', r.등록일]];
  let h = 알림('ok', 안전(r.명칭), '지금 상태 — <b>' + 안전(r.법적상태 || '확인 필요') + '</b>')
    + 표(`<tr><th>출원번호</th><td>${안전(r.출원번호)}</td></tr>
      ${걸음.filter(x => x[1]).map(([이름, 날]) =>
      `<tr><th>${이름}</th><td>${안전(날)}</td></tr>`).join('')}
      ${r.공개번호 ? `<tr><th>공개번호</th><td>${안전(r.공개번호)}</td></tr>` : ''}
      ${r.등록번호 ? `<tr><th>등록번호</th><td>${안전(r.등록번호)}</td></tr>` : ''}
      <tr><th>청구항</th><td>${r.청구항수}항</td></tr>`);

  h += '<p class="hint" style="margin-top:20px"><b>출원일부터 세는 기한</b></p>'
    + 표(r.기한.map(k => {
      const 급 = k.남음 === null ? '' : k.남음 < 0 ? 'bad' : k.남음 < 30 ? 'warn' : '';
      const 남 = k.남음 === null ? '출원일을 몰라 셈하지 못했습니다'
        : k.남음 < 0 ? `${아이콘('stop')} <b>${-k.남음}일 지났습니다</b>`
          : k.남음 < 30 ? `${아이콘('warn')} <b>D-${k.남음}</b>`
            : `${아이콘('ok')} D-${k.남음}`;
      return `<tr class="${급}"><th>${안전(k.이름)}</th><td>${안전(k.날)} · ${남}
        <div class="sub">${안전(k.풀이)}</div>
        <div class="src">${안전(k.근거)}</div></td></tr>`;
    }).join(''));
  h += `<p class="src">KIPRIS 에서 ${안전(r.받은때)} 에 받았습니다.</p>`;
  $('진행').innerHTML = h;
  마당(6, 'done', 안전(r.법적상태 || '조회함'));
}

/* ── 켜기 ─────────────────────────────────────────── */
(async () => {
  const r = await api('/api/start');
  $('ver').textContent = '출원 도우미 ' + r.버전;
  그리기0(r);
})();
