from fastapi import HTTPException
import httpx
import xml.etree.ElementTree as ET
from service.station_service import StationService 
from dotenv import load_dotenv
import os
from typing import Optional, List, Dict, Any
from lib.forecasting_model import forecast_pm25
import asyncio
from collections import defaultdict

# Load environment variables from .env file
load_dotenv()
station_service = StationService()
gov_data_mapping = {
    "Central and Western": "CENTRAL",
    "Kowloon City": "KWUN TONG",
    "Kwun Tong": "KWUN TONG",
    "Sai Kung": "KWUN TONG",
    "Wan Chai": "CENTRAL",
    "Yau Tsim Mong": "CAUSEWAY BAY",
}

class AirQualityService:
    
    # Get forecasting air quality (all stations)
    async def get_air_quality_forecast(self, session):            
        return forecast_pm25()
    
    # Get real-time air quality (all stations or specific station)
    async def get_real_time_air_quality(self, session, station_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        AQHI_URL = os.getenv("AQHI_API_URL")        
        if not AQHI_URL:
            raise HTTPException(status_code=500, detail="AQHI_API_URL environment variable is not set.")
        try:
            all_stations = await station_service.get_stations(session)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(AQHI_URL)
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
                        continue

                    station_data = stations_by_lower_name.get(district_name.lower())                    
                    if (station_filter is None or station_filter.lower() == district_name.lower()) and station_data is not None:
                        try:
                            aqi_value = int(aqhi_str)
                        except ValueError:
                            print(f"Warning: Could not convert AQHI '{aqhi_str}' to int for district '{district_name}'. Skipping this item.")
                            continue

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
    
    async def get_real_time_air_quality_particle(self, session):
        LAMPPORT_API_URL = os.getenv("LAMPPORT_API_URL","https://paqs.epd-asmg.gov.hk/data/data.json")
        aggregated_data = defaultdict(lambda: {'pm25_sum': 0, 'no2_sum': 0, 'no_sum': 0, 'count': 0})
            
        if not LAMPPORT_API_URL:
            raise HTTPException(status_code=500, detail="LAMPPORT_API_URL environment variable is not set.")
            
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(LAMPPORT_API_URL)
                response.raise_for_status()
                response_data = response.json().get('data', [])
                    
                if not isinstance(response_data, list):
                    raise HTTPException(status_code=500, detail="Unexpected data format from external Lamppost API. Expected a list in 'data'.")

                for item_data in response_data:
                    lamppost_info = item_data.get('lamppost', {})
                    station_name = lamppost_info.get('district_en') 

                    # Ensure station_name is valid for grouping
                    if not station_name:
                        print(f"Warning: Item missing 'district_en' in lamppost info: {item_data}")
                        continue

                    pm2_5 = item_data.get('pm25')
                    no2 = item_data.get('no2')
                    no = item_data.get('no')

                    # Aggregate sums and count only if values are present (not None)
                    if pm2_5 is not None:
                        aggregated_data[station_name]['pm25_sum'] += pm2_5
                    if no2 is not None:
                        aggregated_data[station_name]['no2_sum'] += no2
                    if no is not None:
                        aggregated_data[station_name]['no_sum'] += no
                        
                    if pm2_5 is not None or no2 is not None or no is not None:
                        aggregated_data[station_name]['count'] += 1

            aggregated_results = []
            for station, data in aggregated_data.items():
                if data['count'] > 0:
                    aggregated_results.append({
                        'station': station,
                        'pm2_5': round(data['pm25_sum'] / data['count']) if data['pm25_sum'] is not None else None,
                        'no2': round(data['no2_sum'] / data['count']) if data['no2_sum'] is not None else None,
                        'no': round(data['no_sum'] / data['count']) if data['no_sum'] is not None else None,
                    })
            return aggregated_results

        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"External API HTTP error: {e.response.text}") from e
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Network error accessing external API: {str(e)}") from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    
    async def get_real_time_aq_analysis(self, session):
        aqhi_response, aq_data_response = await asyncio.gather(
            self.get_real_time_air_quality(session),
            self.get_real_time_air_quality_particle(session)
        )
        consolidate_response = []
        aqhi_lookup = {item.get('station').upper(): item for item in aqhi_response}
        for aq_data_item in aq_data_response:
            mapping_station = gov_data_mapping.get(aq_data_item.get('station'),'not found')
            aqhi_item = aqhi_lookup.get(mapping_station)
            if aqhi_item:
                consolidate_response.append({
                    'id': aqhi_item.get('id'),
                    'station': aq_data_item.get('station'),
                    'latitude': aqhi_item.get('latitude'),
                    'longitude': aqhi_item.get('longitude'),
                    'aqi': aqhi_item.get('aqi'),
                    'report_datetime': aqhi_item.get('report_datetime'),
                    'pm2_5': round(aq_data_item.get('pm2_5')),
                    'no': round(aq_data_item.get('no')),
                    'no2': round(aq_data_item.get('no2')),
                })
        return consolidate_response    