"""
부산 지하철 시간대별 승하차인원 원본(날짜별)을,
'역별 + 평일/주말 + 시간대별 평균 승하차 인원'으로 압축합니다.
"""
import pandas as pd

df = pd.read_csv(
    "/Users/jiwon/Downloads/부산교통공사_시간대별 승하차인원_20260630.csv",
    encoding="euc-kr",
)

HOUR_COLUMNS = [c for c in df.columns if "시-" in c]
WEEKEND_DAYS = {"토", "일"}

df["is_weekend"] = df["요일"].isin(WEEKEND_DAYS)

# 역명 + 평일/주말 기준으로 그룹핑, 승차/하차 구분 없이 시간대별 평균
grouped = df.groupby(["역명", "is_weekend"])[HOUR_COLUMNS].mean().round(1)
grouped = grouped.reset_index()

# 24개 시간대 컬럼을 "hour: 평균값" 형태의 딕셔너리로 정리해서 저장
def hour_col_to_int(col):
    # "01시-02시" -> 1, "24시-01시" -> 0(자정)
    h = int(col[:2])
    return 0 if h == 24 else h

result = []
for _, row in grouped.iterrows():
    for col in HOUR_COLUMNS:
        result.append({
            "station_name": row["역명"],
            "is_weekend": bool(row["is_weekend"]),
            "hour": hour_col_to_int(col),
            "avg_count": row[col],
        })

out_df = pd.DataFrame(result)
out_df.to_csv("app/data/subway_hourly_pattern.csv", index=False, encoding="utf-8-sig")
print(f"완료: {len(out_df)}행 저장 (역 {df['역명'].nunique()}개 x 평일/주말 2 x 시간대 24)")
print(out_df.head(10))