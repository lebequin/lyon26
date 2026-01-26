"""
Geocoding service using Nominatim (OpenStreetMap).
Free service with rate limiting (1 request per second).
"""
import urllib.request
import urllib.parse
import json
import time
import ssl


class GeocodingService:
    """Geocode addresses using Nominatim (OpenStreetMap)"""
    
    BASE_URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = "Lyon2026-Mobilisation/1.0"
    
    _last_request_time = 0
    
    @classmethod
    def _rate_limit(cls):
        """Ensure at least 1 second between requests (Nominatim policy)"""
        current_time = time.time()
        time_since_last = current_time - cls._last_request_time
        if time_since_last < 1.0:
            time.sleep(1.0 - time_since_last)
        cls._last_request_time = time.time()
    
    @classmethod
    def geocode(cls, address: str, city: str = "Lyon", country: str = "France") -> tuple[float, float] | None:
        """
        Geocode an address to latitude/longitude coordinates.
        
        Args:
            address: Street address (e.g., "15 Rue de la République")
            city: City name (default: "Lyon")
            country: Country name (default: "France")
            
        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        cls._rate_limit()
        
        # Build full query
        full_address = f"{address}, {city}, {country}"
        
        params = {
            'q': full_address,
            'format': 'json',
            'limit': 1,
            'addressdetails': 0
        }
        
        url = f"{cls.BASE_URL}?{urllib.parse.urlencode(params)}"
        
        try:
            request = urllib.request.Request(
                url,
                headers={'User-Agent': cls.USER_AGENT}
            )
            
            # Create unverified SSL context to handle missing certificates on macOS
            context = ssl._create_unverified_context()
            
            with urllib.request.urlopen(request, context=context, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                if data and len(data) > 0:
                    result = data[0]
                    lat = float(result['lat'])
                    lon = float(result['lon'])
                    return (lat, lon)
                    
        except Exception as e:
            print(f"Geocoding error for '{full_address}': {e}")
            
        return None


def geocode_address(address: str, city: str = "Lyon") -> tuple[float, float] | None:
    """
    Convenience function to geocode an address.
    
    Args:
        address: Street address
        city: City name (default: "Lyon")
        
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    return GeocodingService.geocode(address, city)
