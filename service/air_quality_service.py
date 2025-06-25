from datetime import datetime
from fastapi import HTTPException
from model import AirQualityData
import httpx
import xml.etree.ElementTree as ET
from service.station_service import StationService 
from dotenv import load_dotenv
import os
from typing import Optional, List, Dict, Any
from lib.forecasting_model import forecast_pm25

# Load environment variables from .env file
load_dotenv()
station_service = StationService()


class AirQualityService:
    async def get_air_quality_forecast(self, session):            
        return forecast_pm25()
    
    # Get real-time air quality (all stations or specific station)
    async def get_real_time_air_quality(self, session, station_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        URL = os.getenv("AQHI_API_URL")
        if not URL:
            raise HTTPException(status_code=500, detail="AQHI_API_URL environment variable is not set.")
        try:
            all_stations = await station_service.get_stations(session)
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(URL)
                response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
                root = ET.fromstring(response.text)
                items = []
                stations_by_lower_name = {s.name.lower(): s for s in all_stations}
                
                for item_elem in root.findall('./channel/item'): # Use a distinct variable name for the element
                    title_elem = item_elem.find('title')
                    description_elem = item_elem.find('description')
                    pub_date_elem = item_elem.find('pubDate')

                    district_name = title_elem.text.strip() if title_elem is not None else ""
                    description_text = description_elem.text.strip() if description_elem is not None else ""
                    pub_date = pub_date_elem.text if pub_date_elem is not None else ""

                    aqhi_str = None
                    risk = None

                    # Find the part after the second colon and before the final dash
                    parts_after_colon = description_text.split(': ', 1)
                    if len(parts_after_colon) > 1:
                        # This gets "2 Low - Wed, 25 Jun 2025 20:30"
                        aqhi_risk_date_part = parts_after_colon[1].strip()
                        
                        # Split by the first " - " to separate AQHI/Risk from date
                        aqhi_risk_components = aqhi_risk_date_part.split(' - ', 1)
                        if len(aqhi_risk_components) > 0:
                            aqhi_risk_str = aqhi_risk_components[0].strip() # This should be "2 Low" or "3 High"

                            # Split "2 Low" into AQHI and Risk
                            aqhi_and_risk = aqhi_risk_str.split(' ', 1)
                            if len(aqhi_and_risk) == 2:
                                aqhi_str = aqhi_and_risk[0].strip()
                                risk = aqhi_and_risk[1].strip()
                            elif len(aqhi_and_risk) == 1:
                                aqhi_str = aqhi_and_risk[0].strip()
                                risk = "N/A" # Default if risk level is missing

                    if aqhi_str is None or risk is None:
                        print(f"Warning: Could not parse AQHI/Risk from description '{description_text}' for district '{district_name}'. Skipping this item.")
                        continue # Skip to the next item

                    station_data = stations_by_lower_name.get(district_name.lower())                    
                    if (station_filter is None or station_filter.lower() == district_name.lower()) and station_data is not None:
                        try:
                            aqi_value = int(aqhi_str)
                        except ValueError:
                            print(f"Warning: Could not convert AQHI '{aqhi_str}' to int for district '{district_name}'. Skipping this item.")
                            continue # Skip this item if AQHI is not a valid integer

                        items.append({
                            'id': station_data.id,
                            'station': station_data.name,
                            'latitude': station_data.latitude,
                            'longitude': station_data.longitude,
                            'aqi': aqi_value,
                            'risk_level': risk,
                            'report_datetime': pub_date
                        })
                return items
        
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"External API HTTP error: {e.response.text}") from e
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Network error accessing external API: {str(e)}") from e
        except ET.ParseError as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse XML from external API: {str(e)}") 
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

        # mock_real_time_data = {
        #     "station_1": {
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