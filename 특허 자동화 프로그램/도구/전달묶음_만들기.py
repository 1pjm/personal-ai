# -*- coding: utf-8 -*-
"""전달용 묶음을 만든다.

    python 전달묶음_만들기.py          만든다
    python 전달묶음_만들기.py --확인   이미 있는 묶음이 최신인지 본다

`산출물/YYYYMMDD_전달묶음/특허출원도우미_판.zip` 이 나온다.
받는 사람은 압축을 풀고 「출원 준비.bat」 을 두 번 누르면 된다.

○ 원고와 산출물은 넣지 아니한다. 출원 전 명세서 전문이라 사외로 나가면 아니 된다.
  넣지 아니하는 것을 만든 뒤에 다시 확인한다.
"""
from __future__ import annotations

import datetime as dt
import os
import re
import subprocess
import shutil
import sys
import zipfile
from pathlib import Path

도구 = Path(__file__).resolve().parent
뿌리 = 도구.parent


def 판읽기() -> str:
    """변경내역의 맨 위 판을 그대로 쓴다. 두 곳에 판을 적어 두지 아니한다."""
    글 = (뿌리 / "버전기록" / "변경내역.md").read_text(encoding="utf-8")
    m = re.search(r"^##\s*(\d+\.\d+\.\d+)", 글, re.M)
    if not m:
        raise SystemExit("변경내역.md 에서 판을 찾지 못하였다.")
    return m.group(1)


안내글 = """특허 출원 도우미 {판}                                        {날}


■ 무엇을 하는 프로그램인가

  특허 명세서를 검사하고, 관청에 낼 서류를 만들고, 얼마를 내는지 셈하고,
  낸 뒤 진행 상황까지 봅니다. 특허를 하나도 모르셔도 화면만 따라가면 됩니다.

  관청에 내는 마지막 단추는 사람이 누릅니다. 특허청이 제출용 통로를 열어 두지
  않았고, 제출은 공동인증서로 서명하는 법률행위이기 때문입니다.


■ 쓰는 법 — 세 걸음

  1. 파이썬을 깔아 두세요.  https://www.python.org/downloads/
     설치 첫 화면의 "Add python.exe to PATH" 를 반드시 켜세요.

  2. 「원고」 폴더 안에 특허 원고 폴더를 넣으세요.
     patent_config.json 이 들어 있는 폴더가 특허 하나입니다.
     다른 자리에 두셔도 됩니다. 화면에서 폴더를 고를 수 있습니다.

  3. 「출원 준비.bat」 을 두 번 누르세요.
     검은 창이 뜨고 곧 브라우저 창이 열립니다.
     처음 한 번은 프로그램을 까느라 조금 걸립니다.
     검은 창을 닫으면 프로그램이 꺼집니다.


■ 화면은 일곱 마당입니다

  0  어느 특허를 낼까요      낼 것을 고릅니다
  1  준비물 갖추기          특허고객번호·전자문서 이용신고·인증서 (처음 한 번만)
  2  원고 검사             관청이 문제 삼을 곳을 미리 찾습니다
  3  서류 만들기            제출본·워드 파일·도면·준비서를 만듭니다
  4  비용 확인             얼마를 내는지 셈합니다
  5  특허로에 내기          내는 차례와 서식에 적을 값
  6  낸 뒤 진행 상황        출원번호로 지금 어디까지 갔는지 봅니다

  더 자세히 손보시려면 표제 오른쪽의 「전문가용 메인보드」 를 누르세요.
  청구항 대비, 단락번호 다시 매기기, 선행기술 조사까지 다룹니다.


■ 알아 두실 것

  · 이 프로그램은 그 컴퓨터 안에서만 돕니다. 원고가 밖으로 나가지 아니합니다.
  · 워드 파일(DOCX)까지 뽑으려면 검은 창에 한 번 치세요:  pip install python-docx
  · 6마당의 진행 상황 추적은 KIPRIS 열쇠가 있어야 합니다.
    plus.kipris.or.kr 에서 무료로 받아 화면에 한 번 넣어 두면 계속 씁니다.
    열쇠는 그 컴퓨터의 개인 폴더에만 두므로 이 묶음을 남에게 보내도 따라가지 않습니다.


■ 소스코드도 들어 있습니다

  「소스」 폴더에 무엇이 어떻게 도는지 다 들어 있습니다.
  읽어 보시거나 고치실 수 있습니다. 자세한 것은 소스 폴더의 읽어보기.txt 를 보세요.


■ 이 묶음에 없는 것

  특허 원고는 들어 있지 아니합니다. 프로그램만 있습니다.


■ 무엇이 바뀌었는지

  변경내역.md 를 보세요.
"""

