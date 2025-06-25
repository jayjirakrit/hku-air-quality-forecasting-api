from fastapi import FastAPI
from datetime import datetime
from fastapi import FastAPI, Query, HTTPException, Depends
from model import AirQualityData, StationModel, Recommendation  # Import from the model package
from typing import List,Optional
from fastapi.middleware.cors import CORSMiddleware
from service.station_service import StationService
from service.air_quality_service import AirQualityService
from sqlmodel import Session
from database import create_db_and_tables, get_session
from dotenv import load_dotenv
import os
import json
from util.cache_util import InMemoryCache
from datetime import timedelta
from typing import Optional, List, Dict, Any

# Load environment variables from .env file
load_dotenv()

origins = json.loads(os.getenv("ALLOWED_ORIGINS", "[]"))
station_service = StationService()
air_quality_service = AirQualityService()
in_memory_cache = InMemoryCache(default_ttl_seconds=timedelta(days=1).total_seconds())

app = FastAPI(
    title="HKU Air Quality Forecasting API",
    description="HKU Air Quality Forecasting API OpenAPI Specification.",
    version="1.0.0", # Optional: Specify API version
    openapi_url="/openapi.json", # Optional: Customize OpenAPI JSON endpoint
    docs_url="/docs", # Optional: Customize Swagger UI endpoint
    redoc_url="/redoc" # Optional: Customize ReDoc endpoint
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Custom function
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------ Database Setup ------ #

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# ----- API Endpoints ----- #

# Get all stations
@app.get("/api/stations/", response_model=List[StationModel])
async def get_stations( *,
    session: Session = Depends(get_session)):
    return station_service.get_stations(session)
     
# Get real-time air quality (all stations or specific station)
@app.get("/api/real-time-air-quality/")
async def get_real_time_air_quality( *,
    session: Session = Depends(get_session),
    station: Optional[str] = Query(None, description="Filter by station name (optional)")
):
    return await air_quality_service.get_real_time_air_quality(session,station)

@app.get("/api/air-quality-forecast/", response_model= List[Dict[str, Any]])
# def get_air_quality_forecast(*,
#     session: Session = Depends(get_session),
#     date: datetime = Query(None, description="Date for the forecast (YYYY-MM-DD)"),
#     station: str = Query(None, description="Station identifier (e.g., 'station_123')")
# ):    
async def get_air_quality_forecast(*,
    session: Session = Depends(get_session)
):
    print("Start AQ Forecasting")
    cached_data = in_memory_cache.get("real-time-air-quality")
    if cached_data:
        return cached_data
    
    # If not in cache or expired, fetch from source and cache it
    response_data = await air_quality_service.get_air_quality_forecast(session)
    in_memory_cache.set("real-time-air-quality", response_data) # Cache for default         
    return response_data

# Get recommendations based on air quality
@app.post("/api/recommendations/", response_model=List[Recommendation])
def get_recommendation(air_quality: AirQualityData = None):
    return air_quality_service.get_recommendation()