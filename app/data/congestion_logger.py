    def fetch_population(self, poi_id: str, hour: int, is_weekend: bool) -> int:
        from app.data.skt_congestion import fetch_skt_population
        from app.data.busanjin_congestion import fetch_busanjin_population
        from app.data.subway_congestion import fetch_subway_population
        from app.data.cnctr_rate_congestion import fetch_cnctr_rate_population
        from app.data.mock_data import mock_realtime_population
        from app.data.congestion_logger import log_observation

        pois = self.fetch_pois()
        poi = next((p for p in pois if p.poi_id == poi_id), None)
        if poi is None:
            raise ValueError(f"존재하지 않는 poi_id: {poi_id}")

        skt_result = fetch_skt_population(poi_id, poi.area_m2)
        if skt_result is not None:
            log_observation(poi_id, "skt", skt_result)
            return skt_result

        busanjin_result = fetch_busanjin_population(poi.lat, poi.lng)
        if busanjin_result is not None:
            log_observation(poi_id, "busanjin", busanjin_result)
            return busanjin_result

        subway_result = fetch_subway_population(poi.lat, poi.lng, hour, is_weekend)
        if subway_result is not None:
            return subway_result

        cnctr_result = fetch_cnctr_rate_population(poi.name, poi.area_m2)
        if cnctr_result is not None:
            return cnctr_result

        return mock_realtime_population(poi_id, hour, is_weekend)