원고안내 = """이 폴더 안에 특허 원고 폴더를 통째로 넣으세요.

  원고\\
    출원건_01_○○○\\
      patent_config.json     ← 이 파일이 있어야 특허로 알아봅니다
      01_명세서.md
      02_청구범위.md
      도면\\

폴더 이름은 자유입니다. 몇 단계 아래에 있어도 프로그램이 찾아냅니다.
다른 자리에 두셔도 됩니다 — 화면 0마당에서 폴더를 고를 수 있습니다.
"""


소스안내 = r"""소스코드

이 묶음은 돌려 쓰기만 해도 되지만, 무엇이 어떻게 도는지 보고 고칠 수도 있습니다.


■ 어디에 무엇이

  ..\출원도우미\        안내 화면 — 우리가 만든 것
      화면.html         뼈대와 색·글자
      화면.js           마당별 그리기
      화면.py           서버와 관청 자료
      출원도우미.py      수수료·사전등록·제출 차례
      test_출원도우미.py 자체 점검
  ..\run.py            배치가 부르는 중계
  ..\메인보드_옷.py     메인보드에 같은 색을 입힌다

  특허킷\patentkit\   검사·제출본·서식 — 팀원이 만든 것 (2.7.0)
      rules.py          검사 규칙 11갈래
      kipris.py         KIPRIS 조회
      doc.py            명세서 마크다운 해석
      ... 29개 모듈

  전달묶음_만들기.py     이 묶음을 다시 만드는 스크립트


■ 고쳐 보려면

  화면은 고치고 브라우저를 새로고침하면 바로 보입니다. 서버를 다시 띄우지
  않아도 됩니다.

  고친 뒤에는 자체 점검을 돌리세요.
      python 출원도우미\test_출원도우미.py


■ 특허킷 소스는 읽기용입니다

  여기 둔 것은 꾸러미(whl) 안의 것을 풀어 놓은 사본입니다.
  실제로 도는 것은 pip 로 깔린 쪽입니다. 여기를 고쳐도 반영되지 않습니다.
  고치려면 팀원에게 말씀하세요.


■ 다시 묶으려면

      python 소스\전달묶음_만들기.py --확인    지금 묶음이 최신인지 본다
      python 소스\전달묶음_만들기.py           다시 만든다

  다만 이 스크립트는 프로젝트 폴더 짜임을 전제합니다. 이 묶음 안에서는
  읽기용입니다.
"""


