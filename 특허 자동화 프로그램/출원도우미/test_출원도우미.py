# -*- coding: utf-8 -*-
"""출원 도우미 자체 점검.  python test_출원도우미.py"""
import json, sys, tempfile
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

    print(f"자체 점검 통과 — 감면율 6가지 · 수수료 4가지 · 사전등록 2가지")
    return 0


if __name__ == "__main__":
    sys.exit(main())
