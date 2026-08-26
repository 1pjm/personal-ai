# -*- coding: utf-8 -*-
"""킷 자체 점검 — 검사가 잡아야 할 결함을 실제로 잡는지 본다.

    python test_patentkit.py
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import patentkit as K

성한명세서 = """## 【명세서】

### 【발명의 명칭】

시험용 자료 처리 장치, 그 방법 및 이를 기록한 컴퓨터 판독가능 기록매체

### 【기술분야】

[0001] 본 발명은 시험용 자료 처리 장치에 관한 것이다.

### 【발명의 배경이 되는 기술】

[0002] 종래에는 그러하지 아니하였다.

### 【발명의 내용】

[0003] 과제를 해결한다.

### 【도면의 간단한 설명】

[0004] 도 1은 시험용 자료 처리 장치(100)의 구성도이다.

### 【발명을 실시하기 위한 구체적인 내용】

[0005] 도 1을 참조하면, 시험용 자료 처리 장치(100)는 수신부(110)를 포함한다.

### 【부호의 설명】

[0006] 100: 시험용 자료 처리 장치, 110: 수신부

## 【요약서】

### 【요약】

본 발명은 시험용 자료 처리 장치에 관한 것이다.

### 【대표도】

도 1
"""

성한청구범위 = """## 【청구범위】

### 【청구항 1】

시험용 자료 처리 장치로서,

자료를 받는 수신부를 포함하는, 시험용 자료 처리 장치.

### 【청구항 2】

제1항에 있어서,

상기 수신부는 자료를 두 번 받는, 시험용 자료 처리 장치.

---

## 회피 논거