def 만들기() -> int:
    판 = 판읽기()
    날 = dt.date.today()
    이름 = f"특허출원도우미_{판}"
    낼곳 = 뿌리 / "산출물" / f"{날:%Y%m%d}_전달묶음"
    터 = 낼곳 / 이름
    if 터.exists():
        shutil.rmtree(터)
    (터 / "원고").mkdir(parents=True)

    # 도구 — 지금 쓰는 것만
    shutil.copytree(도구 / "출원도우미_1.0", 터 / "출원도우미",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.bak*"))
    for f in ("출원 준비.bat", "run.py", "메인보드_옷.py"):
        shutil.copy(도구 / f, 터 / f)

    # 특허킷 — 딸린 꾸러미째 넣어 인터넷 없이도 깔린다
    킷 = next(도구.glob("*특허킷*"), None)
    if 킷 is None:
        raise SystemExit("특허킷 폴더를 찾지 못하였다.")
    shutil.copytree(킷 / "원본" / "wheels", 터 / "특허킷" / "wheels")
    for f in ("설치.bat", "제거.bat", "사용안내.md", "README.md"):
        만약 = 킷 / "원본" / f
        if 만약.exists():
            shutil.copy(만약, 터 / "특허킷" / f)

    # 특허킷 소스 — 꾸러미(whl) 안의 것을 풀어 읽을 수 있게 둔다.
    # 받는 사람이 무엇이 도는지 볼 수 있어야 한다
    import zipfile as _z
    바퀴 = next((킷 / "원본" / "wheels").glob("patentkit-*.whl"))
    with _z.ZipFile(바퀴) as w:
        for 속 in w.namelist():
            if 속.startswith("patentkit/") and 속.endswith(".py"):
                낼자리 = 터 / "소스" / "특허킷" / 속
                낼자리.parent.mkdir(parents=True, exist_ok=True)
                낼자리.write_bytes(w.read(속))

    # 우리 소스 — 묶음을 다시 만드는 것까지 넘긴다
    (터 / "소스").mkdir(exist_ok=True)
    shutil.copy(도구 / "전달묶음_만들기.py", 터 / "소스" / "전달묶음_만들기.py")
    shutil.copy(뿌리 / "README.md", 터 / "소스" / "프로젝트_README.md")
    shutil.copy(뿌리 / "버전기록" / "README.md", 터 / "소스" / "버전기록_README.md")
    (터 / "소스" / "읽어보기.txt").write_text(소스안내, encoding="utf-8")

    (터 / "먼저 읽어주세요.txt").write_text(
        안내글.format(판=판, 날=날.isoformat()), encoding="utf-8")
    (터 / "원고" / "여기에 특허 원고를 넣으세요.txt").write_text(원고안내, encoding="utf-8")
    shutil.copy(뿌리 / "버전기록" / "변경내역.md", 터 / "변경내역.md")
    shutil.copy(뿌리 / "기능문서.md", 터 / "기능문서.md")

    # 원고나 산출물이 섞여 들어가지 아니하였는가
    샌것 = [f for f in 터.rglob("*")
           if f.is_file() and (f.name == "patent_config.json"
                               or re.search(r"명세서|청구범위|제출본", f.name))]
    if 샌것:
        raise SystemExit(f"★원고가 섞였다★ {[str(x) for x in 샌것]}")

    # 묶기 전에 자체 점검을 돌린다. 깨진 것을 남에게 보내지 아니한다
    r = subprocess.run([sys.executable, str(터 / "출원도우미" / "test_출원도우미.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode != 0:
        raise SystemExit("자체 점검이 떨어졌다. 묶지 아니한다.\n"
                         + (r.stdout or "") + (r.stderr or ""))
    print("  자체 점검 통과")

    # 묶으며 파일을 손대지 아니하였는가. 소스에서 새로 뜨므로 늘 같아야 한다.
    # 예전에 run.py 를 묶으며 문자열로 고쳐 넣은 적이 있는데 그런 짓을 잡는다.
    # 「이미 있는 zip 이 최신인가」 는 이것이 아니라 --확인 이 본다
    바깥 = {"기능문서.md": 뿌리 / "기능문서.md",
           "변경내역.md": 뿌리 / "버전기록" / "변경내역.md"}
    잰것 = 0
    for 안 in sorted(터.rglob("*")):
        if not 안.is_file() or 안.suffix not in (".py", ".js", ".html", ".bat", ".md"):
            continue
        상대 = 안.relative_to(터)
        밖 = (바깥.get(str(상대))
              or (도구 / "출원도우미_1.0" / 상대.name if 상대.parts[0] == "출원도우미"
                  else 도구 / 상대))
        if not 밖.exists():
            continue                      # 묶을 때 새로 지은 것(안내글 따위)
        if 밖.read_bytes() != 안.read_bytes():
            raise SystemExit(f"묶음이 소스와 다르다 — {상대}")
        잰것 += 1
    print(f"  손댄 것 없음 — {잰것}개 대조")

    묶음 = shutil.make_archive(str(낼곳 / 이름), "zip", str(낼곳), 이름)
    잰것 = zipfile.ZipFile(묶음)
    print(f"만들었다 — {Path(묶음).relative_to(뿌리)}")
    print(f"  {len(잰것.namelist())}개 항목 · {Path(묶음).stat().st_size / 1024:.0f} KB")
    print(f"  원고 유입 없음")
    return 0


def 확인() -> int:
    """이미 만들어 둔 묶음이 지금 소스와 같은가. 보내기 전에 이것을 본다."""
    import hashlib
    낸 = sorted(뿌리.glob("산출물/*/특허출원도우미_*.zip"))
    if not 낸:
        print("만들어 둔 묶음이 없다. 먼저 만든다.")
        return 1
    z = 낸[-1]
    zf = zipfile.ZipFile(z)
    뿌 = zf.namelist()[0].split("/")[0] + "/"
    짝 = {"기능문서.md": 뿌리 / "기능문서.md",
         "변경내역.md": 뿌리 / "버전기록" / "변경내역.md",
         "run.py": 도구 / "run.py",
         "메인보드_옷.py": 도구 / "메인보드_옷.py",
         "출원 준비.bat": 도구 / "출원 준비.bat"}
    for f in (도구 / "출원도우미_1.0").iterdir():
        if f.is_file() and f.suffix in (".py", ".js", ".html", ".md"):
            짝[f"출원도우미/{f.name}"] = f

    print(f"묶음 — {z.relative_to(뿌리)}")
    다름 = []
    for 안, 밖 in sorted(짝.items()):
        try:
            같 = (hashlib.sha256(zf.read(뿌 + 안)).hexdigest()
                 == hashlib.sha256(밖.read_bytes()).hexdigest())
        except KeyError:
            같 = False
        print(f"  {'같음' if 같 else '★다름★'}  {안}")
        if not 같:
            다름.append(안)
    if 다름:
        print(f"\n낡았다 — {len(다름)}개. 다시 만든다.")
        return 1
    print(f"\n최신이다 — {len(짝)}개 모두 같다.")
    return 0


if __name__ == "__main__":
    sys.exit(확인() if "--확인" in sys.argv else 만들기())
