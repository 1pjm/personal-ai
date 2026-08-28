# -*- coding: utf-8 -*-
"""출원 준비.bat 이 부르는 중계.

배치 파일 안에 한글을 적으면 chcp 65001 뒤에 cmd 파싱이 깨진다.
그래서 배치는 ASCII 이름의 이 파일만 부르고, 한글 경로는 여기서 푼다.
"""
import os, subprocess, sys
from pathlib import Path

도구 = Path(__file__).resolve().parent
뿌리 = 도구.parent

r = subprocess.run([sys.executable, "-m", "patentkit", "--version"],
                   capture_output=True)
if r.returncode != 0:
    바퀴 = next(도구.glob("*특허킷*/원본/wheels/patentkit-*.whl"), None)
    if 바퀴:
        print("특허킷을 깝니다…")
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", str(바퀴)])

sys.exit(subprocess.run([sys.executable, str(도구 / "출원도우미_1.0" / "화면.py"), str(뿌리 / "원고"), *sys.argv[1:]]).returncode)
