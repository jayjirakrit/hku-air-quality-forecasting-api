from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class AirQualityData(BaseModel):
    date: Optional[datetime] = None
    station: Optional[str] = None
    aqi: Optional[int] = None
    pm2_5: Optional[int] = None
    temp: Optional[float] = None
    wind: Optional[int] = None
    humidity: Optional[int] = None