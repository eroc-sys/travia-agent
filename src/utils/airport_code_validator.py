"""
Airport Code Validator with fuzzy matching and alternative name support
Validates city names/IATA codes against airports.csv and returns correct IATA codes
Note: This is separate from query_validator.py which handles input sanitization
"""

import csv
from typing import Optional, Dict, List
from pathlib import Path
from difflib import SequenceMatcher


class AirportValidator:
    def __init__(self, csv_path: str = "data/airports.csv"):
        self.csv_path = csv_path
        self.airports: Dict[str, Dict] = {}  # IATA -> airport info
        self.city_to_iata: Dict[str, str] = {}  # city name -> IATA
        self.alternative_names: Dict[str, str] = {}  # alternative name -> canonical city
        
        # Define alternative city names and IATA mappings
        self.alternative_mappings = {
            # City alternative names
            "cochin": "kochi",
            "bombay": "mumbai",
            "bangalore": "bengaluru",
            "bengaluru": "bangalore",  # Bidirectional
            "calcutta": "kolkata",
            "madras": "chennai",
            "trivandrum": "thiruvananthapuram",
            "thiruvananthapuram": "trivandrum",
            "calicut": "kozhikode",
            "kozhikode": "calicut",
            "poona": "pune",
            "baroda": "vadodara",
            
            # Common IATA code inputs (people often search by these)
            "bom": "mumbai",
            "del": "delhi",
            "blr": "bangalore",
            "maa": "chennai",
            "ccu": "kolkata",
            "hyd": "hyderabad",
            "goa": "goa",
            "cok": "kochi",
            "ccj": "calicut",
            "ixc": "chandigarh",
            "amd": "ahmedabad",
            "pnq": "pune",
            "jai": "jaipur",
            "gau": "guwahati",
            "idr": "indore",
            "vns": "varanasi",
            "pat": "patna",
            "rpr": "raipur",
            "nag": "nagpur",
            "sxr": "srinagar",
            "ixj": "jammu",
            "ixl": "leh",
            "ixb": "bagdogra",
            "ixz": "port blair",
            "ixr": "ranchi",
            "bho": "bhopal",
            "ixu": "aurangabad",
            "ixe": "mangalore",
            "trz": "tiruchirappalli",
            "tir": "tirupati",
            "nvi": "navi mumbai",
            "mum": "mumbai",
        }
        
        self._load_airports()
    
    def _load_airports(self):
        """Load airports from CSV file - only large_airport type"""
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Only process large airports
                    airport_type = (row.get("type") or "").strip().lower()
                    if airport_type != "large_airport":
                        continue
                    
                    iata = (row.get("iata_code") or "").strip().upper()
                    city = (row.get("municipality") or "").strip().lower()
                    
                    # Skip if no IATA code
                    if not iata or len(iata) != 3:
                        continue
                    
                    airport_info = {
                        "iata": iata,
                        "name": row.get("name", "").strip(),
                        "city": row.get("municipality", "").strip(),
                        "country": row.get("iso_country", "").strip(),
                        "type": airport_type,
                        "keywords": (row.get("keywords") or "").strip().lower(),
                        "iso_region": row.get("iso_region", "").strip(),
                    }
                    
                    # Store airport by IATA code
                    self.airports[iata] = airport_info
                    
                    # Map city name to IATA (lowercase for matching)
                    if city:
                        self.city_to_iata[city] = iata
                    
                    # Also map keywords to IATA if present
                    keywords = airport_info["keywords"]
                    if keywords:
                        keyword_list = [k.strip() for k in keywords.split(',')]
                        for keyword in keyword_list:
                            if keyword and keyword not in self.city_to_iata:
                                self.city_to_iata[keyword] = iata
                
                print(f"✅ Loaded {len(self.airports)} large airports from {self.csv_path}")
                print(f"✅ Mapped {len(self.city_to_iata)} city names to IATA codes")
                
        except FileNotFoundError:
            print(f"❌ Error: {self.csv_path} not found!")
        except Exception as e:
            print(f"❌ Error loading airports: {e}")
    
    def normalize_input(self, text: str) -> str:
        """Normalize input text for matching"""
        if not text:
            return ""
        
        normalized = text.strip().lower()
        
        # Remove common prefixes/suffixes
        normalized = normalized.replace(" airport", "")
        normalized = normalized.replace(" international", "")
        normalized = normalized.replace(" domestic", "")
        
        return normalized
    
    def get_iata_code(self, location: str) -> Optional[str]:
        """
        Get IATA code for a given location (city name or IATA code)
        
        Args:
            location: City name, alternative name, or IATA code
            
        Returns:
            Valid 3-letter IATA code or None
        """
        if not location:
            return None
        
        # Normalize input
        normalized = self.normalize_input(location)
        original_upper = location.strip().upper()
        
        # Strategy 1: Check if input is already a valid IATA code
        if len(original_upper) == 3 and original_upper in self.airports:
            print(f"✅ Direct IATA match: {location} -> {original_upper}")
            return original_upper
        
        # Strategy 2: Check alternative mappings first (handles common aliases)
        if normalized in self.alternative_mappings:
            canonical = self.alternative_mappings[normalized]
            print(f"🔄 Alternative name mapped: {location} -> {canonical}")
            
            # Now search for the canonical name
            if canonical in self.city_to_iata:
                iata = self.city_to_iata[canonical]
                print(f"✅ Found IATA for {canonical}: {iata}")
                return iata
        
        # Strategy 3: Direct city name lookup
        if normalized in self.city_to_iata:
            iata = self.city_to_iata[normalized]
            print(f"✅ Direct city match: {location} -> {iata}")
            return iata
        
        # Strategy 4: Fuzzy matching on city names
        best_match = self._fuzzy_match_city(normalized)
        if best_match:
            iata = self.city_to_iata[best_match]
            print(f"✅ Fuzzy match: {location} -> {best_match} -> {iata}")
            return iata
        
        # Strategy 5: Search in keywords
        for iata, airport in self.airports.items():
            keywords = airport.get("keywords", "").lower()
            if normalized in keywords:
                print(f"✅ Keyword match: {location} -> {iata}")
                return iata
        
        print(f"❌ No IATA code found for: {location}")
        return None
    
    def _fuzzy_match_city(self, query: str, threshold: float = 0.85) -> Optional[str]:
        """
        Fuzzy match city name using sequence matching
        
        Args:
            query: Normalized city name
            threshold: Minimum similarity score (0-1)
            
        Returns:
            Best matching city name or None
        """
        best_match = None
        best_score = 0.0
        
        for city in self.city_to_iata.keys():
            # Calculate similarity
            score = SequenceMatcher(None, query, city).ratio()
            
            # Also check if query is a substring or vice versa
            if query in city or city in query:
                score = max(score, 0.9)
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = city
        
        if best_match:
            print(f"🔍 Fuzzy match score: {best_score:.2f} - {query} ≈ {best_match}")
        
        return best_match
    
    def validate_and_fix_iata(self, origin: Optional[str], destination: Optional[str]) -> Dict[str, Optional[str] | bool]:
        """
        Validate and fix both origin and destination IATA codes
        
        Args:
            origin: Origin city/IATA
            destination: Destination city/IATA
            
        Returns:
            Dict with corrected origin and destination IATA codes and validation flags
        """
        print(f"\n{'='*70}")
        print("AIRPORT VALIDATION - START")
        print(f"{'='*70}")
        print(f"📍 Original Origin: {origin}")
        print(f"📍 Original Destination: {destination}")
        
        corrected_origin = None
        corrected_destination = None
        
        if origin:
            corrected_origin = self.get_iata_code(origin)
        
        if destination:
            corrected_destination = self.get_iata_code(destination)
        
        print(f"\n✅ Corrected Origin: {corrected_origin}")
        print(f"✅ Corrected Destination: {corrected_destination}")
        print(f"{'='*70}\n")
        
        return {
            "origin": corrected_origin,
            "destination": corrected_destination,
            "origin_valid": corrected_origin is not None,
            "destination_valid": corrected_destination is not None,
        }
    
    def get_airport_info(self, iata: str) -> Optional[Dict]:
        """Get full airport information by IATA code"""
        return self.airports.get(iata.upper())
    
    def get_city_name(self, iata: str) -> str:
        """Get city name for an IATA code"""
        airport = self.get_airport_info(iata)
        return airport["city"] if airport else iata


