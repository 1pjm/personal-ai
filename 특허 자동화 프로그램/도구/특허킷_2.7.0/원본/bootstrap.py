# -*- coding: utf-8 -*-
"""설치 도우미 — 받는 사람 컴퓨터에 킷을 앉힌다.

설치.bat 이 파이썬을 찾아 이 파일을 부른다. 여기서 하는 일은 셋이다.
  1. 프로그램 전용 파이썬 자리(venv)를 %LOCALAPPDATA%\\Programs\\PatentKit\\venv 에 만든다.
  2. 함께 들어 있는 wheels 폴더의 꾸러미를 그 자리에 넣는다(인터넷이 없어도 된다).
  3. 넣은 킷의 install 명령을 불러 바탕화면 아이콘과 PATH 를 잡는다.

표준 라이브러리만 쓴다. 실행 파일을 새로 굽지 않으므로 윈도우의 앱 제어 정책
(Smart App Control)에 걸리지 않는다. 회사 PC 배포에는 이 방식이 안전하다.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

폴더이름 = "PatentKit"      # 설치 폴더는 영문. 사람에게 보이는 이름은 한글
표시이름 = "특허 자동화 킷"
최소파이썬 = (3, 10)


def 설치자리() -> Path:
    바탕 = os.environ.get("LOCALAPPDATA")
    return (Path(바탕) if 바탕 else Path.home() / ".local" / "share") / "Programs" / 폴더이름


def 마당(자리: Path) -> Path:
    """venv 안의 python.exe 경로."""
    return 자리 / "venv" / ("Scripts" if os.name == "nt" else "bin") / (
        "python.exe" if os.name == "nt" else "python")


def 달리기(명령: list, 이름: str, 조용히: bool = False) -> bool:
    끝난것 = subprocess.run(명령, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if 끝난것.returncode != 0:
        if not 조용히:
            print(f"  실패 — {이름}")
            for 줄 in (끝난것.stderr or 끝난것.stdout or "").splitlines()[-6:]:
                print(f"      {줄}")
        return False
    return True


def 꾸러미넣기(파이썬: Path, 꾸러미폴더: Path) -> bool:
    """세 번까지 시도한다.

    1. 함께 온 wheel 만으로 (인터넷 없이)
    2. wheel 을 먼저 보되 모자라면 인터넷에서 (파이썬 판이 달라 wheel 이 안 맞는 경우)
    3. 킷만이라도 (관청 서식 기능은 나중에 채울 수 있다)
    """
    바퀴들 = sorted(꾸러미폴더.glob("*.whl")) if 꾸러미폴더.exists() else []
    킷바퀴 = [str(바퀴) for 바퀴 in 바퀴들 if 바퀴.name.startswith("patentkit")]
    바탕 = [str(파이썬), "-m", "pip", "install", "--quiet", "--no-warn-script-location"]
    print(f"  꾸러미를 넣는다 — 함께 온 것 {len(바퀴들)}개")

    시도 = []
    if 바퀴들:
        시도.append(("함께 온 꾸러미로",
                    바탕 + ["--no-index", "--find-links", str(꾸러미폴더)]
                    + [str(바퀴) for 바퀴 in 바퀴들]))
        시도.append(("모자란 것은 인터넷에서",
                    바탕 + ["--find-links", str(꾸러미폴더), "patentkit", "python-docx", "pypdf"]))
        if 킷바퀴:
            시도.append(("킷만 먼저",
                        바탕 + ["--no-index", "--find-links", str(꾸러미폴더)] + 킷바퀴))
    else:
        시도.append(("인터넷에서", 바탕 + ["patentkit", "python-docx", "pypdf"]))

    for 설명, 명령 in 시도:
        if 달리기(명령, 설명, 조용히=True):
            print(f"    {설명} 넣었다.")
            return True
        print(f"    {설명} 넣지 못했다. 다음 방법을 쓴다.")
    print("  꾸러미를 넣지 못했다.")
    달리기(시도[-1][1], 시도[-1][0])      # 마지막 실패 까닭을 보여 준다
    return False


def 설치(꾸러미폴더: Path) -> int:
    print()
    print("─" * 58)
    print(f"  {표시이름} 설치")
    print("─" * 58)

    if sys.version_info < 최소파이썬:
        print(f"  파이썬이 너무 낮다 — {sys.version.split()[0]} "
              f"(최소 {'.'.join(map(str, 최소파이썬))})")
        return 2
    print(f"  파이썬 — {sys.version.split()[0]}")

    자리 = 설치자리()
    자리.mkdir(parents=True, exist_ok=True)
    print(f"  놓을 곳 — {자리}")

    venv자리 = 자리 / "venv"
    if venv자리.exists():
        print("  이전 설치를 지우고 새로 앉힌다.")
        shutil.rmtree(venv자리, ignore_errors=True)
    print("  전용 파이썬 자리를 만든다.")
    if not 달리기([sys.executable, "-m", "venv", str(venv자리)], "venv 만들기"):
        return 1

    파이썬 = 마당(자리)
    if not 꾸러미넣기(파이썬, 꾸러미폴더):
        return 1

    print("  바탕화면 아이콘과 PATH 를 잡는다.")
    끝난것 = subprocess.run([str(파이썬), "-m", "patentkit", "install"],
                          text=True, encoding="utf-8", errors="replace")
    if 끝난것.returncode != 0:
        return 1

    print("\n  잘 도는지 확인한다.")
    확인 = subprocess.run([str(파이썬), "-m", "patentkit", "selftest"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    줄들 = [줄 for 줄 in (확인.stdout or "").splitlines() if 줄.strip()]
    print(f"  {줄들[-1] if 줄들 else '결과 없음'}")
    if 확인.returncode != 0:
        print("  자체 시험이 통과하지 못했다. 설치는 됐으나 담당자에게 알린다.")
        return 1

    print()
    print("─" * 58)
    print("  설치를 마쳤다. 바탕화면의 「특허 자동화 킷」 아이콘을 두 번 누른다.")
    print("─" * 58)
    return 0


if __name__ == "__main__":
    for 스트림 in (sys.stdout, sys.stderr):
        try:
            스트림.reconfigure(encoding="utf-8")
        except Exception:
            pass
    여기 = Path(__file__).resolve().parent
    raise SystemExit(설치(여기 / "wheels"))
