# Apt — 내 집 마련을 위한 아파트 실거래가 분석

국토교통부 아파트 매매 실거래가 공공데이터를 모아, 관심 지역의 시세 흐름과 단지별 가격을 분석합니다.

## 핵심 목표

1. **내가 가진 자산으로 얼마짜리 아파트를 살 수 있나?** → `src/budget.py`
2. **청약은 어디까지 넣을 수 있나?** (가점, 특별공급 자격) → `src/chungyak.py`
3. 그 예산 안에서 **어느 지역·단지가 현실적인가?** → `src/fetch_trades.py`, `src/analyze.py`

## 빠른 시작: 내 예산과 청약 가점

```bash
cp profile.example.toml profile.toml   # 내 자산·소득·청약통장 정보 입력
python src/budget.py
python src/chungyak.py
```

> `profile.toml`은 `.gitignore`에 들어 있어 GitHub에 올라가지 않습니다. 이 저장소는 공개 저장소이니 개인 재무 정보는 이 파일에만 적어 주세요.
>
> 대출 규제(LTV·DSR·대출 상한)와 세율은 자주 바뀝니다. `profile.toml`의 `[loan]` 값을 최신 정부 발표나 은행 상담 결과에 맞춰 수정하세요.

## 폴더 구조

```
profile.example.toml  내 재무·청약 정보 입력 양식
src/budget.py         살 수 있는 최대 가격, 필요한 대출, 월 상환액 계산
src/chungyak.py       청약 가점(84점 만점)과 특별공급 기본 자격 확인
src/fetch_trades.py   실거래가 API에서 데이터를 받아 data/raw/에 CSV로 저장
src/analyze.py        CSV를 정리해 월별·동별·단지별 지표와 차트를 output/에 저장
data/lawd_codes.csv   서울 구별 법정동 코드(5자리)
notes/                연구 메모 (관심 단지, 임장 기록, 결론 등)
```

`data/raw/`와 `output/`은 다시 만들 수 있는 파일이라 git에 올리지 않습니다.

## 시작하기

### 1. 인증키 발급 (최초 1회)

1. [공공데이터포털](https://www.data.go.kr)에 가입합니다.
2. **"국토교통부_아파트 매매 실거래가 자료"**를 검색해 활용신청을 합니다. 보통 바로 또는 몇 시간 안에 승인됩니다.
3. 마이페이지에서 **일반 인증키(Decoding)**를 복사합니다.

### 2. 설치

```bash
pip install -r requirements.txt
cp .env.example .env   # .env 파일에 인증키 붙여넣기
```

### 3. 데이터 받기

```bash
python src/fetch_trades.py --region 마포구 --start 202401 --end 202412
```

### 4. 분석하기

```bash
python src/analyze.py data/raw/apt_trade_11440_202401_202412.csv --min-area 59 --max-area 85
```

`output/` 폴더에 월별 요약(`monthly.csv`), 동별 요약(`by_dong.csv`), 단지별 요약(`by_complex.csv`), 차트(`monthly.png`, `area_vs_price.png`)가 생깁니다.

## 참고

- 가격 단위는 **만원**, 평당 가격은 **전용면적 기준**입니다.
- 해제(취소)된 거래는 분석에서 제외합니다.
- 실거래 신고는 계약 후 30일 이내라 최근 1~2개월 데이터는 덜 쌓여 있을 수 있습니다.
