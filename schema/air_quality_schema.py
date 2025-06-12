from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime

class AirQuality(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    report_datetime: Optional[datetime] = None
    station: Optional[str] = None
    aqi: Optional[int] = None
    pm2_5: Optional[int] = None
    temp: Optional[float] = None
    wind: Optional[int] = None
    humidity: Optional[int] = None