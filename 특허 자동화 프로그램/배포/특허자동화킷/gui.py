# -*- coding: utf-8 -*-
"""특허 자동화 킷 — 창 화면. 특허를 모르는 사람이 쓰는 것을 전제로 한다.

    python gui.py

브라우저 창이 하나 뜬다. 폴더를 고르고 단추를 누르면 된다.
하는 일은 patentkit.py 와 같다. 서버는 이 컴퓨터 안에서만 돈다.

화면의 서식은 이 킷이 실제로 뽑아내는 물건 — 특허청 공보 — 에서 가져왔다.
표제는 patent_config.json 이 지정한 본문 글꼴(바탕)로 짜고, 절 이름은 【 】 로 묶으며,
수치는 Consolas 로 세로줄을 맞춘다. 오류가 없는 출원건에는 직인이 찍힌다.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import patentkit as K

# ─────────────────────────────────────────────── 검사 이름을 쉬운 말로 옮긴다

쉬운말 = {
    "config": ("서지사항 파일", "출원인·발명자 같은 기본 정보를 담은 patent_config.json 파일입니다.",
               "폴더 안에 patent_config.json 이 있는지, 문법이 깨지지 않았는지 보세요."),
    "파일": ("원고 파일", "명세서와 청구범위 원고 파일이 제자리에 있는지 봅니다.",
             "01_명세서.md, 02_청구범위.md 두 파일이 폴더 안에 있어야 합니다."),
    "사람 확인 값": ("사람이 채워야 할 칸", "★ 표시는 프로그램이 대신 정할 수 없는 값입니다. 발명자 이름, 사업자등록번호 같은 것.",
                  "patent_config.json 을 열어 ★ 가 붙은 값을 실제 값으로 바꾸세요."),
    "발명의 명칭": ("발명의 이름", "특허의 제목입니다. 출원서 맨 앞에 들어갑니다.",
                "patent_config.json 의 invention.title_kr 을 채우세요."),
    "출원인": ("출원인", "특허를 가질 사람이나 회사입니다. 보통 회사 이름과 사업자등록번호를 적습니다.",
             "사업자등록번호는 000-00-00000 형식으로 적으세요."),
    "발명자": ("발명자", "실제로 발명한 사람입니다. 회사가 출원해도 발명자는 사람 이름으로 적습니다.",
             "퇴사자나 사외 공동발명자를 빠뜨리면 나중에 특허가 무효가 될 수 있습니다. 꼭 확인하세요."),
    "발명자 지분": ("발명자 지분", "발명자가 여러 명이면 기여도를 %로 나눠 적고, 합이 100%가 되어야 합니다.",
                 "inventors 의 share_pct 값을 합계 100 이 되게 맞추세요."),
    "IPC": ("기술 분류 번호", "이 발명이 어느 기술 분야인지 나타내는 국제 코드입니다.",
            "특허청 KIPRIS 에서 비슷한 특허를 찾아 그 IPC 를 참고해 적으세요."),
    "공지예외": ("공개했던 발명 구제", "출원 전에 논문·발표·제품으로 공개했다면 12개월 안에 출원해야 구제받습니다.",
               "공개일과 마감일을 맞추고, 출원 후 30일 안에 증명서류를 내세요."),
    "필수 절": ("반드시 있어야 할 항목", "특허청 양식에는 【기술분야】【요약서】처럼 꼭 있어야 하는 칸이 정해져 있습니다.",
              "01_명세서.md 에 빠진 【 】 항목을 추가하세요."),
    "단락번호 시작": ("문단 번호 시작 위치", "명세서 문단에는 [0001] 부터 번호를 붙입니다. 첫 번호는 【기술분야】 바로 아래에 와야 합니다.",
                  "【기술분야】 첫 줄을 [0001] 로 시작하세요."),
    "단락번호": ("문단 번호 이어짐", "[0001], [0002], [0003] … 처럼 빠짐없이 이어져야 합니다.",
              "빠진 번호나 겹친 번호를 찾아 다시 매기세요."),
    "청구범위·요약서 단락번호": ("청구범위엔 문단 번호 없음", "청구범위와 요약서에는 [0001] 같은 번호를 붙이지 않습니다.",
                        "해당 구간의 [ ] 번호를 지우세요."),
    "도면 선언": ("그림 목록 대조", "본문에서 「도 3」을 말했으면 【도면의 간단한 설명】에도 도 3 이 있어야 합니다.",
               "빠진 도면 설명을 추가하거나, 본문의 도면 번호를 고치세요."),
    "대표도": ("대표 그림", "특허 공보 첫 장에 실릴 그림 한 장을 정해야 합니다.",
             "【대표도】 칸에 「도 1」처럼 적으세요."),
    "부호 대조": ("부품 번호 대조", "본문에 (110) 처럼 쓴 번호는 【부호의 설명】에 뜻이 적혀 있어야 합니다.",
               "【부호의 설명】에 빠진 번호와 이름을 추가하세요."),
    "청구항 번호": ("청구항 번호", "청구항은 1, 2, 3 … 순서대로 빠짐없이 매겨야 합니다.",
                "02_청구범위.md 의 【청구항 N】 번호를 순서대로 고치세요."),
    "청구항 인용 정합": ("청구항 참조", "「제1항에 있어서」처럼 앞 항을 가리킬 때, 없는 항이나 뒤 항을 가리키면 안 됩니다.",
                   "인용하는 항 번호를 자기보다 앞 번호로 고치세요."),
    "독립항": ("독립항", "다른 항을 참조하지 않고 홀로 서는 청구항입니다. 권리의 뼈대라 최소 하나는 있어야 합니다.",
             "청구항 1 을 다른 항 인용 없이 쓰세요."),
    "카테고리 명사": ("권리의 종류", "「…장치」「…방법」처럼 무엇을 권리로 삼는지 나타내는 말입니다.",
                 "청구항 1 을 「○○ 장치로서,」 형태로 시작하세요."),
    "청구항 종결": ("청구항 마침표", "청구항은 한 문장이라 마침표로 끝나야 합니다.",
                "각 청구항 끝에 마침표를 찍으세요."),
    "선행기재": ("「상기」 앞말 확인", "「상기 제1 구성부」라고 쓰려면 그 말이 앞에 먼저 나와 있어야 합니다.",
              "앞에서 처음 나올 때는 「상기」를 빼고, 두 번째부터 붙이세요."),
    "카테고리 일원화": ("이름과 권리 종류 일치", "발명의 제목과 청구항의 권리 종류가 같은 말이어야 합니다.",
                  "제목에 청구항 1 의 「○○ 장치」와 같은 말을 넣으세요."),
    "편입분 대조": ("청구범위 두 곳 일치", "명세서 안에 옮겨 둔 청구범위와 원본이 글자 하나까지 같아야 합니다.",
                "02_청구범위.md 만 고치세요. 제출본은 이 프로그램이 다시 맞춥니다."),
    "발명의 명칭 대조": ("제목 세 곳 일치", "제목은 설정 파일·명세서·제목 파일 세 곳에 같게 적혀야 합니다.",
                   "세 곳의 제목을 똑같이 맞추세요."),
    "문체·표기": ("특허청 문체", "특허 문서에는 굵은 글씨·따옴표·목록 기호·「합니다」체를 쓰지 않습니다.",
               "지적된 기호를 지우고 「…한다」체로 고치세요."),
    "제출본 재생성": ("제출본 만들기", "명세서와 청구범위를 합쳐 실제 제출할 원고 한 벌을 만듭니다.",
                 "직접 고치지 말고 이 프로그램이 만들게 두세요."),
    "도면 파일": ("그림 파일", "도면 폴더에 그림 파일이 있는지 봅니다.",
               "도면/ 폴더에 도1.svg 같은 파일을 넣으세요."),
}


def 뜻(검사: str):
    쉬움, 설명, 고치기 = 쉬운말.get(검사, (검사, "", ""))
    return {"쉬움": 쉬움, "설명": 설명, "고치기": 고치기}


# ─────────────────────────────────────────────── 자료 만들기


def 출원건목록(뿌리: Path) -> list[dict]:
    if (뿌리 / "patent_config.json").exists():
        폴더들 = [뿌리]
    else:
        # 깊이를 재지 아니한다. 고른 폴더 아래 어디에 있어도 찾는다.
        # _백업_… 처럼 밑줄로 시작하는 폴더 아래는 출원건이 아니다
        폴더들 = sorted(f for f in {p.parent for p in 뿌리.rglob("patent_config.json")}
                       if not any(이름.startswith("_")
                                  for 이름 in f.relative_to(뿌리).parts))
    목록 = []
    for f in 폴더들:
        cfg = K.config읽기(f)
        발명 = cfg.get("invention") or {}
        출원 = cfg.get("filing") or {}
        목록.append({
            "폴더": str(f),
            "이름": f.name,
            "제목": 발명.get("title_kr") or "(제목 없음)",
            "출원인": ", ".join(a.get("name", "") for a in (cfg.get("applicants") or [])),
            "발명자": ", ".join(v.get("name", "") for v in (cfg.get("inventors") or [])),
            "마감": 출원.get("priority_deadline") or "",
            "도면수": len(list((f / "도면").glob("*.svg"))) if (f / "도면").is_dir() else 0,
            "제출본": (f / "03_제출본_명세서_청구범위.md").exists(),
            "출력물": [x.name for x in sorted((f / "_출력").glob("*"))] if (f / "_출력").is_dir() else [],
        })
    return 목록


def 점검(폴더: Path, 서류만들기: bool) -> dict:
    cfg = K.config읽기(폴더)
    rep = K.출원건처리(폴더, 생성=True)
    항목 = [{"등급": 등급, "검사": 검사, "내용": 내용, **뜻(검사)}
            for 등급, 검사, 내용 in rep.항목]
    만든것, 막힌이유 = [], ""
    if 서류만들기:
        if rep.오류수:
            막힌이유 = "보정할 곳이 남아 서류를 만들지 않았습니다."
        else:
            만든것.append(str(K.출원서요약(폴더, cfg)))
            try:
                만든것.append(str(K.docx만들기(폴더, cfg)))
            except SystemExit as e:
                막힌이유 = str(e)
    return {
        "이름": 폴더.name, "폴더": str(폴더), "항목": 항목,
        "오류": rep.오류수, "경고": rep.경고수,
        "통과": len(rep.항목) - rep.오류수 - rep.경고수,
        "만든것": 만든것, "막힌이유": 막힌이유,
    }


def 폴더고르기(초기: str) -> str:
    """별도 프로세스에서 창을 띄운다. 서버 스레드에서 Tk 를 직접 쓰면 불안정하다."""
    코드 = ("import tkinter as tk;from tkinter import filedialog;"
            "r=tk.Tk();r.withdraw();r.attributes('-topmost',True);"
            f"print(filedialog.askdirectory(initialdir={초기!r}) or '')")
    환경 = {**os.environ, "PYTHONIOENCODING": "utf-8"}   # 한글 경로가 cp949 로 깨지는 것을 막는다
    r = subprocess.run([sys.executable, "-c", 코드], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=환경)
    return (r.stdout or "").strip()


# ─────────────────────────────────────────────── 화면

화면 = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>특허 자동화 킷</title>
<style>
/* 서식의 출처는 특허청 공보다. 표제는 본문 글꼴(바탕), 절 이름은 【 】, 수치는 Consolas. */
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
@media (prefers-color-scheme:dark){:root{
  --paper:#121A1E; --sheet:#182126; --ink:#E3E8E1; --ink2:#9BAAB1; --faint:#6E7F87;
  --rule:#2E3D44; --rule2:#243036;
  --seal:#DE7263; --seal-bg:#2A1512; --seal-line:#5C2A24;
  --stamp:#74B4C4; --stamp-bg:#122A31; --stamp-line:#2A4E58;
  --jade:#5FBE8B; --jade-bg:#0F2419; --jade-line:#265139;
  --amber:#D6A63C; --amber-bg:#251C08; --amber-line:#4E3D14;
}}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.7 var(--sans);
  -webkit-font-smoothing:antialiased}
:focus-visible{outline:2px solid var(--stamp);outline-offset:2px}
.wrap{max-width:1080px;margin:0 auto;padding:0 26px}

/* ── 표제부 ── */
header{border-bottom:3px double var(--rule);background:var(--paper);
  position:sticky;top:0;z-index:9}
.hd{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;
  padding:20px 0 14px;flex-wrap:wrap}
.hd h1{margin:0;font:400 27px/1.25 var(--serif);letter-spacing:.16em}
.hd h1 i{font-style:normal;color:var(--faint);font-size:20px}
.hd p{margin:4px 0 0;font-size:12.5px;color:var(--ink2);letter-spacing:.02em}
.badge{font:12px/1 var(--mono);color:var(--ink2);border:1px solid var(--rule);
  padding:6px 10px;letter-spacing:.04em;white-space:nowrap}

/* ── 안내 ── */
main{padding:26px 0 90px}
.lead{font:400 17px/1.85 var(--serif);letter-spacing:.01em;margin:0 0 30px;
  padding-left:16px;border-left:3px double var(--rule);
  word-break:keep-all;text-wrap:pretty}
.lead b{font-weight:400;color:var(--seal);border-bottom:1px solid var(--seal-line)}

/* ── 절 ── */
section{margin-bottom:34px}
.sec-hd{display:flex;align-items:baseline;gap:11px;margin-bottom:14px;
  border-bottom:1px solid var(--rule);padding-bottom:8px}
.sec-hd h2{margin:0;font:400 17px/1.4 var(--serif);letter-spacing:.1em}
.sec-hd small{color:var(--faint);font-size:12.5px;letter-spacing:.01em}

/* ── 입력·단추 ── */
.row{display:flex;gap:8px;flex-wrap:wrap}
input[type=text]{flex:1;min-width:250px;padding:9px 12px;border:1px solid var(--rule);
  border-radius:2px;font:13px/1.5 var(--mono);background:var(--sheet);color:var(--ink)}
input[type=text]:focus{outline:none;border-color:var(--stamp);
  box-shadow:inset 0 0 0 1px var(--stamp)}
button{padding:9px 17px;border:1px solid var(--rule);background:var(--sheet);color:var(--ink);
  border-radius:2px;font:600 13.5px/1.5 var(--sans);letter-spacing:.02em;cursor:pointer;
  transition:background .12s,border-color .12s,color .12s}
button:hover{border-color:var(--ink2)}
button.p{background:var(--stamp);color:#fff;border-color:var(--stamp)}
button.p:hover{background:var(--ink);border-color:var(--ink)}
button:disabled{opacity:.45;cursor:default}

/* ── 출원건 카드 = 서지사항 표 ── */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:11px}
.case{text-align:left;width:100%;padding:0;border:1px solid var(--rule);border-radius:2px;
  background:var(--sheet);cursor:pointer;font-weight:400;overflow:hidden;
  transition:border-color .12s,box-shadow .12s}
.case:hover{border-color:var(--ink2)}
.case.on{border-color:var(--stamp);box-shadow:inset 0 0 0 1px var(--stamp)}
.case-t{padding:11px 14px;border-bottom:1px solid var(--rule2);
  display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.case-t b{font:400 15px/1.4 var(--serif);letter-spacing:.05em}
.case-t em{font:11px/1 var(--mono);color:var(--faint);font-style:normal;white-space:nowrap}
.case-b{padding:11px 14px}
.case-b p{margin:0 0 9px;font-size:13px;line-height:1.6;color:var(--ink2);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.dl{display:grid;grid-template-columns:auto 1fr;gap:2px 9px;font-size:11.5px}
.dl dt{color:var(--faint);white-space:nowrap;font-family:var(--serif);letter-spacing:.04em}
.dl dd{margin:0;color:var(--ink2);font-family:var(--mono);font-size:11px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* ── 심사 결과 ── */
.res-hd{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;
  flex-wrap:wrap;margin-bottom:16px}
.tot{display:flex;gap:0;border:1px solid var(--rule);border-radius:2px;overflow:hidden;
  background:var(--sheet);flex:1;min-width:290px}
.tile{flex:1;padding:11px 15px;border-right:1px solid var(--rule2);text-align:left}
.tile:last-child{border-right:0}
.tile .n{font:600 25px/1.15 var(--mono);letter-spacing:-.02em}
.tile .t{font:12px/1.4 var(--sans);color:var(--ink2);margin-top:1px}
.t-err .n{color:var(--seal)} .t-warn .n{color:var(--amber)} .t-ok .n{color:var(--jade)}

/* 직인 — 이 화면에서 유일하게 큰 소리를 내는 곳 */
.seal{width:96px;height:96px;flex:none;display:grid;place-items:center;text-align:center;
  border:2.5px solid var(--seal);border-radius:3px;color:var(--seal);
  font:400 25px/1.15 var(--serif);letter-spacing:.02em;transform:rotate(-7deg);
  box-shadow:inset 0 0 0 2px var(--paper),inset 0 0 0 4px var(--seal);
  padding:9px;opacity:.92}
.seal.go{animation:stamp .34s cubic-bezier(.2,1.5,.4,1) both}
.seal.no{border-color:var(--faint);color:var(--faint);box-shadow:inset 0 0 0 2px var(--paper),
  inset 0 0 0 4px var(--faint);opacity:.5;animation:none}
@keyframes stamp{
  0%{transform:rotate(-24deg) scale(2.5);opacity:0;filter:blur(3px)}
  60%{opacity:.98}
  100%{transform:rotate(-7deg) scale(1);opacity:.92;filter:blur(0)}}

/* ── 지적사항 = 통지서 행 ── */
.verdict{font:400 15px/1.7 var(--serif);letter-spacing:.02em;padding:11px 15px;
  border:1px solid var(--rule);border-radius:2px;margin:0 0 16px;background:var(--sheet)}
.verdict.bad{border-color:var(--seal-line);background:var(--seal-bg);color:var(--seal)}
.verdict.good{border-color:var(--jade-line);background:var(--jade-bg);color:var(--jade)}
.item{border:1px solid var(--rule);border-left-width:3px;border-radius:2px;
  padding:13px 16px;margin-bottom:8px;background:var(--sheet)}
.item.오류{border-color:var(--seal-line);border-left-color:var(--seal);background:var(--seal-bg)}
.item.경고{border-color:var(--amber-line);border-left-color:var(--amber);background:var(--amber-bg)}
.item h4{margin:0 0 5px;font:400 15.5px/1.5 var(--serif);letter-spacing:.05em;
  display:flex;align-items:baseline;gap:9px;flex-wrap:wrap}
.tag{font:600 11px/1 var(--sans);letter-spacing:.06em;padding:4px 8px;border-radius:2px;
  flex:none}
.tag.오류{background:var(--seal);color:#fff}
.tag.경고{background:var(--amber);color:#fff}
.tag.통과{background:transparent;color:var(--jade);border:1px solid var(--jade-line);
  font-family:var(--mono);padding:2px 6px}
.item .what{margin:0;font-size:13px;color:var(--ink2)}
.item .msg{margin:8px 0 0;font:12.5px/1.6 var(--mono);padding:8px 11px;
  background:var(--paper);border:1px solid var(--rule2);border-radius:2px;word-break:break-all}
.item .fix{margin:8px 0 0;font-size:12.5px;color:var(--ink)}
.item .fix b{font:400 12px var(--serif);letter-spacing:.08em;color:var(--faint);
  margin-right:7px}

/* ── 적합 목록 ── */
details{border-top:1px solid var(--rule);margin-top:14px}
summary{cursor:pointer;padding:10px 2px;font:400 14px var(--serif);letter-spacing:.06em;
  color:var(--ink2);list-style:none}
summary::-webkit-details-marker{display:none}
summary:before{content:"〉";margin-right:7px;color:var(--faint);display:inline-block;
  transition:transform .15s}
details[open] summary:before{transform:rotate(90deg)}
.ok-line{display:grid;grid-template-columns:44px 190px 1fr;gap:11px;align-items:baseline;
  padding:6px 2px;border-top:1px solid var(--rule2);font-size:13px}
.ok-line b{font:400 13.5px var(--serif);letter-spacing:.03em;font-weight:400}
.ok-line span{color:var(--ink2);font:11.5px/1.6 var(--mono);word-break:break-all}

/* ── 산출물 ── */
.done{border:1px solid var(--jade-line);background:var(--jade-bg);border-radius:2px;
  padding:13px 16px;margin-top:14px;font-size:13.5px}
.done b{font:400 15px var(--serif);letter-spacing:.05em;color:var(--jade)}
.done code{display:inline-block;font:11.5px var(--mono);background:var(--paper);
  padding:3px 8px;border:1px solid var(--jade-line);border-radius:2px;margin-top:5px;
  word-break:break-all}
.done p{margin:9px 0 0;color:var(--ink2);font-size:12.5px}
.done.warn{border-color:var(--amber-line);background:var(--amber-bg)}

.empty{padding:38px 16px;text-align:center;color:var(--faint);font-size:13.5px;
  border:1px dashed var(--rule);border-radius:2px}
.spin{display:inline-block;width:12px;height:12px;border:2px solid var(--rule);
  border-top-color:var(--stamp);border-radius:50%;animation:s .7s linear infinite;
  vertical-align:-1px;margin-right:8px}
@keyframes s{to{transform:rotate(360deg)}}
.hide{display:none}
@media (prefers-reduced-motion:reduce){
  *{animation-duration:.01ms!important;transition-duration:.01ms!important}
  html{scroll-behavior:auto}}
@media (max-width:640px){
  .hd h1{font-size:22px}.lead{font-size:15.5px}
  .ok-line{grid-template-columns:44px 1fr;}.ok-line span{grid-column:2}
  .seal{width:80px;height:80px;font-size:21px}}
</style></head><body>

<header><div class="wrap hd">
  <div>
    <h1>특허 자동화 킷 <i>特許自動化</i></h1>
    <p>임시명세서(가출원) 원고를 검사하고, 특허청에 낼 서류를 만듭니다</p>
  </div>
  <div class="badge" id="ver">內部用 · 提出前 檢査</div>
</div></header>

<main class="wrap">
  <p class="lead">특허를 처음 내시나요. 폴더를 고르고 검사를 누르면
  <b>특허청이 문제 삼을 곳</b>을 미리 찾아 드립니다.<br>
  각 항목마다 무슨 뜻인지와 어떻게 고치는지 함께 적습니다.</p>

  <section>
    <div class="sec-hd"><h2>【1】 원고 폴더</h2><small>특허 원고가 들어 있는 폴더를 고릅니다</small></div>
    <div class="row">
      <input type="text" id="dir" placeholder="폴더 경로" aria-label="원고 폴더 경로">
      <button onclick="찾기()">찾아보기</button>
      <button class="p" onclick="목록()">불러오기</button>
    </div>
  </section>

  <section id="s2">
    <div class="sec-hd"><h2>【2】 출원 건</h2><small>특허 하나가 폴더 하나입니다</small></div>
    <div id="cases" class="grid"></div>
  </section>

  <section id="s3" class="hide">
    <div class="sec-hd"><h2 id="s3t">【3】 심사 결과</h2><small id="s3s"></small></div>
    <div class="row" style="margin-bottom:18px">
      <button class="p" onclick="실행(false)">원고 검사</button>
      <button onclick="실행(true)">검사 후 서류 만들기</button>
      <button onclick="열기()">폴더 열기</button>
    </div>
    <div id="out"></div>
  </section>
</main>

<script>
let 건들=[], 고른=null;
const $=id=>document.getElementById(id);
const 안전=s=>String(s??'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

// 표제부(sticky)가 덮지 아니하도록 그 높이만큼 띄워 세운다
const 보이게=el=>window.scrollTo({
  top: el.getBoundingClientRect().top + window.scrollY
       - document.querySelector('header').offsetHeight - 14});

async function api(길, 몸){
  const r = await fetch(길, 몸?{method:'POST',body:JSON.stringify(몸)}:undefined);
  return r.json();
}

async function 찾기(){
  const r = await api('/api/pick?dir='+encodeURIComponent($('dir').value));
  if(r.폴더){ $('dir').value=r.폴더; 목록(); }
}

async function 목록(조용히){
  if(!조용히) $('cases').innerHTML='<div class="empty"><span class="spin"></span>출원 건을 찾는 중</div>';
  const r = await api('/api/cases?dir='+encodeURIComponent($('dir').value));
  건들 = r.목록||[];
  if(!건들.length){
    $('cases').innerHTML='<div class="empty">이 폴더에는 출원 건이 없습니다.<br>'+
      'patent_config.json 파일이 있는 폴더를 고르세요.</div>';
    $('s3').classList.add('hide'); return;
  }
  $('cases').innerHTML = 건들.map((c,i)=>`
    <button class="case" id="c${i}" onclick="고르기(${i})">
      <div class="case-t"><b>${안전(c.이름)}</b>
        <em>${c.제출본?'제출본 有':'제출본 無'}</em></div>
      <div class="case-b">
        <p>${안전(c.제목)}</p>
        <dl class="dl">
          <dt>【발명자】</dt><dd>${안전(c.발명자)||'미정'}</dd>
          <dt>【도　면】</dt><dd>${c.도면수}매</dd>
          ${c.마감?`<dt>【마　감】</dt><dd>${안전(c.마감)}</dd>`:''}
          ${c.출력물.length?`<dt>【산출물】</dt><dd>${c.출력물.length}건</dd>`:''}
        </dl>
      </div>
    </button>`).join('');
}

function 고르기(i){
  고른=i;
  건들.forEach((_,j)=>$('c'+j).classList.toggle('on',i===j));
  $('s3').classList.remove('hide');
  $('s3t').textContent = '【3】 심사 결과';
  $('s3s').textContent = 건들[i].이름;
  $('out').innerHTML='<div class="empty">위 단추를 눌러 검사를 시작하세요.</div>';
  보이게($('s3'));
}

async function 실행(서류){
  if(고른===null) return;
  const 이름 = 건들[고른].이름, 칸 = $('out');
  칸.style.minHeight = 칸.offsetHeight + 'px';   // 줄었다 늘며 화면이 튀는 것을 막는다
  칸.innerHTML='<div class="empty"><span class="spin"></span>원고를 검사하는 중</div>';
  const r = await api('/api/run',{폴더:건들[고른].폴더, 서류:서류});
  칸.style.minHeight='';
  if(r.오류메시지){
    칸.innerHTML='<div class="empty">'+안전(r.오류메시지)+'</div>'; 보이게(칸); return;
  }
  그리기(r);
  await 목록(true);                   // 격자를 비우지 아니한 채 새로 고친다
  const j = 건들.findIndex(c=>c.이름===이름);
  if(j>=0){ 고른=j; $('c'+j).classList.add('on'); }   // 고른 표시를 되살린다
  보이게($('out'));                    // 높이가 다 잡힌 뒤에 자리를 잡는다
}

function 그리기(r){
  const 나쁨 = r.항목.filter(x=>x.등급!=='통과');
  const 좋음 = r.항목.filter(x=>x.등급==='통과');
  const 적합 = r.오류===0;

  let h = `<div class="res-hd">
    <div class="tot">
      <div class="tile t-err"><div class="n">${r.오류}</div><div class="t">보정 필요</div></div>
      <div class="tile t-warn"><div class="n">${r.경고}</div><div class="t">확인 권장</div></div>
      <div class="tile t-ok"><div class="n">${r.통과}</div><div class="t">적합</div></div>
    </div>
    <div class="seal ${적합?'go':'no'}">${적합?'出願<br>適格':'補正<br>要求'}</div>
  </div>`;

  h += 적합
    ? `<p class="verdict good">출원을 막는 결함이 확인되지 아니합니다. 「검사 후 서류 만들기」를 누르면 제출용 파일이 나옵니다.</p>`
    : `<p class="verdict bad">아직 특허청에 낼 수 없습니다. 아래 「보정 필요」 ${r.오류}건을 고친 뒤 다시 검사하세요.</p>`;

  h += 나쁨.map(x=>`<div class="item ${x.등급}">
      <h4><span class="tag ${x.등급}">${x.등급==='오류'?'보정 필요':'확인 권장'}</span>${안전(x.쉬움)}</h4>
      <p class="what">${안전(x.설명)}</p>
      <p class="msg">${안전(x.내용)}</p>
      ${x.고치기?`<p class="fix"><b>보정 방법</b>${안전(x.고치기)}</p>`:''}
    </div>`).join('');

  if(좋음.length) h += `<details><summary>적합 항목 ${좋음.length}건 보기</summary>`+
    좋음.map(x=>`<div class="ok-line"><span class="tag 통과">適</span>
      <b>${안전(x.쉬움)}</b><span>${안전(x.내용)}</span></div>`).join('')+`</details>`;

  if(r.만든것.length) h += `<div class="done"><b>서류를 만들었습니다</b><br>`+
    r.만든것.map(p=>`<code>${안전(p)}</code>`).join('<br>')+
    `<p>이 내용을 특허로 전자출원(KIPOnet) 서식에 옮겨 적으면 됩니다.
     공지예외를 주장했다면 출원일부터 30일 안에 증명서류를 내세요.</p></div>`;
  if(r.막힌이유) h += `<div class="done warn"><b>서류를 만들지 못했습니다</b>
    <p>${안전(r.막힌이유)}</p></div>`;

  $('out').innerHTML = h;
}

function 열기(){ if(고른!==null) api('/api/open',{폴더:건들[고른].폴더}); }

fetch('/api/cwd').then(r=>r.json()).then(r=>{
  $('dir').value=r.폴더; $('ver').textContent='특허 자동화 킷 '+r.버전; 목록();});
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
        질의 = parse_qs(길.query)
        if 길.path in ("/", "/index.html"):
            return self.보냄(화면, "text/html")
        if 길.path == "/api/cwd":
            return self.보냄({"폴더": str(Path.cwd()), "버전": K.버전})
        if 길.path == "/api/pick":
            return self.보냄({"폴더": 폴더고르기(질의.get("dir", [""])[0])})
        if 길.path == "/api/cases":
            뿌리 = Path(질의.get("dir", ["."])[0])
            if not 뿌리.is_dir():
                return self.보냄({"오류메시지": "그런 폴더가 없습니다", "목록": []})
            return self.보냄({"목록": 출원건목록(뿌리)})
        self.send_error(404)

    def do_POST(self):
        몸 = json.loads(self.rfile.read(int(self.headers["Content-Length"] or 0)) or b"{}")
        폴더 = Path(몸.get("폴더", ""))
        if self.path == "/api/run":
            try:
                return self.보냄(점검(폴더, bool(몸.get("서류"))))
            except Exception as e:
                return self.보냄({"오류메시지": f"{type(e).__name__}: {e}"})
        if self.path == "/api/open":
            subprocess.Popen(["explorer", str(폴더)] if sys.platform == "win32"
                             else ["open", str(폴더)])
            return self.보냄({"열림": True})
        self.send_error(404)


def 자가점검():
    """목록·점검이 실제 출원건 폴더에서 자료를 뽑는지 본다."""
    뿌리 = Path.cwd()
    목록 = 출원건목록(뿌리)
    assert isinstance(목록, list), 목록
    assert all({"폴더", "이름", "제목"} <= set(c) for c in 목록)
    if 목록:
        r = 점검(Path(목록[0]["폴더"]), 서류만들기=False)
        assert r["오류"] + r["경고"] + r["통과"] == len(r["항목"])
        assert all(x["쉬움"] for x in r["항목"]), "쉬운말 사전에 없는 검사 이름이 있다"
        print(f"자가점검 통과 · 출원건 {len(목록)}건 · 항목 {len(r['항목'])}개")
    else:
        print("자가점검 통과 · 이 폴더에는 출원건이 없다")


def main():
    if "--자가점검" in sys.argv or "--test" in sys.argv:
        return 자가점검()
    서버 = ThreadingHTTPServer(("127.0.0.1", 0), 처리기)
    주소 = f"http://127.0.0.1:{서버.server_address[1]}/"
    print(f"특허 자동화 킷 {K.버전} — 창을 띄웁니다: {주소}\n  이 창을 닫으면 프로그램이 꺼집니다. (Ctrl+C)")
    threading.Timer(0.4, lambda: webbrowser.open(주소)).start()
    try:
        서버.serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")


if __name__ == "__main__":
    main()
