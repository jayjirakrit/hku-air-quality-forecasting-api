from sqlmodel import select
from schema.station_schema import Station
from model.station_model import StationModel
from typing import List

class StationService:
    async def get_stations(self, session): 
        # statement = select(Station)
        # results = session.exec(statement)
        raw_data = [{"id":1,"name":"Causeway Bay","latitude":22.2798,"longitude":114.1831},
                    {"id":2,"name":"Central","latitude":22.2823,"longitude":114.1585},
                    {"id":3,"name":"Central/Western","latitude":22.2866,"longitude":114.1455},
                    {"id":5,"name":"Kwai Chung","latitude":22.3639,"longitude":114.1347},
                    {"id":6,"name":"Kwun Tong","latitude":22.3122,"longitude":114.2255},
                    {"id":7,"name":"Mong Kok","latitude":22.3193,"longitude":114.1694},
                    {"id":8,"name":"North","latitude":22.5027,"longitude":114.1308},
                    {"id":9,"name":"Southern","latitude":22.2477,"longitude":114.1584},
                    {"id":10,"name":"Sham Shui Po","latitude":22.3307,"longitude":114.1622},
                    {"id":11,"name":"Shatin","latitude":22.3823,"longitude":114.1892},
                    {"id":12,"name":"Tung Chung","latitude":22.2887,"longitude":113.9424},
                    {"id":13,"name":"Tseung Kwan O","latitude":22.3079,"longitude":114.2601},
                    {"id":14,"name":"Tap Mun","latitude":22.4633,"longitude":114.3617},
                    {"id":15,"name":"Tuen Mun","latitude":22.3916,"longitude":113.9736},
                    {"id":16,"name":"Tai Po","latitude":22.448,"longitude":114.1612},
                    {"id":17,"name":"Tsuen Wan","latitude":22.3709,"longitude":114.1135},
                    {"id":18,"name":"Yuen Long","latitude":22.4455,"longitude":114.0226}]
        return [StationModel(**data) for data in raw_data]
        # return [StationModel(id=r.id, name=r.name, latitude=r.latitude or 0.0, longitude=r.longitude or 0.0).model_dump() for r in results]
