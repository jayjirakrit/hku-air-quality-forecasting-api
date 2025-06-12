from pydantic import BaseModel
from typing import Optional

class Recommendation(BaseModel):
    id: Optional[int] = None
    recommend: Optional[str] = None
    image: Optional[str] = None