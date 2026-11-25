"""내려받은 실거래가 CSV를 정리하고 기본 지표와 차트를 만듭니다.

사용 예:
    python src/analyze.py data/raw/apt_trade_11440_202401_202412.csv
    python src/analyze.py data/raw/apt_trade_11440_202401_202412.csv --min-area 59 --max-area 85

결과물은 output/ 폴더에 저장됩니다.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PYEONG = 3.305785  # 1평 = 3.305785㎡


def setup_korean_font() -> None:
    """설치된 한글 폰트가 있으면 차트에 사용합니다."""
    from matplotlib import font_manager

    for name in ("AppleGothic", "Malgun Gothic", "NanumGothic", "Noto Sans CJK KR"):
        if any(f.name == name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")

    # 해제(취소)된 거래 제외
    if "cdealType" in df.columns:
        df = df[df["cdealType"].fillna("").str.strip() != "O"]

    df["price"] = df["dealAmount"].str.replace(",", "").str.strip().astype(float)  # 만원
    df["area"] = df["excluUseAr"].astype(float)  # 전용면적 ㎡
    df["floor"] = pd.to_numeric(df.get("floor"), errors="coerce")
    df["buildYear"] = pd.to_numeric(df.get("buildYear"), errors="coerce")
    df["date"] = pd.to_datetime(
        df["dealYear"] + "-" + df["dealMonth"].str.zfill(2) + "-" + df["dealDay"].str.zfill(2)
    )
    df["month"] = df["date"].dt.to_period("M")
    df["price_per_pyeong"] = df["price"] / (df["area"] / PYEONG)  # 만원/평(전용)
    return df


def summarize(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    monthly = (
        df.groupby("month")
        .agg(
            거래건수=("price", "size"),
            중위가격_만원=("price", "median"),
            평당중위가_만원=("price_per_pyeong", "median"),
        )
        .round(0)
    )
    by_dong = (
        df.groupby("umdNm")
        .agg(거래건수=("price", "size"), 평당중위가_만원=("price_per_pyeong", "median"))
        .sort_values("평당중위가_만원", ascending=False)
        .round(0)
    )
    by_complex = (
        df.groupby(["umdNm", "aptNm"])
        .agg(
            거래건수=("price", "size"),
            중위가격_만원=("price", "median"),
            평당중위가_만원=("price_per_pyeong", "median"),
            준공연도=("buildYear", "median"),
        )
        .query("거래건수 >= 3")
        .sort_values("거래건수", ascending=False)
        .round(0)
    )
    return {"monthly": monthly, "by_dong": by_dong, "by_complex": by_complex}


def plot(df: pd.DataFrame, monthly: pd.DataFrame, out_dir: Path, title: str) -> None:
    setup_korean_font()

    fig, ax1 = plt.subplots(figsize=(10, 5))
    x = monthly.index.to_timestamp()
    ax1.bar(x, monthly["거래건수"], width=20, color="#c9d6e3", label="거래건수")
    ax1.set_ylabel("거래건수")
    ax2 = ax1.twinx()
    ax2.plot(x, monthly["평당중위가_만원"], color="#1f5fa8", marker="o", label="평당 중위가")
    ax2.set_ylabel("평당 중위가 (만원, 전용 기준)")
    ax1.set_title(f"{title} 월별 거래량과 평당 중위가")
    fig.tight_layout()
    fig.savefig(out_dir / "monthly.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(df["area"], df["price"] / 10000, s=8, alpha=0.4, color="#1f5fa8")
    ax.set_xlabel("전용면적 (㎡)")
    ax.set_ylabel("거래가격 (억원)")
    ax.set_title(f"{title} 면적별 거래가격")
    fig.tight_layout()
    fig.savefig(out_dir / "area_vs_price.png", dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", type=Path, help="fetch_trades.py로 받은 CSV 파일")
    parser.add_argument("--min-area", type=float, default=0, help="최소 전용면적(㎡)")
    parser.add_argument("--max-area", type=float, default=1000, help="최대 전용면적(㎡)")
    args = parser.parse_args()

    df = load(args.csv)
    df = df[(df["area"] >= args.min_area) & (df["area"] <= args.max_area)]
    if df.empty:
        print("조건에 맞는 거래가 없습니다.")
        return

    out_dir = ROOT / "output" / args.csv.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    tables = summarize(df)
    for name, table in tables.items():
        table.to_csv(out_dir / f"{name}.csv", encoding="utf-8-sig")

    plot(df, tables["monthly"], out_dir, args.csv.stem)

    print(f"거래 {len(df)}건 분석 완료 → {out_dir}")
    print("\n[월별 요약]")
    print(tables["monthly"].to_string())
    print("\n[거래 많은 단지 TOP 10]")
    print(tables["by_complex"].head(10).to_string())


if __name__ == "__main__":
    main()
