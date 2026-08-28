# -*- coding: utf-8 -*-
"""출원 안내 화면 — 특허를 하나도 모르는 사람이 이것만 따라가면 되도록 만든다.

    python 화면.py [원고폴더]

브라우저 창이 하나 뜬다. 여섯 마당을 차례로 따라가면 관청에 낼 것이 다 갖춰진다.
마지막 서명과 결제만 사람이 특허로에서 누른다.

원고를 깊이 손보는 일(청구항 대비·선행기술·후보 원장)은 특허킷 2.7.0 의 메인보드가
훨씬 낫다. 그것을 다시 만들지 아니하고, 필요할 때 그 화면으로 넘긴다.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import 출원도우미 as D

뿌리 = Path(".").resolve()
보드주소 = ""          # 특허킷 2.7.0 메인보드. 띄우면 채워진다


# ─────────────────────────────────────────────── 자료 모으기


def 출원건들() -> list[Path]:
    if (뿌리 / "patent_config.json").exists():
        return [뿌리]
    return sorted({p.parent for p in 뿌리.rglob("patent_config.json")}
                  - {p.parent for p in 뿌리.rglob("_*/**/patent_config.json")})


def 설정(건: Path) -> dict:
    try:
        return json.loads((건 / "patent_config.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def 한건(건: Path) -> dict:
    cfg = 설정(건)
    발명 = cfg.get("invention") or {}
    출원 = cfg.get("filing") or {}
    막는값 = [f"{k}" for k, v in
              (("발명자 이름", D.설정값(cfg, "inventors.0.name")),
               ("사업자등록번호", D.설정값(cfg, "applicants.0.biz_no")))
              if not v or "★" in str(v)]
    return {
        "이름": 건.name, "폴더": str(건),
        "제목": 발명.get("title_kr") or "(제목 없음)",
        "출원인": ", ".join(a.get("name", "") for a in (cfg.get("applicants") or [])),
        "발명자": ", ".join(v.get("name", "") for v in (cfg.get("inventors") or [])),
        "마감": 출원.get("priority_deadline") or "",
        "청구항": len(D.청구항수(건)), "도면": D.도면수(건),
        "막는값": 막는값,
        "사전등록": [{"이름": n, "됨": 됨, "값": 값, "근거": 근거, "자리": 자리}
                   for n, 됨, 값, 근거, 자리 in D.사전등록점검(cfg)],
        "수수료": D.수수료셈(건, cfg),
        "준비서": (건 / "_출력" / "출원_준비.md").exists(),
    }


def 검사(건: Path) -> dict:
    코드, 글 = D.킷("validate", str(건))
    오류 = [l.strip() for l in 글.splitlines() if "[오류]" in l]
    경고 = [l.strip() for l in 글.splitlines() if "[경고]" in l]
    return {"성함": 코드 == 0, "오류": 오류, "경고": 경고}


쉬운말 = [
    (r"미확정", "사람이 정해야 하는 값이 비어 있습니다",
     "바로 아래 칸에 적고 「저장」 을 누르면 됩니다."),
    (r"깨진SVG|not well-formed", "도면 파일이 깨졌습니다",
     "도면 안의 「<」 기호가 문제입니다. 도면을 다시 만들거나 그 기호를 지우세요."),
    (r"불일치", "제출본이 원고와 다릅니다",
     "「3. 서류 만들기」를 누르면 자동으로 맞춰집니다."),
    (r"결번|중복|역행", "단락번호가 어긋났습니다",
     "메인보드의 「번호 다시 매기기」로 고칩니다."),
    (r"뒷받침", "청구항에 쓴 말이 설명에 없습니다",
     "청구항의 구성요소는 명세서 본문에서 설명해야 합니다(특허법 제42조제4항)."),
]


def 풀이(줄: str) -> dict:
    for 무늬, 뜻, 방법 in 쉬운말:
        if re.search(무늬, 줄):
            return {"원문": 줄, "뜻": 뜻, "방법": 방법}
    return {"원문": 줄, "뜻": "형식이 관청 기준과 다릅니다", "방법": "메인보드에서 자세히 봅니다."}


# ─────────────────────────────────────────────── 화면

화면 = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>특허 출원 안내</title>
<style>
:root{
  --paper:#ECEEE8; --sheet:#F7F8F4; --ink:#16222C; --ink2:#54636E; --faint:#8B98A1;
  --rule:#C3CABF; --rule2:#DDE2D8;
  --seal:#B23A2E; --seal-bg:#FAECE9; --seal-line:#E4B8B1;
  --stamp:#1F4E5F; --stamp-bg:#E4EDEF; --stamp-line:#B4CDD3;
  --jade:#2C6B4C; --jade-bg:#E8F1EA; --jade-line:#B6D4C0;
  --amber:#87610F; --amber-bg:#F7F1DE; --amber-line:#DFCE9E;
  --serif:Batang,"바탕",BatangChe,"Nanum Myeongjo",serif;
  --sans:"Malgun Gothic","맑은 고딕",system-ui,sans-serif;
  --mono:Consolas,"D2Coding",ui-monospace,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
  --paper:#121A1E; --sheet:#182126; --ink:#E3E8E1; --ink2:#9BAAB1; --faint:#6E7F87;
  --rule:#33454C; --rule2:#25333A;
  --seal:#DE7263; --seal-bg:#2A1512; --seal-line:#5C2A24;
  --stamp:#74B4C4; --stamp-bg:#122A31; --stamp-line:#2A4E58;
  --jade:#7FC49B; --jade-bg:#12241A; --jade-line:#2C4E38;
  --amber:#D9B463; --amber-bg:#241E10; --amber-line:#4E4224;
}}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.75 var(--sans);
  -webkit-font-smoothing:antialiased}
.wrap{max-width:940px;margin:0 auto;padding:0 24px}
a{color:var(--stamp)}
header{border-bottom:3px double var(--rule);background:var(--paper);position:sticky;top:0;z-index:9}
.hd{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;
  padding:18px 0 13px;flex-wrap:wrap}
.hd h1{margin:0;font:400 25px/1.25 var(--serif);letter-spacing:.15em}
.badge{font:400 12px/1 var(--serif);letter-spacing:.2em;color:var(--faint);
  border:1px solid var(--rule);padding:6px 10px}
main{padding:24px 0 90px}
.lead{font:400 17px/1.85 var(--serif);margin:0 0 26px;padding-left:15px;
  border-left:3px double var(--rule);word-break:keep-all;text-wrap:pretty}

/* 마당 */
.step{background:var(--sheet);border:1px solid var(--rule2);margin-bottom:16px}
.step>summary{cursor:pointer;padding:15px 18px;display:flex;align-items:center;gap:12px;
  font:400 18px/1.4 var(--serif);letter-spacing:.04em;list-style:none}
.step>summary::-webkit-details-marker{display:none}
.step[open]>summary{border-bottom:1px solid var(--rule2)}
.no{flex:none;width:29px;height:29px;border-radius:50%;display:grid;place-items:center;
  font:400 14px var(--mono);background:var(--stamp-bg);color:var(--stamp);
  border:1px solid var(--stamp-line)}
.step.done .no{background:var(--jade-bg);color:var(--jade);border-color:var(--jade-line)}
.step.stop .no{background:var(--seal-bg);color:var(--seal);border-color:var(--seal-line)}
.tag{margin-left:auto;font:400 12px var(--sans);padding:3px 9px;border:1px solid var(--rule)}
.done .tag{background:var(--jade-bg);color:var(--jade);border-color:var(--jade-line)}
.stop .tag{background:var(--seal-bg);color:var(--seal);border-color:var(--seal-line)}
.body{padding:18px}
.hint{color:var(--ink2);margin:0 0 14px;word-break:keep-all}

/* 표 */
table{border-collapse:collapse;width:100%;margin:0 0 14px;font-size:14px}
th,td{border-bottom:1px solid var(--rule2);padding:9px 10px;text-align:left;vertical-align:top}
th{font-weight:400;color:var(--ink2);white-space:nowrap;width:1%}
td.n{font-family:var(--mono);text-align:right;white-space:nowrap}
.tw{overflow-x:auto}

/* 단추 */
button,.btn{font:14px var(--sans);padding:9px 15px;border:1px solid var(--rule);
  background:var(--sheet);color:var(--ink);cursor:pointer;text-decoration:none;
  display:inline-block}
button:hover,.btn:hover{border-color:var(--stamp)}
button.p{background:var(--stamp);color:#fff;border-color:var(--stamp)}
button:disabled{opacity:.45;cursor:not-allowed}
.row{display:flex;gap:9px;flex-wrap:wrap;align-items:center}

/* 건 고르기 */
.cases{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:10px}
.case{text-align:left;padding:12px;line-height:1.5}
.case.on{border-color:var(--stamp);box-shadow:inset 0 0 0 1px var(--stamp)}
.case b{display:block;font-weight:400;font-family:var(--serif);font-size:16px}
.case small{color:var(--faint);display:block;margin-top:4px;font-size:12px}

/* 알림 */
.note{padding:11px 13px;border:1px solid var(--rule2);margin:0 0 12px;font-size:14px;
  word-break:keep-all}
.note.bad{background:var(--seal-bg);border-color:var(--seal-line)}
.note.ok{background:var(--jade-bg);border-color:var(--jade-line)}
.note.warn{background:var(--amber-bg);border-color:var(--amber-line)}
.note b{font-weight:400;font-family:var(--serif);font-size:15px}
.note p{margin:5px 0 0;color:var(--ink2)}
.empty{color:var(--faint);padding:22px;text-align:center}
.spin{display:inline-block;width:12px;height:12px;margin-right:7px;
  border:2px solid var(--rule);border-top-color:var(--stamp);border-radius:50%;
  animation:s .7s linear infinite;vertical-align:-1px}
@keyframes s{to{transform:rotate(360deg)}}
.won{font-family:var(--mono);font-size:19px;color:var(--seal)}
.copy{font-size:12px;padding:4px 9px}
pre{background:var(--paper);border:1px solid var(--rule2);padding:11px;overflow-x:auto;
  font:13px/1.6 var(--mono);margin:0 0 12px}
</style></head><body>

<header><div class="wrap hd">
  <h1>특허 출원 안내</h1>
  <div class="badge" id="ver">준비 중</div>
</div></header>

<main class="wrap">
  <p class="lead">특허를 처음 내시나요. 아래 여섯 마당을 위에서부터 차례로 따라가면 됩니다.<br>
  각 마당이 무엇인지와 무엇을 눌러야 하는지 함께 적어 두었습니다.</p>

  <details class="step" id="s0" open><summary><span class="no">0</span>어느 특허를 낼까요<span class="tag" id="t0">고르세요</span></summary>
    <div class="body">
      <p class="hint">특허 하나가 폴더 하나입니다. 낼 것을 고르세요.</p>
      <div class="cases" id="cases"><div class="empty"><span class="spin"></span>찾는 중</div></div>
    </div></details>

  <details class="step" id="s1"><summary><span class="no">1</span>준비물 갖추기<span class="tag" id="t1">—</span></summary>
    <div class="body" id="b1"></div></details>

  <details class="step" id="s2"><summary><span class="no">2</span>원고 검사<span class="tag" id="t2">—</span></summary>
    <div class="body" id="b2"></div></details>

  <details class="step" id="s3"><summary><span class="no">3</span>서류 만들기<span class="tag" id="t3">—</span></summary>
    <div class="body" id="b3"></div></details>

  <details class="step" id="s4"><summary><span class="no">4</span>비용 확인<span class="tag" id="t4">—</span></summary>
    <div class="body" id="b4"></div></details>

  <details class="step" id="s5"><summary><span class="no">5</span>특허로에 내기<span class="tag" id="t5">—</span></summary>
    <div class="body" id="b5"></div></details>

  <details class="step" id="s6"><summary><span class="no">6</span>낸 뒤에 할 일<span class="tag" id="t6">—</span></summary>
    <div class="body" id="b6"></div></details>
</main>

<script>
const $=i=>document.getElementById(i);
const 안전=s=>String(s??'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const 원=n=>Number(n||0).toLocaleString('ko-KR')+'원';
let 건들=[], 고른=null, 보드='';

const 보이게=el=>window.scrollTo({top:el.getBoundingClientRect().top+window.scrollY
  -document.querySelector('header').offsetHeight-12});

async function api(길,몸){
  const r=await fetch(길,몸?{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(몸)}:undefined);
  return r.json();
}
function 표(칸){ return '<div class="tw"><table>'+칸+'</table></div>'; }
function 마당(n,상태,꼬리){
  const e=$('s'+n); e.classList.remove('done','stop');
  if(상태) e.classList.add(상태);
  $('t'+n).textContent=꼬리;
}

(async()=>{
  const r=await api('/api/start');
  보드=r.보드||''; $('ver').textContent='출원 도우미 '+r.버전;
  건들=r.건들;
  $('cases').innerHTML = 건들.length ? 건들.map((c,i)=>`
    <button class="case" id="c${i}" onclick="고르기(${i})">
      <b>${안전(c.이름)}</b>
      <small>${안전(c.제목).slice(0,44)}…</small>
      <small>청구항 ${c.청구항}항 · 도면 ${c.도면}매${c.마감?' · 마감 '+c.마감:''}</small>
    </button>`).join('')
    : '<div class="empty">이 폴더에 특허 원고가 없습니다.<br>patent_config.json 이 있는 폴더에서 실행하세요.</div>';
  if(건들.length===1) 고르기(0);
})();

function 고르기(i){
  고른=i; 건들.forEach((_,j)=>$('c'+j).classList.toggle('on',i===j));
  마당(0,'done',건들[i].이름);
  ['1','2','3','4','5','6'].forEach(n=>$('s'+n).open=false);
  그리기1(); 그리기3(); 그리기4(); 그리기5(); 그리기6();
  $('s1').open=true; 보이게($('s1'));
  검사하기();
}

/* 1 — 준비물 */
function 그리기1(){
  const c=건들[고른], 안된=c.사전등록.filter(x=>!x.됨);
  let h='<p class="hint">특허를 처음 내는 분은 이 셋을 먼저 해야 합니다. <b>한 번만 하면 됩니다.</b> '
    +'이미 하셨다면 아래에서 값을 적어 두세요. 다음부터 「완료」로 뜹니다.</p>';
  h+=표('<tr><th>할 일</th><th>상태</th><th>근거</th></tr>'+c.사전등록.map(x=>
    `<tr><td><a href="${x.자리}" target="_blank" rel="noopener">${안전(x.이름)}</a>
     <div style="color:var(--faint);font-size:12px">${안전(x.값)}</div></td>
     <td>${x.됨?'완료':'<b style="color:var(--seal)">미확인</b>'}</td>
     <td style="color:var(--ink2);font-size:13px">${안전(x.근거)}</td></tr>`).join(''));
  h+='<p class="hint">인증서는 은행에서 쓰시는 공동인증서면 됩니다. '
    +'특허로에 한 번 등록해 두면 계속 씁니다.</p>';
  마당(1, 안된.length?'stop':'done', 안된.length?안된.length+'건 남음':'갖춤');
  $('b1').innerHTML=h;
}

/* 2 — 검사 */
async function 검사하기(){
  $('b2').innerHTML='<div class="empty"><span class="spin"></span>원고를 검사하는 중</div>';
  마당(2,'','검사 중');
  const r=await api('/api/check?i='+고른);
  let h='';
  if(r.성함){
    h='<div class="note ok"><b>관청이 문제 삼을 곳이 없습니다.</b>'
     +'<p>형식 검사를 모두 통과했습니다. 다음 마당으로 가세요.</p></div>';
    마당(2,'done','통과');
  }else{
    h='<div class="note bad"><b>먼저 고쳐야 할 것이 '+r.오류.length+'건 있습니다.</b>'
     +'<p>이대로는 관청에 낼 수 없습니다.</p></div>';
    h+=r.오류.map(x=>`<div class="note bad"><b>${안전(x.뜻)}</b><p>${안전(x.방법)}</p>
      <p style="font-size:12px;color:var(--faint)">${안전(x.원문)}</p></div>`).join('');
    마당(2,'stop',r.오류.length+'건 고쳐야 함');
  }
  h+=r.경고.map(x=>`<div class="note warn"><b>${안전(x.뜻)}</b><p>${안전(x.방법)}</p></div>`).join('');
  const c=건들[고른];
  if(c.막는값.length){
    h+='<div class="note warn"><b>사람이 정해야 하는 값이 남아 있습니다.</b>'
     +'<p>프로그램이 대신 정할 수 없는 값입니다. 아래에 적고 저장하세요.</p></div>';
    h+='<div class="tw"><table>'+c.막는값.map(n=>{
      const 길 = n==='발명자 이름' ? 'inventors.0.name' : 'applicants.0.biz_no';
      const 도움 = n==='발명자 이름'
        ? '실제로 발명한 사람의 이름입니다. 회사가 내더라도 발명자는 사람 이름으로 적습니다. 빠뜨리면 등록 뒤에도 무효가 될 수 있습니다.'
        : '000-00-00000 형식으로 적습니다.';
      return `<tr><th>${안전(n)}</th><td>
        <input id="f_${길}" style="font:14px var(--sans);padding:7px 9px;
          border:1px solid var(--rule);background:var(--paper);color:var(--ink);width:230px">
        <div style="color:var(--faint);font-size:12px;margin-top:4px">${도움}</div></td></tr>`;
    }).join('')+'</table></div>'
     +'<div class="row"><button class="p" onclick="채우기()">저장</button>'
     +'<span id="fm" style="color:var(--jade)"></span></div>';
  }
  if(보드) h+=`<p class="hint">원고를 직접 고치려면 <a href="${보드}" target="_blank" rel="noopener">특허킷 메인보드</a>에서
    청구항·단락번호·선행기술까지 자세히 다룰 수 있습니다.</p>`;
  $('b2').innerHTML=h;
}

/* 3 — 서류 */
function 그리기3(){
  $('b3').innerHTML='<p class="hint">관청에 낼 파일을 한 번에 만듭니다. '
    +'제출본·DOCX·도면 PNG·출원 준비서가 나옵니다.</p>'
    +'<div class="row"><button class="p" onclick="만들기()">서류 만들기</button>'
    +'<button onclick="폴더()">만든 것 열어보기</button></div><div id="r3"></div>';
  마당(3, 건들[고른].준비서?'done':'', 건들[고른].준비서?'만들어 둠':'—');
}
async function 만들기(){
  $('r3').innerHTML='<div class="empty"><span class="spin"></span>만드는 중입니다. 조금 걸립니다</div>';
  const r=await api('/api/build',{i:고른});
  건들[고른]=r.건;
  $('r3').innerHTML=(r.줄||[]).map(x=>`<div class="note ${x.ok?'ok':'bad'}">${안전(x.글)}</div>`).join('');
  마당(3, r.성함?'done':'stop', r.성함?'다 만듦':'막힘');
  그리기4(); 그리기5(); 검사하기();
}
async function 폴더(){ await api('/api/folder',{i:고른}); }

async function 채우기(){
  const 값={};
  document.querySelectorAll('[id^="f_"]').forEach(e=>{값[e.id.slice(2)]=e.value;});
  const r=await api('/api/fill',{i:고른, 값:값});
  건들[고른]=r.건;
  $('fm').textContent = r.바꿈.length ? '저장했습니다' : '적은 것이 없습니다';
  if(r.바꿈.length){ 그리기1(); 그리기5(); 검사하기(); }
}

/* 4 — 비용 */
function 그리기4(){
  const s=건들[고른].수수료;
  $('b4').innerHTML='<p class="hint">특허를 낼 때 관청에 내는 돈입니다. '
    +'개인이나 중소기업은 70%를 깎아 줍니다.</p>'
    +표(`<tr><th>기본 출원료 (전자·국어)</th><td class="n">${원(s.기본)}</td></tr>
      <tr><th>면수 가산 (${s.면수}면 · 20면 넘는 만큼)</th><td class="n">${원(s.가산)}</td></tr>
      <tr><th>감면 (${안전(s.감면설명)})</th><td class="n">−${원(s.감면액)}</td></tr>
      <tr><th>낼 돈</th><td class="n"><span class="won">${원(s.실납부)}</span></td></tr>`)
    +`<div class="note warn"><b>심사청구료는 따로입니다.</b>
      <p>지금 안 내도 됩니다. 출원일부터 <b>3년 안에</b> 내면 되고, 지금 청구항 수로는
      ${원(s.심사청구_참고)}입니다(감면 전). 이걸 안 내면 심사를 받지 못하고 취하된 것으로 봅니다.</p></div>`
    +'<p class="hint">면수는 어림한 값입니다. 정확한 금액은 특허로 결제 화면이 정본입니다.</p>';
  마당(4,'done',원(s.실납부));
}

/* 5 — 제출 */
function 그리기5(){
  const c=건들[고른], s=c.수수료;
  const 값=[['발명의 명칭',c.제목],['출원인',c.출원인],['발명자',c.발명자],
    ['청구항 수',c.청구항+'항'],['도면',c.도면+'매'],['낼 돈',원(s.실납부)]];
  $('b5').innerHTML='<div class="note warn"><b>여기부터는 사람이 눌러야 합니다.</b>'
    +'<p>특허청은 제출용 API 를 열어 두지 않았고, 제출은 공동인증서로 서명하는 법률행위입니다'
    +'(특허법 제28조의3). 프로그램이 대신 낼 수 없습니다.</p></div>'
    +'<p class="hint">아래 차례대로 하세요. 각 줄의 파란 글씨를 누르면 그 자리가 열립니다.</p>'
    +표(`<tr><th>1</th><td><a href="https://patent.go.kr/smart/jsp/kiponet/ir/pctinfo/PctOnlineInstall.do" target="_blank" rel="noopener">전자출원 SW 설치</a> — NK-Editor 와 NKEAPS. 처음 한 번만</td></tr>
      <tr><th>2</th><td>NK-Editor 를 열고 3마당에서 만든 <b>DOCX</b> 를 넣습니다.<br>
        「도구 → 제출파일 생성」 을 누르면 <b>.HLZ</b> 파일이 나옵니다. 이게 관청이 받는 형식입니다.</td></tr>
      <tr><th>3</th><td>NKEAPS 로 출원서 서식을 채웁니다. 아래 값을 그대로 옮겨 적으세요.</td></tr>
      <tr><th>4</th><td>도면 ${c.도면}매를 붙입니다.</td></tr>
      <tr><th>5</th><td><a href="https://www.patent.go.kr/smart/jsp/kiponet/ma/websolution/OnlineWrite.do" target="_blank" rel="noopener">특허로에서 제출</a> — 인증서로 서명합니다.</td></tr>
      <tr><th>6</th><td>수수료 ${원(s.실납부)} 을 결제합니다.</td></tr>
      <tr><th>7</th><td>접수증과 <b>출원번호</b>가 바로 나옵니다. 꼭 적어 두세요.</td></tr>`)
    +'<p class="hint">서식에 옮겨 적을 값</p>'
    +표(값.map(([k,v])=>`<tr><th>${안전(k)}</th><td>${안전(v)}</td></tr>`).join(''))
    +'<div class="row"><button class="copy" onclick="베끼기()">위 값 한꺼번에 복사</button>'
    +'<span id="cp" style="color:var(--jade)"></span></div>';
  마당(5,'','사람이 함');
}
function 베끼기(){
  const c=건들[고른];
  const t=`발명의 명칭: ${c.제목}\n출원인: ${c.출원인}\n발명자: ${c.발명자}\n`
    +`청구항 수: ${c.청구항}항\n도면: ${c.도면}매`;
  navigator.clipboard.writeText(t).then(()=>{$('cp').textContent='복사했습니다';
    setTimeout(()=>$('cp').textContent='',2500);});
}

/* 6 — 뒤에 할 일 */
function 그리기6(){
  const c=건들[고른];
  $('b6').innerHTML='<p class="hint">출원번호를 받은 뒤에 놓치면 안 되는 기한입니다.</p>'
    +표(`<tr><th>30일 안</th><td><b>공지예외 증명서류</b>를 냅니다.
        발명을 미리 공개한 적이 있다면 이걸 내야 그 공개가 없던 것으로 취급됩니다(특허법 제30조제2항).
        <b>넘기면 되돌릴 수 없습니다.</b></td></tr>
      <tr><th>1년 안</th><td>임시명세서(가출원)로 냈다면 <b>정식 명세서</b>로 바꿔야 합니다.
        ${c.마감?'지금 건의 마감은 <b>'+c.마감+'</b> 입니다.':''}</td></tr>
      <tr><th>3년 안</th><td><b>심사청구</b>를 합니다. 안 하면 취하된 것으로 봅니다.</td></tr>`)
    +'<p class="hint">진행 상황은 출원번호로 볼 수 있습니다.</p>'
    +'<pre>python 출원도우미.py 추적 &lt;출원번호&gt;</pre>';
  마당(6,'','기한 3가지');
}
</script></body></html>
"""


