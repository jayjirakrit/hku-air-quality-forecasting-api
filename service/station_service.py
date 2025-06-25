from sqlmodel import select
from schema.station_schema import Station
from model.station_model import StationModel
from typing import List

class StationService:
    async def get_stations(self, session): 
        statement = select(Station)
        results = session.exec(statement)
        return [StationModel(id=r.id, name=r.name, latitude=r.latitude or 0.0, longitude=r.longitude or 0.0) for r in results]
