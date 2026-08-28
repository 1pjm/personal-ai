# -*- coding: utf-8 -*-
"""출원 도우미 — 명세서가 다 되었을 때부터 관청에 내기까지를 한 번에 끌고 간다.

    python 출원도우미.py 준비 <출원건폴더|상위폴더>
    python 출원도우미.py 추적 1020260142020

킷(patentkit 2.7.0)이 원고를 보고, 이 도우미가 그 뒤를 본다.
수수료를 셈하고, 사전등록이 되었는지 묻고, 특허로의 어느 자리로 가야 하는지 짚는다.

○ 관청 제출 자체는 하지 아니한다. 특허청은 제출용 공개 API 를 두고 있지 아니하며,
  제출은 공동인증서로 서명하는 법률행위다(특허법 제28조의3, 시행규칙 제9조의6).
  마지막 서명과 결제는 사람이 누른다. 그 직전까지를 이 도우미가 만든다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import webbrowser
from pathlib import Path

버전 = "1.0"

# ─────────────────────────────────────────────── 관청 자리 (실측 확인 2026-08-28)

특허로 = {
    "메인": "https://www.patent.go.kr",
    "고객번호": "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=14300000032",
    "서식작성": "https://www.patent.go.kr/smart/jsp/kiponet/ma/websolution/OnlineWrite.do",
    "전자출원SW": "https://patent.go.kr/smart/jsp/kiponet/ir/pctinfo/PctOnlineInstall.do",
    "수수료": "https://www.patent.go.kr/smart/jsp/ka/menu/fee/main/FeeMain01.do",
}

# ─────────────────────────────────────────────── 수수료
# 출처: 특허로 수수료정보안내 (특허료 등의 징수규칙). 2026-08-28 확인.
# 금액은 규칙 개정으로 바뀐다. 결제 직전 화면의 금액이 정본이다.

출원료 = {"전자_국어": 46_000, "전자_외국어": 73_000,
          "서면_국어": 66_000, "서면_외국어": 93_000}
면가산 = 1_000          # 명세서·도면·요약서 합계 20면 초과 1면마다
면기준 = 20
심사청구_기본 = 166_000
심사청구_항당 = 51_000
감면표 = {"개인": 0.70, "중소기업": 0.70, "소기업": 0.70,
          "학생": 1.00, "만18세이하": 1.00, "없음": 0.0}


def 감면율(설명: str) -> tuple[float, str]:
    """설정의 fee_reduction 글월에서 감면율을 읽는다. 못 읽으면 0 이다."""
    if not 설명:
        return 0.0, "감면 없음"
    m = re.search(r"(\d{1,3})\s*%", 설명)
    if m:
        비 = int(m.group(1)) / 100
        return min(비, 1.0), 설명
    for 이름, 비 in 감면표.items():
        if 이름 in 설명.replace(" ", ""):
            return 비, 설명
    return 0.0, f"{설명} (감면율을 읽지 못하였다)"


def 면수추정(폴더: Path) -> int:
    """제출본 글자수로 면수를 어림한다. 정확한 면수는 관청 서식이 정한다.

    특허 명세서 한 면은 대략 1,000자 안팎이다. 도면은 한 장이 한 면이다.
    ponytail: 글자수 어림. 정확한 값이 필요하면 제출용 파일의 면수를 쓴다
    """
    제출본 = 폴더 / "03_제출본_명세서_청구범위.md"
    글자 = len(제출본.read_text(encoding="utf-8")) if 제출본.exists() else 0
    도면 = 폴더 / "도면"
    장 = len({f.stem for f in 도면.glob("*.svg")}) if 도면.is_dir() else 0
    return max(1, round(글자 / 1000)) + 장


def 수수료셈(폴더: Path, cfg: dict) -> dict:
    출원 = cfg.get("filing") or {}
    외국어 = bool(출원.get("foreign_language"))
    기본 = 출원료["전자_외국어" if 외국어 else "전자_국어"]
    면 = 면수추정(폴더)
    가산 = max(0, 면 - 면기준) * 면가산
    비, 설명 = 감면율(출원.get("fee_reduction", ""))
    합 = 기본 + 가산
    return {
        "기본": 기본, "면수": 면, "가산": 가산, "합계": 합,
        "감면율": 비, "감면설명": 설명,
        "감면액": round(합 * 비), "실납부": round(합 * (1 - 비)),
        "심사청구_참고": 심사청구_기본 + 심사청구_항당 * len(청구항수(폴더)),
    }


def 청구항수(폴더: Path) -> list[int]:
    f = 폴더 / "02_청구범위.md"
    if not f.exists():
        return []
    본문 = f.read_text(encoding="utf-8").split("## 회피 논거")[0]
    return sorted({int(n) for n in re.findall(r"【청구항\s*(\d+)】", 본문)})


# ─────────────────────────────────────────────── 사전등록 (1회성)

사전등록 = [
    ("특허고객번호(출원인코드) 부여신청", "applicants.0.customer_no",
     "특허법 제28조의2제1항 · 시행규칙 제9조", "고객번호"),
    ("전자문서 이용신고", "filing.edoc_reported",
     "특허법 제28조의4제1항", "메인"),
    ("인증서 발급 및 사용등록", "filing.cert_registered",
     "특허법 시행규칙 제9조의6", "메인"),
]


def 설정값(cfg: dict, 길: str):
    값 = cfg
    for k in 길.split("."):
        if isinstance(값, list):
            값 = 값[int(k)] if k.isdigit() and int(k) < len(값) else None
        elif isinstance(값, dict):
            값 = 값.get(k)
        else:
            return None
        if 값 is None:
            return None
    return 값


def 사전등록점검(cfg: dict) -> list[tuple[str, bool, str, str, str]]:
    낸 = []
    for 이름, 길, 근거, 자리 in 사전등록:
        값 = 설정값(cfg, 길)
        됨 = bool(값) and "★" not in str(값)
        낸.append((이름, 됨, str(값) if 됨 else "미확인", 근거, 특허로[자리]))
    return 낸


# ─────────────────────────────────────────────── 킷 부르기


def 킷(*인자, 폴더: Path | None = None) -> tuple[int, str]:
    명 = [sys.executable, "-m", "patentkit", *인자]
    r = subprocess.run(명, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       cwd=str(폴더) if 폴더 else None)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ─────────────────────────────────────────────── 준비


def 준비(뿌리: Path, 열기: bool) -> int:
    건들 = ([뿌리] if (뿌리 / "patent_config.json").exists()
            else sorted(p.parent for p in 뿌리.rglob("patent_config.json")
                        if not any(x.startswith("_") for x in
                                   p.parent.relative_to(뿌리).parts)))
    if not 건들:
        print("출원건을 찾지 못하였다. patent_config.json 이 있는 폴더를 주어라.")
        return 1

    막힘 = 0
    for 건 in 건들:
        cfg = json.loads((건 / "patent_config.json").read_text(encoding="utf-8"))
        print(f"\n■ {건.name}")

        for 단계, 인자 in (("제출본", ("build",)), ("도면", ("figures",)),
                          ("검사", ("validate",)), ("서식", ("docx",))):
            코드, 글 = 킷(*인자, str(건))
            표 = "OK" if 코드 == 0 else "막힘"
            줄 = [l.strip() for l in 글.splitlines() if "[오류]" in l]
            print(f"  {표:<4} {단계}" + (f" — {줄[0][:70]}" if 줄 else ""))
            if 코드 != 0 and 단계 == "검사":
                막힘 += 1
                break

        낸 = 사전등록점검(cfg)
        수 = 수수료셈(건, cfg)
        글 = 문서(건, cfg, 낸, 수, 막힘 == 0)
        출력 = 건 / "_출력"
        출력.mkdir(exist_ok=True)
        길 = 출력 / "출원_준비.md"
        길.write_text(글, encoding="utf-8")
        print(f"  OK   준비서 — {길.relative_to(건)}")
        print(f"       수수료 {수['실납부']:,}원 "
              f"(기본 {수['기본']:,} + 가산 {수['가산']:,} − 감면 {수['감면액']:,})")
        안된 = [n for n, 됨, *_ in 낸 if not 됨]
        if 안된:
            print(f"  확인 사전등록 {len(안된)}건 미확인 — {', '.join(안된)}")

    if 열기 and 건들:
        webbrowser.open(특허로["서식작성"])
    return 1 if 막힘 else 0


def 문서(건: Path, cfg: dict, 낸, 수: dict, 성함: bool) -> str:
    발명 = cfg.get("invention") or {}
    출원 = cfg.get("filing") or {}
    항 = 청구항수(건)
    마감 = 출원.get("priority_deadline") or ""
    남 = ""
    try:
        남 = f" (D-{(dt.date.fromisoformat(마감) - dt.date.today()).days})"
    except ValueError:
        pass

    ㄱ = [f"# 출원 준비 — {건.name}", "",
          f"작성 {dt.date.today().isoformat()} · 출원 도우미 {버전}", "",
          f"판정 — **{'제출 가능' if 성함 else '보정 필요 (원고에 오류가 남아 있다)'}**", "",
          "## 1. 사전등록 — 처음 한 번만 한다", "",
          "| 할 일 | 상태 | 값 | 근거 |", "| --- | --- | --- | --- |"]
    for 이름, 됨, 값, 근거, 자리 in 낸:
        ㄱ.append(f"| [{이름}]({자리}) | {'완료' if 됨 else '**미확인**'} | {값} | {근거} |")

    ㄱ += ["", "## 2. 수수료 (추정)", "",
           "| 항목 | 금액 |", "| --- | --- |",
           f"| 기본 출원료 (전자·국어) | {수['기본']:,}원 |",
           f"| 면수 가산 ({수['면수']}면 · {면기준}면 초과분) | {수['가산']:,}원 |",
           f"| 감면 ({수['감면설명']}) | −{수['감면액']:,}원 |",
           f"| **실납부** | **{수['실납부']:,}원** |", "",
           f"○ 면수는 제출본 글자수로 어림한 값이다. 정확한 금액은 결제 직전 화면이 정본이다.",
           f"○ 심사청구료는 별도이며 출원일부터 3년 안에 낸다. "
           f"지금 청구항 {len(항)}항 기준 {수['심사청구_참고']:,}원 (감면 전).",
           f"○ 요율 출처: [특허로 수수료정보안내]({특허로['수수료']})", "",
           "## 3. 제출 차례", "",
           "| # | 할 일 | 값 |", "| --- | --- | --- |",
           f"| 1 | [전자출원 SW 설치]({특허로['전자출원SW']}) — NK-Editor · NKEAPS | 최초 1회 |",
           f"| 2 | NK-Editor 로 원고를 넣고 「도구 → 제출파일 생성」 | `_출력/{docx이름(건)}` → `.HLZ` |",
           f"| 3 | NKEAPS 로 출원서 서식 작성 | 아래 4장의 값 |",
           f"| 4 | 도면 첨부 | {도면수(건)}매 |",
           f"| 5 | 청구항 수 확인 | {len(항)}항 |",
           f"| 6 | 공지예외 주장 칸 | {공지문(출원)} |",
           f"| 7 | [특허로 온라인 제출]({특허로['서식작성']}) — 인증서 서명 | **사람이 누른다** |",
           f"| 8 | 수수료 결제 | {수['실납부']:,}원 |",
           f"| 9 | 접수증·출원번호 통지서 수령 | 접수와 동시 |",
           f"| 10 | 공지예외 증명서류 제출 | 출원일부터 30일 이내 |", ""]
    if 마감:
        ㄱ.append(f"○ 우선일 마감 {마감}{남}")
    ㄱ += ["", "## 4. 서식에 옮겨 적을 값", "",
           "| 항목 | 값 |", "| --- | --- |",
           f"| 발명의 명칭 | {발명.get('title_kr','')} |",
           f"| 영문 명칭 | {발명.get('title_en','')} |",
           f"| 출원 종류 | {출원.get('kind','')} |",
           f"| IPC | {' · '.join(cfg.get('ipc') or [])} |"]
    for a in cfg.get("applicants") or []:
        ㄱ.append(f"| 출원인 | {a.get('name','')} · {a.get('biz_no','')} "
                  f"· 고객번호 {a.get('customer_no','미확인')} |")
    for v in cfg.get("inventors") or []:
        ㄱ.append(f"| 발명자 | {v.get('name','')} |")
    ㄱ += ["", "## 5. 출원 뒤", "",
           "출원번호를 받으면 진행 상황을 자동으로 본다.", "",
           "```", "python 출원도우미.py 추적 <출원번호>", "```", "",
           "---", "",
           "관청 제출은 공동인증서로 서명하는 법률행위다(특허법 제28조의3, 시행규칙 제9조의6).",
           "특허청은 제출용 공개 API 를 두고 있지 아니하다. 7·8번은 사람이 누른다.", ""]
    return "\n".join(ㄱ)


def docx이름(건: Path) -> str:
    낸 = sorted((건 / "_출력").glob("*.docx")) if (건 / "_출력").is_dir() else []
    return 낸[-1].name if 낸 else "임시명세서.docx"


def 도면수(건: Path) -> int:
    d = 건 / "도면"
    return len({f.stem for f in d.glob("*.svg")}) if d.is_dir() else 0


def 공지문(출원: dict) -> str:
    공 = 출원.get("disclosure_exception") or {}
    return f"예 · 공개일 {공.get('date','')}" if 공.get("claimed") else "아니오"


# ─────────────────────────────────────────────── 추적


def 추적(번호: str) -> int:
    """출원번호로 진행 상황을 본다. KIPRIS 열쇠가 있어야 한다."""
    코드, 글 = 킷("kipris")
    if 코드 != 0:
        print("KIPRIS 열쇠가 없다. 「python -m patentkit kipris」 로 받는 방법을 본다.")
        return 1
    print(f"출원번호 {번호} — KIPRIS 서지상세를 부른다.\n")
    코드, 글 = 킷("prior-art", "--application", 번호)
    print(글[:2000] if 글.strip() else
          "킷의 prior-art 로는 서지상세를 바로 뽑지 못한다. "
          "korean-patent MCP 의 get_patent_detail 을 쓰거나 KIPRIS 화면에서 본다.")
    return 코드


# ─────────────────────────────────────────────── 들머리


def main() -> int:
    ㅍ = argparse.ArgumentParser(description=f"출원 도우미 {버전}")
    하 = ㅍ.add_subparsers(dest="명령", required=True)
    ㄱ = 하.add_parser("준비", help="검사·제출본·도면·서식을 만들고 출원 준비서를 뽑는다")
    ㄱ.add_argument("폴더", nargs="?", default=".")
    ㄱ.add_argument("--열기", action="store_true", help="특허로를 브라우저로 연다")
    ㄴ = 하.add_parser("추적", help="출원번호로 진행 상황을 본다")
    ㄴ.add_argument("번호")
    ㅁ = ㅍ.parse_args()
    if ㅁ.명령 == "준비":
        return 준비(Path(ㅁ.폴더).resolve(), ㅁ.열기)
    return 추적(ㅁ.번호)


if __name__ == "__main__":
    sys.exit(main())
