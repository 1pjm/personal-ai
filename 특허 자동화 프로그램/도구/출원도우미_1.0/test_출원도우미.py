# -*- coding: utf-8 -*-
"""출원 도우미 자체 점검.  python test_출원도우미.py"""
import json, re, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import 출원도우미 as D


def main() -> int:
    # 감면율 읽기 — 글월에서 퍼센트를 뽑는다
    assert D.감면율("중소기업 70% 감경 (특허료 등의 징수규칙 별표 5)")[0] == 0.70
    assert D.감면율("개인")[0] == 0.70
    assert D.감면율("학생")[0] == 1.00
    assert D.감면율("")[0] == 0.0
    assert D.감면율("알 수 없는 말")[0] == 0.0          # 못 읽으면 감면하지 아니한다
    assert D.감면율("150%")[0] == 1.0                    # 1을 넘지 아니한다

    with tempfile.TemporaryDirectory() as t:
        건 = Path(t) / "출원건_00_시험"
        (건 / "도면").mkdir(parents=True)
        cfg = {"filing": {"fee_reduction": "중소기업 70%"},
               "invention": {"title_kr": "시험"}}
        (건 / "patent_config.json").write_text(json.dumps(cfg), encoding="utf-8")
        (건 / "03_제출본_명세서_청구범위.md").write_text("가" * 25_000, encoding="utf-8")
        (건 / "02_청구범위.md").write_text(
            "### 【청구항 1】\n갑.\n### 【청구항 2】\n을.\n## 회피 논거\n### 【청구항 9】\n무시.",
            encoding="utf-8")
        for n in range(3):
            (건 / "도면" / f"도{n+1}_가.svg").write_text("<svg/>", encoding="utf-8")

        assert D.청구항수(건) == [1, 2], D.청구항수(건)     # 회피 논거 뒤는 세지 아니한다
        assert D.도면수(건) == 3
        assert D.면수추정(건) == 28                          # 25면 + 도면 3장

        수 = D.수수료셈(건, cfg)
        assert 수["기본"] == 46_000
        assert 수["가산"] == (28 - 20) * 1_000 == 8_000
        assert 수["합계"] == 54_000
        assert 수["실납부"] == round(54_000 * 0.30) == 16_200
        assert 수["심사청구_참고"] == 166_000 + 51_000 * 2

        # 감면이 없으면 그대로 낸다
        cfg2 = {"filing": {}}
        assert D.수수료셈(건, cfg2)["실납부"] == 54_000

        # 사전등록 — ★ 가 남아 있으면 미확인이다
        낸 = D.사전등록점검({"applicants": [{"customer_no": "★확인 필요"}]})
        assert 낸[0][1] is False
        낸 = D.사전등록점검({"applicants": [{"customer_no": "4-2020-123456-7"}]})
        assert 낸[0][1] is True

    # 화면의 id 가 겹치지 아니하는가.
    # 레일 단추를 id="nav_${n}" 로 찍는데 서류 결과 칸도 id="r3" 이라 겹친 적이 있다.
    # getElementById 가 헤더의 단추를 먼저 집어 결과를 거기다 그렸고, 화면이 겹쳐 보였다.
    # 「찍어 내는 id」 와 「박아 둔 id」 가 같은 자리를 가리키면 잡는다.
    자리 = Path(__file__).resolve().parent
    js = (자리 / "화면.js").read_text(encoding="utf-8")
    html = (자리 / "화면.html").read_text(encoding="utf-8")
    글 = js + html
    찍는앞 = set(re.findall(r'id="([A-Za-z_]+)\$\{', 글))       # id="b${n}" → b
    박은것 = set(re.findall(r'id="([^"$]+)"', 글))                # id="r3"    → r3
    겹침 = sorted(f for f in 박은것 for a in 찍는앞
                 if f.startswith(a) and f[len(a):].isdigit())
    assert not 겹침, f"id 가 겹친다 — 찍는 앞머리 {sorted(찍는앞)} 와 박은 id {겹침}"

    # 아래에 붙는 요약이 본문 마지막 줄을 가리지 아니하는가.
    # CSS 는 main 의 아래 여백을 --sidh 로 잡고, JS 가 그 값을 띠 높이로 채운다.
    # 한쪽 이름만 고치면 여백이 0 이 되어 글이 가린다.
    for 변수 in ("--sidh", "--hdh"):
        assert f"var({변수}" in html, f"CSS 가 {변수} 를 쓰지 아니한다"
        assert f"'{변수}'" in js, f"JS 가 {변수} 를 채우지 아니한다"
    assert "addEventListener('resize', 높이재기)" in js, "창 크기가 바뀔 때 다시 재지 아니한다"

    # 표제의 메인보드 단추가 살아 있는가
    assert 'id="보드길"' in html and "보드길" in js, "메인보드로 가는 길이 없다"

    print(f"자체 점검 통과 — 감면율 6가지 · 수수료 4가지 · 사전등록 2가지 · 화면 id 겹침 없음 · 요약 여백·메인보드 길")
    return 0


if __name__ == "__main__":
    sys.exit(main())
