from fastapi import FastAPI, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from service.station_service import StationService
from service.air_quality_service import AirQualityService
from sqlmodel import Session
from database import create_db_and_tables, get_session
from dotenv import load_dotenv
import os
import shutil
import json
from util.cache_util import InMemoryCache
from datetime import timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from tzlocal import get_localzone
from lib.google_cloud import download_blob_to_file

# Load environment variables from .env file
load_dotenv()

origins = json.loads(os.getenv("ALLOWED_ORIGINS", '["http://localhost:3000","https://hku-capstone-project-458309.df.r.appspot.com"]'))
station_service = StationService()
air_quality_service = AirQualityService()
in_memory_cache = InMemoryCache(default_ttl_seconds=timedelta(days=1).total_seconds())

scheduler = AsyncIOScheduler(timezone=get_localzone())
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    
    try:
        create_db_and_tables()
    except Exception as e:
        print(f"Database Connection ERROR: Failed to connect Database: {e}")
    
    try:
        await clear_forecasting_cache()
        await batch_download_image_data()
    except Exception as e:
        print(f"Machine Learning Preparing Failed: Failed to load ml image data: {e}")
    
    try:
        with MockSession() as session:
            print("Startup: Fetching initial air quality data...")
            response_data = await air_quality_service.get_air_quality_forecast_v2(session)
            in_memory_cache.set("forecast-air-quality", response_data)
            print("Startup: Cache preloaded successfully!")
    except Exception as e:
        print(f"Startup ERROR: Failed to preload cache: {e}")
    
    yield
    scheduler.shutdown()

app = FastAPI(
    title="HKU Air Quality Forecasting API",
    description="HKU Air Quality Forecasting API OpenAPI Specification.",
    version="1.0.0", 
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan 
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Custom function
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MockSession:
    """
    A mock database session class that supports context management
    and provides dummy methods for common session operations.
    """
    def __enter__(self):
        print("Mock Session opened.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass # No actual resources to release in a mock

    def close(self):
        pass # No actual resources to release in a mock

    # Add any other methods your real Session object might have, empty commit/rollback etc.
    def add(self, obj):
        print(f"Mock Session: Added object {obj}")
        pass
    def commit(self):
        print("Mock Session: Committed changes.")
        pass
    def rollback(self):
        print("Mock Session: Rolled back changes.")
        pass
    def refresh(self, obj):
        print(f"Mock Session: Refreshed object {obj}")
        pass

def get_session_mock():
    session = MockSession()
    try:
        yield session
    finally:
        # In a real SQLAlchemy setup, this would be session.close()
        session.close()
    
# ----- API Endpoints ----- #

# Get all stations
@app.get("/api/stations/")
async def get_stations( *,
    session: Session = Depends(get_session)):
    return await station_service.get_stations(session)
     
# Get real-time air quality (all stations or specific station)
@app.get("/api/real-time-air-quality/")
async def get_real_time_air_quality( *,
    session: Session = Depends(get_session),
    station: Optional[str] = Query(None, description="Filter by station name (optional)")
):
    return await air_quality_service.get_real_time_air_quality(session,station)

# Get real-time analysis air quality (all stations or specific station)
@app.get("/api/real-time-analysis-air-quality/")
async def get_real_time_air_quality( *,
    session: Session = Depends(get_session)
):
    return await air_quality_service.get_real_time_aq_analysis(session)

@app.post("/api/forecast-air-quality/", response_model= List[Dict[str, Any]])
async def get_air_quality_forecast(*,
    session: Session = Depends(get_session)
):
    cached_data = in_memory_cache.get("forecast-air-quality")
    if cached_data:
        return cached_data

    # If not in cache or expired, fetch from source and cache it
    response_data = await air_quality_service.get_air_quality_forecast_v2(session)
    in_memory_cache.set("forecast-air-quality", response_data) # Cache for default         
    return response_data

# Scheduler download past 48 hour image data from GCS
@scheduler.scheduled_job('cron', hour=0, minute=10)
async def batch_download_image_data():    
    # Download image data from GCS
    bucket_name = os.getenv("GBS_BUCKET_NAME")
    source_file = os.getenv("GBS_SOURCE_FILE")
    destination_path = os.getenv("IMAGE_DESTINATION_PATH")
    move_path = os.getenv("IMAGE_MOVE_PATH")
    try:
        download_blob_to_file(bucket_name, source_file, destination_path)
        if os.path.exists(destination_path):
            os.makedirs(move_path, exist_ok=True)
            # Construct full destination path
            filename = os.path.basename(destination_path)
            target_path = os.path.join(move_path, filename)
            # Move the file
            shutil.move(destination_path, target_path)
            print(f"File moved to {target_path}")
        else:
            print(f"File not found at {destination_path}")

    except Exception as e:
        print(f"Download Image Data from GCS is failed: {e}")

# Scheduler Clear Forecasting Air Quality Cache
@scheduler.scheduled_job('cron', hour=0, minute=5)
async def clear_forecasting_cache():    
    try:
        in_memory_cache.invalidate("forecast-air-quality")
    except Exception as e:
        print(f"Error in clear forecasting cache: {e}")