import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lyon26.settings")
django.setup()

from mobilisation.models import Address

print(f"Total addresses: {Address.objects.count()}")
for a in Address.objects.all():
    print(f"Address: {a} | Coords: {a.latitude}, {a.longitude}")
