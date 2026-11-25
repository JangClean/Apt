"""내 자산과 소득으로 살 수 있는 아파트 최대 가격을 추정합니다.

사용 예:
    python src/budget.py               # profile.toml 사용
    python src/budget.py my.toml

계산 방식
    살 수 있는 가격 = 내 돈 + 대출 - 취득세·부대비용
    대출 = min(LTV 한도, DSR 한도, 정책 상한)

정책(LTV·DSR·대출 상한·취득세)은 자주 바뀝니다. profile.toml의 [loan] 값을
최신 정부 발표와 은행 상담 결과로 맞춘 뒤 결과를 참고용으로만 쓰세요.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_profile(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"{path}가 없습니다. profile.example.toml을 profile.toml로 복사해 값을 채워 주세요.")
    with open(path, "rb") as f:
        return tomllib.load(f)


def annual_payment(principal: float, rate_pct: float, years: int) -> float:
    """원리금균등상환 기준 연간 상환액."""
    r = rate_pct / 100 / 12
    n = years * 12
    if r == 0:
        return principal / years
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1) * 12


def max_loan_by_dsr(income: float, other: float, rate_pct: float, years: int, dsr_pct: float) -> float:
    """DSR 한도 안에서 빌릴 수 있는 최대 원금."""
    room = income * dsr_pct / 100 - other
    if room <= 0:
        return 0.0
    per_unit = annual_payment(1.0, rate_pct, years)
    return room / per_unit


def acquisition_tax(price: float) -> float:
    """1주택 취득세 + 지방교육세 근사치 (전용 85㎡ 이하, 농특세 제외)."""
    eok = price / 10000
    if eok <= 6:
        rate = 1.0
    elif eok <= 9:
        rate = eok * 2 / 3 - 3  # 6억~9억 구간 1%→3% 선형
    else:
        rate = 3.0
    tax = price * rate / 100
    return tax * 1.1  # 지방교육세(취득세의 10%) 근사


def total_costs(price: float, c: dict) -> float:
    return acquisition_tax(price) + price * c["brokerage_rate"] / 100 + c["misc"]


def solve_max_price(own: float, loan_cap: float, ltv: float, costs: dict) -> tuple[float, float]:
    """내 돈 + 대출 = 가격 + 부대비용 을 만족하는 최대 가격을 이분 탐색으로 찾습니다."""
    lo, hi = 0.0, 1_000_000.0  # 100억 상한
    for _ in range(100):
        mid = (lo + hi) / 2
        loan = min(loan_cap, mid * ltv / 100)
        if own + loan >= mid + total_costs(mid, costs):
            lo = mid
        else:
            hi = mid
    return lo, min(loan_cap, lo * ltv / 100)


def fmt(manwon: float) -> str:
    eok, rest = divmod(round(manwon), 10000)
    if eok and rest:
        return f"{eok}억 {rest:,}만원"
    if eok:
        return f"{eok}억원"
    return f"{rest:,}만원"


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "profile.toml"
    p = load_profile(path)
    a, inc, ln, c = p["assets"], p["income"], p["loan"], p["costs"]

    own = a["cash"] + a.get("deposit_to_return", 0)
    stress_rate = ln["rate"] + ln.get("stress_rate_add", 0)
    dsr_loan = max_loan_by_dsr(
        inc["annual"], a.get("other_debt_annual_payment", 0), stress_rate, ln["years"], ln["dsr_limit"]
    )
    loan_cap = min(dsr_loan, ln["max_loan"])

    price, loan = solve_max_price(own, loan_cap, ln["ltv"], c)
    no_loan_price, _ = solve_max_price(own, 0, 0, c)
    pay = annual_payment(loan, ln["rate"], ln["years"])

    print("=== 내 집 마련 예산 추정 ===")
    print(f"내 돈                 : {fmt(own)}")
    print(f"DSR 기준 대출 한도    : {fmt(dsr_loan)}  (스트레스 금리 {stress_rate:.1f}%, DSR {ln['dsr_limit']}%)")
    print(f"정책 대출 상한        : {fmt(ln['max_loan'])}")
    print(f"LTV                   : {ln['ltv']}%")
    print()
    print(f"▶ 살 수 있는 최대 가격 : {fmt(price)}")
    print(f"  필요한 대출          : {fmt(loan)}")
    print(f"  취득세·부대비용      : {fmt(total_costs(price, c))}")
    print(f"  월 상환액(금리 {ln['rate']}%, {ln['years']}년): 약 {pay / 12:,.0f}만원")
    print(f"  소득 대비 상환 비율  : {pay / inc['annual'] * 100:.1f}%")
    print()
    print(f"(참고) 대출 없이 살 수 있는 가격: {fmt(no_loan_price)}")

    binding = "LTV" if loan < loan_cap - 1 else ("정책 상한" if ln["max_loan"] <= dsr_loan else "DSR")
    print(f"(참고) 대출을 가장 크게 제한하는 조건: {binding}")


if __name__ == "__main__":
    main()