# ─────────────────────────────────────────────── 서버


class 처리기(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def 보냄(self, 자료, 형식="application/json"):
        몸 = (json.dumps(자료, ensure_ascii=False) if 형식.startswith("application")
              else 자료).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", f"{형식}; charset=utf-8")
        self.send_header("Content-Length", str(len(몸)))
        self.end_headers()
        self.wfile.write(몸)

    def do_GET(self):
        길 = urlparse(self.path)
        물 = parse_qs(길.query)
        if 길.path in ("/", "/index.html"):
            return self.보냄(화면, "text/html")
        if 길.path == "/api/start":
            return self.보냄({"버전": D.버전, "보드": 보드주소,
                            "건들": [한건(g) for g in 출원건들()]})
        if 길.path == "/api/check":
            건 = 출원건들()[int(물.get("i", ["0"])[0])]
            r = 검사(건)
            return self.보냄({"성함": r["성함"],
                            "오류": [풀이(x) for x in r["오류"]],
                            "경고": [풀이(x) for x in r["경고"]]})
        self.send_error(404)

    def do_POST(self):
        몸 = json.loads(self.rfile.read(int(self.headers["Content-Length"] or 0)) or b"{}")
        건 = 출원건들()[int(몸.get("i", 0))]
        if self.path == "/api/build":
            줄 = []
            성함 = True
            for 이름, 인자 in (("제출본", "build"), ("도면", "figures"),
                             ("검사", "validate"), ("서식(DOCX)", "docx")):
                코드, 글 = D.킷(인자, str(건))
                줄.append({"ok": 코드 == 0, "글": f"{이름} — " +
                          ("만들었습니다" if 코드 == 0 else
                           next((l.strip() for l in 글.splitlines() if "[오류]" in l),
                                "막혔습니다"))})
                if 코드 != 0 and 인자 == "validate":
                    성함 = False
                    break
            D.준비(건, False)
            return self.보냄({"성함": 성함, "줄": 줄, "건": 한건(건)})
        if self.path == "/api/fill":
            f = 건 / "patent_config.json"
            cfg = json.loads(f.read_text(encoding="utf-8"))
            바꿈 = []
            for 길, 값 in (몸.get("값") or {}).items():
                값 = (값 or "").strip()
                if not 값:
                    continue
                자리, 끝 = cfg, 길.split(".")
                for k in 끝[:-1]:
                    자리 = 자리[int(k)] if isinstance(자리, list) else 자리.setdefault(k, {})
                자리[끝[-1]] = 값
                바꿈.append(길)
            if 바꿈:
                shutil.copy(f, f.with_name(f.name + ".bak_화면"))
                f.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
            return self.보냄({"바꿈": 바꿈, "건": 한건(건)})
        if self.path == "/api/folder":
            낼 = 건 / "_출력"
            subprocess.Popen(["explorer", str(낼)] if sys.platform == "win32"
                             else ["open", str(낼)])
            return self.보냄({"열림": True})
        self.send_error(404)


def 보드띄우기(폴더: Path) -> None:
    """특허킷 2.7.0 메인보드를 뒤에서 띄우고 그 주소를 받아 둔다."""
    global 보드주소
    try:
        p = subprocess.Popen([sys.executable, "-m", "patentkit", "web", str(폴더),
                              "--no-open"], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace")
        for _ in range(40):
            줄 = p.stdout.readline()
            if not 줄:
                break
            m = re.search(r"(http://127\.0\.0\.1:\d+/\?key=\S+)", 줄)
            if m:
                보드주소 = m.group(1)
                return
    except Exception:
        pass


def main() -> int:
    global 뿌리
    뿌리 = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    threading.Thread(target=보드띄우기, args=(뿌리,), daemon=True).start()
    서버 = ThreadingHTTPServer(("127.0.0.1", 0), 처리기)
    주소 = f"http://127.0.0.1:{서버.server_address[1]}/"
    print(f"특허 출원 안내 — 창을 띄웁니다: {주소}\n"
          f"  원고 폴더: {뿌리}\n  이 창을 닫으면 꺼집니다. (Ctrl+C)")
    threading.Timer(0.5, lambda: webbrowser.open(주소)).start()
    try:
        서버.serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
