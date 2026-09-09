"""
TourAPI detailCommon2로 각 관광지의 overview(소개글)를 가져와 CSV로 저장합니다.

fetch_pois()와 별도로 실행하는 이유: 594개 전부 조회하면 API를 594번 더 써야 해서
(하루 한도 1,000건), 디버깅 중 반복 실행으로 한도를 낭비하지 않기 위함입니다.

이미 저장된 poi_id는 건너뛰므로, 중간에 끊겨도 다시 실행하면 이어서 진행됩니다.
사용법: python3 -m scripts.fetch_overviews [가져올 개수, 기본 20]
"""
import csv
import sys
import time
from pathlib import Path

import httpx

from app.config import settings
from app.data.category_mapping import map_tourapi_category
from app.data.loader import TOUR_API_BASE_URL, _fetch_area_based_list

OUTPUT_PATH = Path("scripts/overviews.csv")


def fetch_overview(content_id: str) -> dict:
    params = {
        "serviceKey": settings.TOUR_API_KEY,
        "MobileOS": "ETC",
        "MobileApp": "COLTRIP",
        "_type": "json",
        "numOfRows": 1,
        "pageNo": 1,
        "contentId": content_id,
    }
    resp = httpx.get(f"{TOUR_API_BASE_URL}/detailCommon2", params=params, timeout=10)
    resp.raise_for_status()
    body = resp.json()["response"]["body"]
    items = body.get("items", "")
    if not items:
        return {"overview": "", "image": ""}
    item = items["item"]
    if isinstance(item, list):
        item = item[0]
    return {"overview": item.get("overview", ""), "image": item.get("firstimage", "")}

def load_existing_ids() -> set[str]:
    if not OUTPUT_PATH.exists():
        return set()
    with open(OUTPUT_PATH, encoding="utf-8-sig") as f:
        return {row["poi_id"] for row in csv.DictReader(f)}


def main(limit: int) -> None:
    # fetch_pois()는 contentTypeId를 안 갖고 있어서, 원본을 다시 훑으며
    # (poi_id, contentTypeId) 매핑을 따로 만듭니다.
    poi_meta: dict[str, dict] = {}
    for content_type_id in ("12", "14", "39"):
        for item in _fetch_area_based_list(content_type_id):
            poi_id = item.get("contentid")
            if not poi_id or poi_id in poi_meta:
                continue
            category = map_tourapi_category(
                lcls_systm3=item.get("lclsSystm3", ""),
                lcls_systm2=item.get("lclsSystm2", ""),
            )
            if category is None:
                continue
            poi_meta[poi_id] = {
                "name": item.get("title", ""),
                "category": category,
                "content_type_id": content_type_id,
            }

    existing_ids = load_existing_ids()
    write_header = not OUTPUT_PATH.exists()

    count = 0
    with open(OUTPUT_PATH, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["poi_id", "name", "category", "overview"])

        for poi_id, meta in poi_meta.items():
            if poi_id in existing_ids:
                continue
            if count >= limit:
                break
            try:
                overview = fetch_overview(poi_id)
            except Exception as e:
                print(f"실패: {meta['name']} ({poi_id}) - {e}")
                continue

            writer.writerow([poi_id, meta["name"], meta["category"], overview])
            f.flush()
            print(f"[{count + 1}] {meta['name']}: {overview[:30]}...")
            count += 1
            time.sleep(0.1)

    print(f"\n이번에 {count}건 저장, 누적 {len(existing_ids) + count}건")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    main(limit=n)