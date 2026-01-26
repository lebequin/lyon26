"""
Management command to geocode buildings using Nominatim (OpenStreetMap).

Usage:
    python manage.py geocode_buildings                    # All buildings without coords
    python manage.py geocode_buildings --district 5       # Only district 5
    python manage.py geocode_buildings --voting-desk 502  # Only voting desk 502
    python manage.py geocode_buildings --force            # Re-geocode all (even with coords)
    python manage.py geocode_buildings --dry-run          # Preview without changes
"""
import time
import urllib.request
import urllib.parse
import json
import ssl

from django.core.management.base import BaseCommand

from territory.models import Building


class Command(BaseCommand):
    help = 'Geocode buildings to get latitude/longitude coordinates'

    # Rate limiting for Nominatim (1 req/sec)
    _last_request_time = 0

    def add_arguments(self, parser):
        parser.add_argument(
            '--district',
            type=str,
            help='Only geocode buildings in this district (by code)'
        )
        parser.add_argument(
            '--voting-desk',
            type=str,
            help='Only geocode buildings in this voting desk (by code)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-geocode buildings even if they already have coordinates'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be geocoded without making changes'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of buildings to geocode'
        )

    def _rate_limit(self):
        """Small delay between requests to avoid being blocked"""
        time.sleep(0.1)  # 100ms delay

    def _normalize_street_name(self, name):
        """Convert uppercase street name to title case."""
        # Convert to title case
        name = name.title()
        # Fix common French words that should be lowercase
        lowercase_words = [' De ', ' Du ', ' Des ', ' La ', ' Le ', ' Les ', " L'", " D'"]
        for word in lowercase_words:
            name = name.replace(word, word.lower())
        return name

    def _geocode(self, query):
        """Geocode an address query using Nominatim."""
        self._rate_limit()

        params = {
            'q': query,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'fr',
        }

        url = f"https://nominatim.openstreetmap.org/search?{urllib.parse.urlencode(params)}"

        try:
            request = urllib.request.Request(
                url,
                headers={'User-Agent': 'Lyon2026-Campaign/1.0'}
            )
            context = ssl._create_unverified_context()

            with urllib.request.urlopen(request, context=context, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

                if data and len(data) > 0:
                    result = data[0]
                    return (float(result['lat']), float(result['lon']))
        except Exception as e:
            pass

        return None

    def _try_geocode_building(self, building):
        """Try multiple address formats to geocode a building."""
        street_num = building.street_number
        street_name = self._normalize_street_name(building.street_name)

        # Try different query formats
        queries = [
            f"{street_num} {street_name}, Lyon 5e, France",
            f"{street_num} {street_name}, 69005 Lyon, France",
            f"{street_num} {street_name}, Lyon, France",
            f"{street_name}, Lyon 5e, France",  # Without number
        ]

        for query in queries:
            coords = self._geocode(query)
            if coords:
                # Verify it's roughly in Lyon area (lat ~45.7, lon ~4.8)
                if 45.5 < coords[0] < 46.0 and 4.5 < coords[1] < 5.2:
                    return coords

        return None

    def handle(self, *args, **options):
        district_code = options['district']
        voting_desk_code = options['voting_desk']
        force = options['force']
        dry_run = options['dry_run']
        limit = options['limit']

        # Build queryset
        queryset = Building.objects.select_related('voting_desk__district')

        if voting_desk_code:
            queryset = queryset.filter(voting_desk__code=voting_desk_code)
            self.stdout.write(f"Filtering by voting desk: {voting_desk_code}")
        elif district_code:
            queryset = queryset.filter(voting_desk__district__code=district_code)
            self.stdout.write(f"Filtering by district: {district_code}")

        if not force:
            queryset = queryset.filter(latitude__isnull=True)
            self.stdout.write("Only buildings without coordinates (use --force to re-geocode)")

        queryset = queryset.order_by('voting_desk__code', 'street_name', 'street_number')

        if limit:
            queryset = queryset[:limit]
            self.stdout.write(f"Limiting to {limit} buildings")

        buildings = list(queryset)
        total = len(buildings)

        if total == 0:
            self.stdout.write(self.style.WARNING("No buildings to geocode"))
            return

        self.stdout.write(f"Found {total} buildings to geocode")
        self.stdout.write("")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
            for bldg in buildings[:10]:
                street = self._normalize_street_name(bldg.street_name)
                self.stdout.write(f"  Would geocode: {bldg.street_number} {street}, Lyon")
            if total > 10:
                self.stdout.write(f"  ... and {total - 10} more")
            return

        # Geocode buildings
        success_count = 0
        fail_count = 0
        failed_addresses = []

        for i, building in enumerate(buildings, 1):
            street = self._normalize_street_name(building.street_name)
            self.stdout.write(f"[{i}/{total}] {building.street_number} {street}... ", ending='')
            self.stdout.flush()

            coords = self._try_geocode_building(building)

            if coords:
                building.latitude, building.longitude = coords
                building.save(update_fields=['latitude', 'longitude'])
                self.stdout.write(self.style.SUCCESS(f"OK ({coords[0]:.5f}, {coords[1]:.5f})"))
                success_count += 1
            else:
                self.stdout.write(self.style.ERROR("FAILED"))
                fail_count += 1
                failed_addresses.append(f"{building.street_number} {street}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Complete: {success_count} success, {fail_count} failed"))

        if failed_addresses and fail_count <= 20:
            self.stdout.write("")
            self.stdout.write("Failed addresses:")
            for addr in failed_addresses:
                self.stdout.write(f"  - {addr}")
