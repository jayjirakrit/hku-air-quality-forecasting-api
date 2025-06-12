from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime

class Station(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    latitude:  Optional[float] = None
    longitude: Optional[float] = None