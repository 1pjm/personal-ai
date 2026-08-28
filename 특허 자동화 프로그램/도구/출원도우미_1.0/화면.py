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
import os
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
보드꾼 = None          # 그 프로세스. 폴더가 바뀌면 다시 띄운다
적바림 = Path.home() / ".patentkit-helper.json"   # ASCII 이름. 한글은 탈이 잦다


def 적바림읽기() -> dict:
    try:
        return json.loads(적바림.read_text(encoding="utf-8"))
    except Exception:
        return {}


def 적바림쓰기(**바꿈) -> None:
    낸 = 적바림읽기()
    낸.update(바꿈)
    try:
        적바림.write_text(json.dumps(낸, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def 열쇠올리기() -> bool:
    """적바림의 KIPRIS 열쇠를 환경변수로 올린다.

    열쇠를 patent_config.json 에 두지 아니한다. 그 파일은 배포 묶음에 실려
    사외로 나간다. 적바림은 사용자 집 폴더에 있고 어디로도 따라가지 아니한다.
    """
    열쇠 = (적바림읽기().get("열쇠") or "").strip()
    if 열쇠 and not os.environ.get("KIPRIS_KEY"):
        os.environ["KIPRIS_KEY"] = 열쇠
    return bool(os.environ.get("KIPRIS_KEY"))


def 최근읽기() -> list[str]:
    return [x for x in (적바림읽기().get("최근") or []) if Path(x).is_dir()][:8]


def 최근적기(폴더: Path) -> None:
    적바림쓰기(최근=([str(폴더)] + [x for x in 최근읽기() if x != str(폴더)])[:8])


def 폴더고르기(처음: str) -> str:
    """따로 프로세스를 띄운다. 서버 갈래에서 Tk 를 바로 쓰면 흔들린다."""
    코드 = ("import tkinter as tk;from tkinter import filedialog;"
            "r=tk.Tk();r.withdraw();r.attributes('-topmost',True);"
            f"print(filedialog.askdirectory(initialdir={처음!r}) or '')")
    환경 = {**os.environ, "PYTHONIOENCODING": "utf-8"}   # 한글 경로가 깨지는 것을 막는다
    r = subprocess.run([sys.executable, "-c", 코드], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=환경)
    return (r.stdout or "").strip()


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
        "출원번호": (출원.get("application_number") or ""),
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


# ─────────────────────────────────────────────── 진행 상황

기한표 = [
    (30, "공지예외 증명서류", "특허법 제30조제2항",
     "발명을 미리 공개한 적이 있으면 이것을 내야 그 공개가 없던 것으로 다뤄집니다. "
     "넘기면 되돌릴 수 없습니다."),
    (365, "정식 명세서로 바꾸기", "특허법 제42조의2제2항",
     "임시명세서(가출원)로 냈다면 1년 안에 정식 명세서를 내야 합니다."),
    (365 * 3, "심사청구", "특허법 제59조제2항",
     "3년 안에 청구하지 아니하면 취하한 것으로 봅니다."),
]


def 진행받기(번호: str) -> dict:
    """출원번호로 관청 서지를 받고 기한을 셈한다."""
    import datetime as dt
    from patentkit import kipris as K
    if not 열쇠올리기():
        return {"잘못": "열쇠없음"}
    try:
        r = K.상세받기(번호, K.열쇠찾기())
    except Exception as e:
        return {"잘못": f"{type(e).__name__}: {e}"}

    오늘 = dt.date.today()
    기한 = []
    try:
        출원일 = dt.date.fromisoformat(r.get("출원일") or "")
    except ValueError:
        출원일 = None
    for 날수, 이름, 근거, 풀이 in 기한표:
        칸 = {"이름": 이름, "근거": 근거, "풀이": 풀이, "날": "", "남음": None}
        if 출원일:
            그날 = 출원일 + dt.timedelta(days=날수)
            칸["날"] = 그날.isoformat()
            칸["남음"] = (그날 - 오늘).days
        기한.append(칸)

    return {
        "명칭": r.get("명칭", ""), "출원번호": r.get("출원번호", ""),
        "출원일": r.get("출원일", ""), "공개번호": r.get("공개번호", ""),
        "공개일": r.get("공개일", ""), "등록번호": r.get("등록번호", ""),
        "등록일": r.get("등록일", ""), "법적상태": r.get("법적상태", ""),
        "청구항수": r.get("청구항수", 0), "받은때": r.get("받은때", ""),
        "기한": 기한,
    }


# ─────────────────────────────────────────────── 화면

자리 = Path(__file__).resolve().parent


def 화면파일(이름: str) -> tuple[bytes, str]:
    """화면 자료를 그때그때 읽는다. 고치고 새로고침만 하면 바로 보인다."""
    갈래 = {"html": "text/html", "js": "text/javascript", "css": "text/css"}
    끝 = 이름.rsplit(".", 1)[-1]
    return ((자리 / 이름).read_bytes(), f"{갈래.get(끝, 'text/plain')}; charset=utf-8")


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

    def 파일보냄(self, 이름: str):
        try:
            몸, 형식 = 화면파일(이름)
        except OSError:
            return self.send_error(404)
        self.send_response(200)
        self.send_header("Content-Type", 형식)
        self.send_header("Content-Length", str(len(몸)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(몸)

    def do_GET(self):
        길 = urlparse(self.path)
        물 = parse_qs(길.query)
        if 길.path in ("/", "/index.html", "/화면.html"):
            return self.파일보냄("화면.html")
        if 길.path in ("/화면.js", "/%ED%99%94%EB%A9%B4.js"):
            return self.파일보냄("화면.js")
        if 길.path == "/api/start":
            return self.보냄({"버전": D.버전, "보드": 보드주소, "열쇠": 열쇠올리기(),
                            "폴더": str(뿌리), "최근": 최근읽기(),
                            "건들": [한건(g) for g in 출원건들()]})
        if 길.path == "/api/track":
            번호 = re.sub(r"[^0-9]", "", 물.get("no", [""])[0])
            if len(번호) < 10:
                return self.보냄({"잘못": "출원번호는 숫자 13자리입니다 (예 1020260142020)"})
            return self.보냄(진행받기(번호))
        if 길.path == "/api/pick":
            return self.보냄({"폴더": 폴더고르기(물.get("dir", [str(뿌리)])[0])})
        if 길.path == "/api/check":
            건 = 출원건들()[int(물.get("i", ["0"])[0])]
            r = 검사(건)
            return self.보냄({"성함": r["성함"],
                            "오류": [풀이(x) for x in r["오류"]],
                            "경고": [풀이(x) for x in r["경고"]]})
        self.send_error(404)

    def do_POST(self):
        global 뿌리
        몸 = json.loads(self.rfile.read(int(self.headers["Content-Length"] or 0)) or b"{}")
        건들 = 출원건들()
        건 = 건들[int(몸.get("i", 0))] if 건들 else 뿌리
        if self.path == "/api/build":
            줄 = []
            성함 = True
            for 이름, 인자 in (("제출본", "build"), ("도면", "figures"),
                             ("검사", "validate"), ("서식(DOCX)", "docx")):
                코드, 글 = D.킷(인자, str(건))
                if 코드 == 0:
                    줄.append({"ok": True, "글": f"{이름} — 만들었습니다"})
                else:
                    첫 = next((l.strip() for l in 글.splitlines() if "[오류]" in l), "")
                    풀 = 풀이(첫) if 첫 else {"뜻": "만들지 못했습니다", "방법": "", "원문": ""}
                    줄.append({"ok": False, "글": f"{이름} — {풀['뜻']}",
                               "방법": 풀["방법"], "원문": 풀["원문"]})
                if 코드 != 0 and 인자 == "validate":
                    성함 = False
                    break
            D.준비(건, False)
            return self.보냄({"성함": 성함, "줄": 줄, "건": 한건(건)})
        if self.path == "/api/key":
            적바림쓰기(열쇠=(몸.get("열쇠") or "").strip())
            os.environ.pop("KIPRIS_KEY", None)
            return self.보냄({"있음": 열쇠올리기()})
        if self.path == "/api/chdir":
            새 = Path(몸.get("폴더", "")).expanduser()
            if not 새.is_dir():
                return self.보냄({"잘못": "그런 폴더가 없습니다", "건들": []})
            뿌리 = 새.resolve()
            건들 = 출원건들()
            if 건들:
                최근적기(뿌리)
                threading.Thread(target=보드띄우기, args=(뿌리,), daemon=True).start()
            return self.보냄({"폴더": str(뿌리), "최근": 최근읽기(),
                            "건들": [한건(g) for g in 건들]})
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
    global 보드주소, 보드꾼
    보드주소 = ""
    if 보드꾼 and 보드꾼.poll() is None:
        보드꾼.terminate()
    try:
        p = 보드꾼 = subprocess.Popen([sys.executable, "-m", "patentkit", "web", str(폴더),
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
    if 출원건들():
        최근적기(뿌리)
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
