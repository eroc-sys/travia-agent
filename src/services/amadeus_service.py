import os
from amadeus import Client, ResponseError
from dotenv import load_dotenv

load_dotenv()


class AmadeusService:
    def __init__(self):
        self.client = Client(
            client_id=os.environ["AMADEUS_CLIENT_ID"],
            client_secret=os.environ["AMADEUS_CLIENT_SECRET"],
        )
    
    def search_flights(self, origin: str, destination: str, departure_date: str, adults: int):
        """Search for flights"""
        try:
            res = self.client.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=destination,
                departureDate=departure_date,
                adults=adults,
            )
            return res.data
        except ResponseError as e:
            raise e
    
    def search_hotels_by_city(self, city_code: str):
        """Get hotels in a city"""
        try:
            hotels_by_city = self.client.reference_data.locations.hotels.by_city.get(
                cityCode=city_code
            )
            return hotels_by_city.data
        except ResponseError as e:
            raise e
    
    def search_hotel_offers(self, hotel_id: str, adults: int, check_in: str, check_out: str):
        """Search for hotel offers"""
        try:
            offer = self.client.shopping.hotel_offers_search.get(
                hotelIds=hotel_id,
                adults=adults,
                checkInDate=check_in,
                checkOutDate=check_out
            )
            return offer.data
        except ResponseError as e:
            raise e
    
    def get_location_info(self, keyword: str, sub_type: str = "AIRPORT"):
        """Get location information"""
        try:
            loc = self.client.reference_data.locations.get(
                keyword=keyword,
                subType=sub_type
            )
            return loc.data
        except ResponseError as e:
            raise e


# Global instance
amadeus_service = AmadeusService()