# -*- coding: utf-8 -*-
"""메인보드에 우리 옷을 입힌다 — 색만 바꾼다.

    python 메인보드_옷.py         입힌다
    python 메인보드_옷.py --벗기기  원래대로 되돌린다

특허킷 2.7.0 은 팀원이 만든 것이고 우리가 고쳐 쓰는 것이 아니다. 다만 안내 화면과
메인보드를 오가는 사람에게 둘이 딴 프로그램으로 보이면 헷갈린다. 그래서 **색 토큰만**
같은 값으로 맞춘다. 짜임새도 글도 기능도 건드리지 아니한다.

○ 팀원이 2.8.0 을 내면 이 옷은 사라진다. 그때 이것을 한 번 더 돌리면 된다.
○ 원본은 dashboard.html.민낯 으로 남긴다.
"""
from __future__ import annotations

import pathlib
import re
import sys

표식 = "/* 출원도우미 옷 */"

# 안내 화면과 같은 값이다. 남색은 관청, 초록은 됨, 붉은색은 막힘
밝은옷 = """--ground:#F4F6F8; --panel:#FFFFFF; --panel2:#F8FAFC; --panel3:#EEF1F5;
    --ink:#0F172A; --ink-soft:#475569; --ink-faint:#64748B;
    --rule:#DDE3EA; --rule-firm:#C3CCD6;
    --seal:#B91C1C; --seal-wash:#FBEBEB;
    --pass:#047857; --pass-wash:#E7F3EE;
    --warn:#92600B; --warn-wash:#FBF2E0;
    --code-ground:#1E3A5F; --code-ink:#E8EDF3"""

어두운옷 = """--ground:#0D1520; --panel:#141E2B; --panel2:#182434; --panel3:#1E2C3E;
    --ink:#E8EDF3; --ink-soft:#A3B2C2; --ink-faint:#7A8B9D;
    --rule:#26364A; --rule-firm:#36495F;
    --seal:#F08D8D; --seal-wash:#2A1416;
    --pass:#5FBF9C; --pass-wash:#0F2620;
    --warn:#E0BC6E; --warn-wash:#2A2213;
    --code-ground:#0A1119; --code-ink:#D7E0EA"""


def 자리찾기() -> pathlib.Path:
    import patentkit
    return pathlib.Path(patentkit.__file__).parent / "자료" / "dashboard.html"


def 입히기(f: pathlib.Path) -> str:
    민낯 = f.with_suffix(".html.민낯")
    글 = f.read_text(encoding="utf-8")
    if 표식 in 글:
        글 = 민낯.read_text(encoding="utf-8") if 민낯.exists() else 글
    elif not 민낯.exists():
        민낯.write_text(글, encoding="utf-8")

    센 = 0

    def 갈기(m):
        nonlocal 센
        앞 = m.group(1)
        어두우냐 = "data-theme" in 앞 or "prefers-color-scheme" in 앞
        센 += 1
        return f"{앞}{표식}\n    {어두운옷 if 어두우냐 else 밝은옷}}}"

    새 = re.sub(r"(:root[^{]*\{)[^}]*\}", 갈기, 글, count=2)
    if 센 == 0:
        raise SystemExit("dashboard.html 에서 :root 토큰을 찾지 못하였다. 판이 바뀐 듯하다.")
    f.write_text(새, encoding="utf-8")
    return f"{센}개 토큰 묶음에 옷을 입혔다"


def 벗기기(f: pathlib.Path) -> str:
    민낯 = f.with_suffix(".html.민낯")
    if not 민낯.exists():
        return "민낯이 없다. 이미 원본이다"
    f.write_text(민낯.read_text(encoding="utf-8"), encoding="utf-8")
    민낯.unlink()
    return "원래대로 되돌렸다"


def main() -> int:
    f = 자리찾기()
    if not f.exists():
        print(f"메인보드를 찾지 못하였다: {f}\n  먼저 특허킷을 깐다.")
        return 1
    print(f"자리 — {f}")
    print("  " + (벗기기(f) if "--벗기기" in sys.argv else 입히기(f)))
    print("  메인보드를 새로 띄우면 보인다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
