from mobilisation.services import geocode_address
import os
import django

print("Testing geocoding...")
try:
    result = geocode_address("10 avenue de ménival", "Lyon")
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")
