"""청약 가점과 기본 자격을 계산합니다.

사용 예:
    python src/chungyak.py               # profile.toml 사용

가점제(84점 만점)
    무주택기간     최대 32점
    부양가족 수    최대 35점
    청약통장 기간  최대 17점

특별공급(신혼부부·생애최초·다자녀 등)의 소득·자산 기준과 지역별 예치금 기준은
공고마다 다르니 청약홈(applyhome.co.kr)의 모집공고로 반드시 확인하세요.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from budget import ROOT, load_profile


def years_between(start: date, end: date) -> float:
    return (end - start).days / 365.25


def parse(d: str) -> date | None:
    return date.fromisoformat(d) if d else None


def homeless_start(h: dict, today: date) -> date | None:
    """무주택기간 기산일: 명시값 > (만 30세, 혼인신고일 중 빠른 날)."""
    if h.get("owns_home"):
        return None
    if h.get("homeless_since"):
        return parse(h["homeless_since"])
    birth_year = today.year - h["age"]
    turned_30 = date(birth_year + 30, today.month, min(today.day, 28))
    candidates = [turned_30]
    if h.get("married") and h.get("marriage_date"):
        candidates.append(parse(h["marriage_date"]))
    return min(candidates)


def homeless_score(start: date | None, today: date) -> int:
    if start is None:
        return 0
    if start > today:
        return 0  # 만 30세 미만 미혼: 무주택기간 0점
    y = years_between(start, today)
    if y < 1:
        return 2
    return min(32, 2 + 2 * int(y))


def dependents_score(n: int) -> int:
    return min(35, 5 + 5 * n)


def subscription_score(opened: date, today: date) -> int:
    y = years_between(opened, today)
    if y < 0.5:
        return 1
    if y < 1:
        return 2
    return min(17, 2 + int(y))


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "profile.toml"
    p = load_profile(path)
    h, s = p["household"], p["subscription"]
    today = date.today()

    start = homeless_start(h, today)
    opened = parse(s["opened"])
    sc_home = homeless_score(start, today)
    sc_dep = dependents_score(h["dependents"])
    sc_sub = subscription_score(opened, today)
    total = sc_home + sc_dep + sc_sub

    print("=== 청약 가점 ===")
    print(f"무주택기간    : {sc_home:>2} / 32  (기산일 {start or '해당 없음(주택 보유)'})")
    print(f"부양가족      : {sc_dep:>2} / 35  ({h['dependents']}명)")
    print(f"청약통장 기간 : {sc_sub:>2} / 17  (가입 {years_between(opened, today):.1f}년)")
    print(f"합계          : {total} / 84")
    print()

    print("=== 기본 자격 체크 (공고마다 세부 기준 확인 필요) ===")
    months = years_between(opened, today) * 12
    print(f"- 1순위 통장 기간(투기과열·청약과열지역 24개월): {'충족' if months >= 24 else '미충족'}")
    print(f"- 무주택 세대구성원: {'예' if not h.get('owns_home') else '아니오 (가점제 불리, 추첨제 위주)'}")
    if h.get("married") and h.get("marriage_date"):
        wed_years = years_between(parse(h["marriage_date"]), today)
        print(f"- 신혼부부 특별공급(혼인 7년 이내): {'대상 가능' if wed_years <= 7 else '기간 초과'} (혼인 {wed_years:.1f}년)")
    print(f"- 생애최초 특별공급: {'대상 가능' if h.get('first_time_buyer') else '해당 없음'} (소득·자산 기준 별도)")
    print(f"- 다자녀 특별공급: 자녀 수 기준 — 부양가족 중 미성년 자녀 수로 확인")
    print(f"- 통장 인정 납입액: {s['total_paid']:,}만원 (민영주택 지역·면적별 예치금 기준과 비교)")


if __name__ == "__main__":
    main()
