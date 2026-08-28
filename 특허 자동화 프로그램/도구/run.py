# -*- coding: utf-8 -*-
"""출원 준비.bat 이 부르는 중계.

배치 파일 안에 한글을 적으면 chcp 65001 뒤에 cmd 파싱이 깨진다.
그래서 배치는 ASCII 이름의 이 파일만 부르고, 한글 경로는 여기서 푼다.

짜임을 두 가지로 쓴다. 어느 쪽이든 돌도록 자리를 찾아 간다.

  프로젝트          묶음(전달용)
  ├ 도구/           ├ run.py
  │ ├ run.py        ├ 출원도우미/
  │ └ 출원도우미_1.0/ ├ 특허킷/
  └ 원고/           └ 원고/
"""
import subprocess
import sys
from pathlib import Path

자리 = Path(__file__).resolve().parent


def 찾기(*무늬, 없으면=None):
    """제 자리와 그 위에서 차례로 찾는다."""
    for 터 in (자리, 자리.parent):
        for m in 무늬:
            낸 = sorted(터.glob(m))
            if 낸:
                return 낸[0]
    return 없으면


원고 = 찾기("원고", "*/원고", 없으면=자리)
화면 = 찾기("출원도우미*/화면.py", "*/출원도우미*/화면.py")
바퀴 = 찾기("*특허킷*/**/patentkit-*.whl")

if 화면 is None:
    raise SystemExit(f"화면.py 를 찾지 못하였다. 자리 — {자리}")

if subprocess.run([sys.executable, "-m", "patentkit", "--version"],
                  capture_output=True).returncode != 0:
    if 바퀴:
        print("특허킷을 깝니다. 처음 한 번만 걸립니다…")
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", str(바퀴)])
    else:
        print("특허킷 꾸러미를 찾지 못하였다. pip install patentkit 로 깐다.")

sys.exit(subprocess.run([sys.executable, str(화면), str(원고), *sys.argv[1:]]).returncode)