# Singleton instance
_validator_instance: Optional[AirportValidator] = None


def get_airport_validator(csv_path: str = "data/airports.csv") -> AirportValidator:
    """Get or create singleton airport validator instance"""
    global _validator_instance
    
    if _validator_instance is None:
        _validator_instance = AirportValidator(csv_path)
    
    return _validator_instance


# Testing
if __name__ == "__main__":
    print("🧪 Testing Airport Validator\n")
    
    validator = AirportValidator("airports.csv")
    
    test_cases = [
        "Calicut",
        "Kozhikode",
        "CCJ",
        "Mumbai",
        "Bombay",
        "BOM",
        "Bangalore",
        "Bengaluru",
        "BLR",
        "Kochi",
        "Cochin",
        "COK",
        "Delhi",
        "DEL",
        "Chennai",
        "Madras",
        "MUM",  # Should map to Mumbai
        "Navi Mumbai",
    ]
    
    print("Testing individual lookups:")
    print("-" * 70)
    for test in test_cases:
        result = validator.get_iata_code(test)
        print(f"{test:20} -> {result}")
    
    print("\n\nTesting origin/destination validation:")
    print("-" * 70)
    
    test_pairs = [
        ("Calicut", "Bangalore"),
        ("Bombay", "Delhi"),
        ("CCJ", "BLR"),
        ("Cochin", "Mumbai"),
        ("MUM", "Kochi"),
    ]
    
    for origin, dest in test_pairs:
        result = validator.validate_and_fix_iata(origin, dest)
        print(f"{origin} -> {dest}")
        print(f"  Result: {result}")
        print()