from pydantic import BaseModel

class StationModel(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float