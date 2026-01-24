from typing import Dict
from src.services.amadeus_service import amadeus_service


class AirportCityCache:
    def __init__(self):
        self.cache: Dict[str, str] = {}
    
    def get_city_name(self, iata_code: str) -> str:
        """Get city name from airport code with caching"""
        if iata_code in self.cache:
            return self.cache[iata_code]

        try:
            loc_data = amadeus_service.get_location_info(iata_code, "AIRPORT")
            city = loc_data[0]["address"]["cityName"]
            self.cache[iata_code] = city
            return city
        except Exception as e:
            print(f"Error getting city name for {iata_code}: {e}")
            return iata_code  # Fallback to IATA code


# Global instance
airport_cache = AirportCityCache()