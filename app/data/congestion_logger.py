"""
SKT·부산진구 실시간 데이터를 부를 때마다, 나중에 지하철처럼 "시간대별 평균
패턴"을 학습할 수 있도록 관측값을 계속 CSV에 쌓아둡니다.

지하철 데이터(6개월치)로 평균 패턴을 만들었던 것과 같은 방식을, SKT·부산진구도
나중에(예: 11월 부산 현장검증 즈음) 시도해볼 수 있도록 지금부터 데이터를
모아두는 목적입니다. 추가 API 호출을 발생시키지 않고, 이미 하는 호출의
결과값만 옆에서 기록합니다.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

_LOG_PATH = Path(__file__).parent / "congestion_observations.csv"


def log_observation(poi_id: str, source: str, value: int) -> None:
    """
    관측값 한 건을 기록합니다.

    poi_id: 우리 쪽 POI 식별자
    source: "skt" 또는 "busanjin"
    value: 그 시점에 계산된 population 값
    """
    now = datetime.now()
    is_new_file = not _LOG_PATH.exists()

    try:
        with open(_LOG_PATH, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if is_new_file:
                writer.writerow(["timestamp", "poi_id", "source", "weekday", "hour", "value"])
            writer.writerow([
                now.isoformat(timespec="seconds"),
                poi_id,
                source,
                now.strftime("%a"),  # 예: Mon, Tue ...
                now.hour,
                value,
            ])
    except OSError:
        # 로깅 실패가 본 기능(고요지수 계산)을 막으면 안 되므로 조용히 무시
        pass