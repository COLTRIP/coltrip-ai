from __future__ import annotations

from app.models.nudge_engine import recommend_alternatives, should_trigger_nudge
from app.services.quiet_index_service import get_all_quiet_indices, get_quiet_index


def get_alternatives_if_needed(
    poi_id: str, hour: int, is_weekend: bool, baseline_quiet_index: float | None = None
) -> dict:
    target_poi, _population, target_quiet_index = get_quiet_index(poi_id, hour, is_weekend)

    triggered = should_trigger_nudge(target_quiet_index, baseline_quiet_index)
    if not triggered:
        return {"triggered": False, "target_quiet_index": target_quiet_index, "alternatives": []}

    all_results = get_all_quiet_indices(hour, is_weekend)
    candidates = [(poi, qi) for poi, _pop, qi in all_results]

    alternatives = recommend_alternatives(
        target_poi=target_poi,
        target_quiet_index=target_quiet_index,
        candidates=candidates,
    )
    return {
        "triggered": True,
        "target_quiet_index": target_quiet_index,
        "alternatives": alternatives,
    }
