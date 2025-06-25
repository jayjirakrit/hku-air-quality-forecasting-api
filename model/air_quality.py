from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class AirQualityData(BaseModel):
    date: Optional[datetime] = None
    time: Optional[int] = None
    station: Optional[str] = None
    aqi: Optional[int] = None
    pm2_5: float = None
    temp: Optional[float] = None
    wind: Optional[int] = None
    humidity: Optional[int] = None