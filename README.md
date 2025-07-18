# HKU Air Quality Forecasting API

## Overview
HKU Air Quality Forecasting API

## Technology Stack
- Python 3.12  
- FastAPI 0.115.12  
- PyTorch 2.7.1  
- Scikit-learn 1.7.0  
- SqlModel 0.0.24  
- Google Cloud Storage

## Installation and Usage

### Prerequisites
- Python 3.12

### Steps
```bash
cd hku-air-quality-forecasting-api
python3.12 -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload # Window
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000 # Linux
```
If run in local you to commend out create_db_and_tables() in main file and some service might not working

### Local Environment
- http://localhost:8000

## API

# HKU Air Quality Forecasting API Documentation

This document outlines the available endpoints provided by the HKU Air Quality Forecasting (AQF) API, including their paths and descriptions of their functionality.

## Endpoints

| **Path**                               | **Function**                                                                 |
|----------------------------------------|------------------------------------------------------------------------------|
|  `GET - http://localhost:8000/api/stations`                        | Get all stations information including station name, latitude, and longitude. |
| `POST - http://localhost:8000/api/forecast-air-quality/`          | Get predicted air quality for the next 24 hours across all stations.         |
| `GET - http://localhost:8000/api/real-time-air-quality/`         | Get current real-time air quality data, such as AQHI.                        |
| `GET - http://localhost:8000/api/real-time-analysis-air-quality/`| Get real-time air quality data for analysis purposes (e.g., AQHI, PM2.5, NO, NO₂, etc.). |