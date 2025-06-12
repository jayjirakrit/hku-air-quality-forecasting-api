from sqlmodel import select
from schema.station_schema import Station
from model.station_model import StationModel
from typing import List

class StationService:
     def get_stations(self, session) -> List[StationModel]: 
        mock_stations = {
        "station_1": {"latitude": 34.0522, "longitude": -118.2437},
        "station_2": {"latitude": 40.7128, "longitude": -74.0060},
        }
        statement = select(Station)
        results = session.exec(statement)
        return [StationModel(id=r.id, name=r.name, latitude=r.latitude or 0.0, longitude=r.longitude or 0.0) for r in results]
