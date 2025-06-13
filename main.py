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

# Load environment variables from .env file
load_dotenv()

origins = json.loads(os.getenv("ALLOWED_ORIGINS", "[]"))
station_service = StationService()
air_quality_service = AirQualityService()

app = FastAPI()
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

@app.get("/api/air-quality-forecast/", response_model=List[AirQualityData])
def get_air_quality_forecast(
    date: datetime = Query(..., description="Date for the forecast (YYYY-MM-DD)"),
    station: str = Query(..., description="Station identifier (e.g., 'station_123')")
):    
    return air_quality_service.get_air_quality_forecast(date,station)
     
# Get real-time air quality (all stations or specific station)
@app.get("/api/real-time-air-quality/")
def get_real_time_air_quality( *,
    session: Session = Depends(get_session),
    station: Optional[str] = Query(None, description="Filter by station name (optional)")
):
    return air_quality_service.get_real_time_air_quality(session,station)

# Get all stations
@app.get("/api/stations/", response_model=List[StationModel])
def get_stations( *,
    session: Session = Depends(get_session)):
    return station_service.get_stations(session)

# Get recommendations based on air quality
@app.post("/api/recommendations/", response_model=List[Recommendation])
def get_recommendation(air_quality: AirQualityData = None):
    return air_quality_service.get_recommendation()