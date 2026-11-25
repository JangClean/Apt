"""국토교통부 아파트 매매 실거래가 데이터를 내려받아 CSV로 저장합니다.

사용 예:
    python src/fetch_trades.py --region 11440 --start 202401 --end 202412
    python src/fetch_trades.py --region 마포구 --start 202401 --end 202412

인증키는 환경변수 DATA_GO_KR_SERVICE_KEY 또는 프로젝트 루트의 .env 파일에서 읽습니다.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
API_URL = (
    "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
)
PAGE_SIZE = 1000


def load_service_key() -> str:
    key = os.environ.get("DATA_GO_KR_SERVICE_KEY", "").strip()
    env_file = ROOT / ".env"
    if not key and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATA_GO_KR_SERVICE_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit(
            "인증키가 없습니다. .env.example을 .env로 복사하고 "
            "DATA_GO_KR_SERVICE_KEY 값을 채워 주세요."
        )
    return key


def resolve_region(region: str) -> tuple[str, str]:
    """지역 코드(5자리) 또는 구 이름을 받아 (코드, 이름)을 돌려줍니다."""
    with open(ROOT / "data" / "lawd_codes.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if region in (row["code"], row["name"]):
            return row["code"], row["name"]
    if region.isdigit() and len(region) == 5:
        return region, region
    sys.exit(f"알 수 없는 지역입니다: {region} (data/lawd_codes.csv 참고)")


def month_range(start: str, end: str) -> list[str]:
    y, m = int(start[:4]), int(start[4:])
    ey, em = int(end[:4]), int(end[4:])
    months = []
    while (y, m) <= (ey, em):
        months.append(f"{y}{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return months


def fetch_month(key: str, lawd_cd: str, ymd: str) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        params = {
            "serviceKey": key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": ymd,
            "pageNo": page,
            "numOfRows": PAGE_SIZE,
        }
        resp = requests.get(API_URL, params=params, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        code = root.findtext(".//resultCode")
        if code not in (None, "00", "000"):
            msg = root.findtext(".//resultMsg")
            raise RuntimeError(f"API 오류 {code}: {msg}")

        page_items = [
            {child.tag: (child.text or "").strip() for child in item}
            for item in root.iter("item")
        ]
        items.extend(page_items)

        total = int(root.findtext(".//totalCount") or 0)
        if page * PAGE_SIZE >= total or not page_items:
            return items
        page += 1
        time.sleep(0.2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--region", required=True, help="지역 코드 또는 구 이름")
    parser.add_argument("--start", required=True, help="시작 연월 (YYYYMM)")
    parser.add_argument("--end", required=True, help="종료 연월 (YYYYMM)")
    args = parser.parse_args()

    key = load_service_key()
    code, name = resolve_region(args.region)
    out_dir = ROOT / "data" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    all_items: list[dict] = []
    for ymd in month_range(args.start, args.end):
        items = fetch_month(key, code, ymd)
        print(f"{name} {ymd}: {len(items)}건")
        all_items.extend(items)
        time.sleep(0.2)

    if not all_items:
        print("받은 데이터가 없습니다.")
        return

    fields = sorted({k for item in all_items for k in item})
    out = out_dir / f"apt_trade_{code}_{args.start}_{args.end}.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_items)
    print(f"저장 완료: {out} ({len(all_items)}건)")


if __name__ == "__main__":
    main()
