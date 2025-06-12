from datetime import datetime
from fastapi import HTTPException
from model import AirQualityData
import requests
import xml.etree.ElementTree as ET
from service.station_service import StationService 
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()
station_service = StationService()


class AirQualityService:
    def get_air_quality_forecast(self, session, date: datetime, station: str):            
        # Mock database (replace with real DB/API calls)
        mock_forecast_data = {
            "station_123": {
                "2025-01-01": {
                    "aqi": 45,
                    "pm2_5": 12,
                    "temp": 22.5,
                    "wind": 10,
                    "humidity": 65
                }
            }
        }
        # Convert datetime to date string (YYYY-MM-DD) for lookup
        date_str = date.strftime("%Y-%m-%d")
        
        # Check if station exists
        if station not in mock_forecast_data:
            raise HTTPException(status_code=404, detail="Station not found")
        
        # Check if forecast exists for the given date
        station_data = mock_forecast_data[station]
        if date_str not in station_data:
            raise HTTPException(status_code=404, detail="Forecast not available for this date")
        
        forecast = station_data[date_str]
        
        return [{
            "date": date,
            "station": station,
            "aqi": forecast["aqi"],
            "pm2_5": forecast["pm2_5"],
            "temp": forecast["temp"],
            "wind": forecast["wind"],
            "humidity": forecast["humidity"]
        }]
    
    # Get real-time air quality (all stations or specific station)
    def get_real_time_air_quality(self, session, station: str):
        URL = os.getenv("AQHI_API_URL")
        try:
            # Get All Stations
            stations = station_service.get_stations(session)

            response = requests.get(URL, timeout=5)
            response.raise_for_status()
            # Parse the XML response
            root = ET.fromstring(response.text)
            items = []
            
            for item in root.findall('.//channel/item'):
                title = item.find('title').text
                description = item.find('description').text.strip()
                pub_date = item.find('pubDate').text
                # Extract data from title (format: "District : AQHI : Risk Level")
                parts = title.split(' : ')
                if len(parts) == 3:
                    district, aqhi, risk = parts
                    stationData = next((s for s in stations if s.name.lower() == district.lower()), None)
                    if (station is None or station.lower() in district.lower()) and stationData is not None:
                        items.append({
                            'id': stationData.id,
                            'station': stationData.name,
                            'latitude': stationData.latitude,
                            'longitude': stationData.longitude,
                            'aqi': int(aqhi),
                            'risk_level': risk,
                            'report_datetime': pub_date
                        })
            return items
        
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=400, detail=f"API call failed: {str(e)}")
        except ET.ParseError as e:
            raise HTTPException(status_code=500, detail=f"XML parsing failed: {str(e)}") 
        # mock_real_time_data = {
        #     "station_1": {
        #         "date": datetime.now(),
        #         "station": "central",
        #         "aqi": 65,
        #         "pm2_5": 25,
        #         "temp": 28.3,
        #         "wind": 12,
        #         "humidity": 60,
        #     },
        #     "station_2": {
        #         "date": datetime.now(),
        #         "station": "central",
        #         "aqi": 42,
        #         "pm2_5": 15,
        #         "temp": 22.1,
        #         "wind": 8,
        #         "humidity": 55,
        #     },
        # }
        # return [mock_real_time_data[station]]
    
    def get_recommendation(self, session, air_quality: AirQualityData = None):
        mock_recommendations = [
        { "image": "", "recommend": "Sensitive groups should wear a mask outdoors" },
        { "image": "", "recommend": "Sensitive groups should reduce outdoor exercise" },
        { "image": "", "recommend": "Close your windows to avoid dirty outdoor air" },
        ]
        # # Example logic: Recommend masks if AQI > 50
        # if air_quality.aqi > 50:
        #     return mock_recommendations
        # else:
        #     return [mock_recommendations[1]]  # Only return "close windows"
        return mock_recommendations