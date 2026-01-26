import os
import django
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lyon26.settings")
django.setup()

from mobilisation.models import Address
from mobilisation.services import geocode_address

print("Refreshing geocoding for addresses without coordinates...")
addresses = Address.objects.filter(latitude__isnull=True)
print(f"Found {addresses.count()} addresses to update.")

for a in addresses:
    print(f"Geocoding {a} ({a.address}, {a.city})...")
    coords = geocode_address(a.address, a.city)
    if coords:
        a.latitude, a.longitude = coords
        a.save()
        print(f"Updated: {coords}")
    else:
        print("Failed to geocode.")
    
    # Respect rate limit just in case (though service handles it)
    time.sleep(1.1)

print("Done.")