내부 검토용이므로 제출본에서 빠진다.
"""

성한config = {
    "invention": {"title_kr": "시험용 자료 처리 장치, 그 방법 및 이를 기록한 컴퓨터 판독가능 기록매체",
                  "title_en": "Test Apparatus"},
    "applicants": [{"name": "시험 주식회사", "biz_no": "123-45-67890", "type": "주출원"}],
    "inventors": [{"name": "홍길동", "org": "시험 주식회사", "is_representative": True}],
    "ipc": ["G06F 16/22"],
    "filing": {"kind": "임시명세서(가출원)",
               "disclosure_exception": {"claimed": False, "date": "", "medium": ""}},
    "paths": {"spec_md": "01_명세서.md", "claims_md": "02_청구범위.md", "out_dir": "_출력"},
    "style": {"font_kr": "바탕", "heading_sizes": {"1": 16, "2": 14, "3": 12}},
    "output": {"filename_pattern": "임시명세서_{date}.docx"},
}


def 출원건만들기(뿌리: Path, 명세서=성한명세서, 청구범위=성한청구범위, cfg=None) -> Path:
    폴더 = 뿌리 / "출원건_시험"
    폴더.mkdir(parents=True, exist_ok=True)
    (폴더 / "01_명세서.md").write_text(명세서, encoding="utf-8")
    (폴더 / "02_청구범위.md").write_text(청구범위, encoding="utf-8")
    (폴더 / "_발명의명칭.txt").write_text(
        (cfg or 성한config)["invention"]["title_kr"], encoding="utf-8")
    (폴더 / "patent_config.json").write_text(
        json.dumps(cfg or 성한config, ensure_ascii=False, indent=2), encoding="utf-8")
    return 폴더


def 검사명들(rep, 등급):
    return {검사 for g, 검사, _ in rep.항목 if g == 등급}


def main():
    뿌리 = Path(tempfile.mkdtemp(prefix="patentkit_test_"))
    try:
        # 1. 성한 출원건은 오류 0건이어야 한다
        폴더 = 출원건만들기(뿌리)
        rep = K.출원건처리(폴더)
        assert rep.오류수 == 0, [x for x in rep.항목 if x[0] == "오류"]

        # 2. 제출본은 명세서 본문 → 청구범위 → 요약서 순서로 나오고 회피 논거를 뺀다
        제출본 = (폴더 / "03_제출본_명세서_청구범위.md").read_text(encoding="utf-8")
        assert "회피 논거" not in 제출본
        assert 제출본.index("【청구항 1】") < 제출본.index("【요약서】")
        assert 제출본.index("【부호의 설명】") < 제출본.index("【청구항 1】")

        # 3. 재생성은 변동이 없어야 한다
        rep = K.출원건처리(폴더)
        assert "변동 없음" in dict((c, m) for _, c, m in rep.항목)["제출본 재생성"]

        # 4. 본문에 인용된 단락 참조는 단락 표지로 세지 아니한다 (종전 킷의 오탐)
        오탐본 = 성한명세서.replace("[0005] 도 1을 참조하면",
                                   "[0005] [0002]의 내용과 같이 도 1을 참조하면")
        폴더2 = 출원건만들기(뿌리 / "b", 명세서=오탐본)
        rep = K.출원건처리(폴더2)
        assert "단락번호" not in 검사명들(rep, "오류"), [x for x in rep.항목 if x[0] == "오류"]

        # 5. 진짜 결번은 잡아야 한다
        결번본 = 성한명세서.replace("[0005] 도 1을", "[0007] 도 1을")
        폴더3 = 출원건만들기(뿌리 / "c", 명세서=결번본)
        assert "단락번호" in 검사명들(K.출원건처리(폴더3), "오류")

        # 6. 없는 항 인용·자기 인용·후행 인용
        나쁜청구범위 = 성한청구범위.replace("제1항에 있어서", "제9항에 있어서")
        폴더4 = 출원건만들기(뿌리 / "d", 청구범위=나쁜청구범위)
        assert "청구항 인용 정합" in 검사명들(K.출원건처리(폴더4), "오류")

        # 7. 선언되지 않은 도면 인용
        도면본 = 성한명세서.replace("도 1을 참조하면", "도 1 및 도 3을 참조하면")
        폴더5 = 출원건만들기(뿌리 / "e", 명세서=도면본)
        assert "도면 선언" in 검사명들(K.출원건처리(폴더5), "오류")
        # 「산소포화도 16」 같은 어미는 도면 인용이 아니다
        어미본 = 성한명세서.replace("수신부(110)를 포함한다", "수신부(110)를 포함하고 산소포화도 16 을 받는다")
        폴더6 = 출원건만들기(뿌리 / "f", 명세서=어미본)
        assert "도면 선언" not in 검사명들(K.출원건처리(폴더6), "오류")

        # 8. 선언되지 않은 부호. 연도 (2025) 는 부호가 아니다
        부호본 = 성한명세서.replace("수신부(110)를", "수신부(110)와 저장부(120)를")
        폴더7 = 출원건만들기(뿌리 / "g", 명세서=부호본)
        assert "부호 대조" in 검사명들(K.출원건처리(폴더7), "오류")
        연도본 = 성한명세서.replace("수신부(110)를 포함한다", "수신부(110)를 포함하고 지침(2025)을 따른다")
        폴더8 = 출원건만들기(뿌리 / "h", 명세서=연도본)
        assert "부호 대조" not in 검사명들(K.출원건처리(폴더8), "오류")

        # 9. 명세서 편입분과 정본의 불일치
        편입본 = 성한명세서.replace("## 【요약서】",
                                   성한청구범위.split("---")[0].replace("두 번", "세 번")
                                   + "\n## 【요약서】")
        폴더9 = 출원건만들기(뿌리 / "i", 명세서=편입본)
        assert "편입분 대조" in 검사명들(K.출원건처리(폴더9), "오류")

        # 10. 문체 — 존댓말·마크업·따옴표
        문체본 = 성한명세서.replace("종래에는 그러하지 아니하였다.", "종래에는 그러하지 않았습니다.")
        폴더10 = 출원건만들기(뿌리 / "j", 명세서=문체본)
        assert "문체·표기" in 검사명들(K.출원건처리(폴더10), "오류")

        # 11. config — ★ 표식, 사업자번호 형식, 지분 합계
        별표 = json.loads(json.dumps(성한config))
        별표["inventors"][0]["name"] = "★발명자 확정 필요"
        폴더11 = 출원건만들기(뿌리 / "k", cfg=별표)
        assert "사람 확인 값" in 검사명들(K.출원건처리(폴더11), "오류")

        번호 = json.loads(json.dumps(성한config))
        번호["applicants"][0]["biz_no"] = "1234567890"
        폴더12 = 출원건만들기(뿌리 / "l", cfg=번호)
        assert "출원인" in 검사명들(K.출원건처리(폴더12), "오류")

        지분 = json.loads(json.dumps(성한config))
        지분["inventors"] = [{"name": "홍길동", "share_pct": 60},
                             {"name": "김철수", "share_pct": 30}]
        폴더13 = 출원건만들기(뿌리 / "m", cfg=지분)
        assert "발명자 지분" in 검사명들(K.출원건처리(폴더13), "오류")

        # 12. 공지예외 — 우선일 마감이 공개일+12개월과 어긋나면 잡는다
        공지 = json.loads(json.dumps(성한config))
        공지["filing"]["disclosure_exception"] = {"claimed": True, "date": "2026-08-02",
                                                  "medium": "웹페이지"}
        공지["filing"]["priority_deadline"] = "2027-09-30"
        폴더14 = 출원건만들기(뿌리 / "n", cfg=공지)
        assert "공지예외" in 검사명들(K.출원건처리(폴더14), "오류")

        # 13. init 로 만든 출원건은 ★ 두 곳만 막고 나머지는 통과한다
        새폴더 = 뿌리 / "새출원건"
        K.init(새폴더, "새 시험 장치, 그 방법 및 이를 기록한 컴퓨터 판독가능 기록매체")
        rep = K.출원건처리(새폴더)
        assert 검사명들(rep, "오류") <= {"사람 확인 값"}, [x for x in rep.항목 if x[0] == "오류"]

        # 14. 출원서 기재사항 한 장
        파일 = K.출원서요약(폴더, 성한config)
        본문 = 파일.read_text(encoding="utf-8")
        assert "홍길동" in 본문 and "123-45-67890" in 본문

        print("자체 점검 14개 항목 전부 통과")
        return 0
    finally:
        shutil.rmtree(뿌리, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
