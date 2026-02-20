"""
Import HLM (social housing) data and mark matching buildings.

Usage:
    python manage.py import_hlm hlm_lyon5_manual.csv
    python manage.py import_hlm hlm_lyon5_manual.csv --dry-run
"""
import csv
from django.core.management.base import BaseCommand
from territory.models import Building


class Command(BaseCommand):
    help = 'Import HLM data from CSV and mark matching buildings as social housing'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', help='Path to the HLM CSV file (street_number;street_name)')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )

    def normalize_street(self, street):
        """Normalize street name for comparison."""
        if not street:
            return ''
        # Lowercase, remove extra spaces
        s = street.lower().strip()
        s = ' '.join(s.split())
        # Remove accents for comparison
        replacements = {
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'à': 'a', 'â': 'a', 'ä': 'a',
            'ù': 'u', 'û': 'u', 'ü': 'u',
            'î': 'i', 'ï': 'i',
            'ô': 'o', 'ö': 'o',
            'ç': 'c',
        }
        for a, b in replacements.items():
            s = s.replace(a, b)
        return s

    def normalize_number(self, num):
        """Normalize street number for comparison."""
        if not num:
            return ''
        # Extract numeric part and suffix
        num = str(num).lower().strip()
        return num

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']

        # Load HLM addresses from CSV
        hlm_entries = []  # List of (number, street, normalized_street, normalized_number)
        with open(csv_file, 'r', encoding='utf-8') as f:
            # Detect delimiter
            first_line = f.readline()
            f.seek(0)
            delimiter = ';' if ';' in first_line else ','

            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                street = row.get('street_name', '').strip()
                number = row.get('street_number', '').strip()
                if street and number:
                    hlm_entries.append((
                        number,
                        street,
                        self.normalize_street(street),
                        self.normalize_number(number)
                    ))

        self.stdout.write(f"\nCSV entries: {len(hlm_entries)}")

        # Build lookup from buildings
        buildings_lookup = {}  # {(norm_street, norm_number): building}
        for building in Building.objects.all():
            key = (
                self.normalize_street(building.street_name),
                self.normalize_number(building.street_number)
            )
            buildings_lookup[key] = building

        # Process entries
        matched = 0
        already_hlm = 0
        skipped = []

        for number, street, norm_street, norm_number in hlm_entries:
            key = (norm_street, norm_number)
            building = buildings_lookup.get(key)

            if building:
                if building.is_hlm:
                    already_hlm += 1
                else:
                    matched += 1
                    if not dry_run:
                        building.is_hlm = True
                        building.save(update_fields=['is_hlm'])
                    self.stdout.write(self.style.SUCCESS(
                        f"  {'[DRY-RUN] ' if dry_run else ''}Marked as HLM: {number} {street}"
                    ))
            else:
                skipped.append(f"{number} {street}")

        # Summary
        self.stdout.write(f"\n{'[DRY-RUN] ' if dry_run else ''}Results:")
        self.stdout.write(f"  - CSV entries: {len(hlm_entries)}")
        self.stdout.write(self.style.SUCCESS(f"  - Marked as HLM: {matched}"))
        self.stdout.write(f"  - Already HLM: {already_hlm}")
        self.stdout.write(self.style.WARNING(f"  - Skipped (not found): {len(skipped)}"))

        if skipped:
            self.stdout.write(self.style.WARNING(f"\nSkipped addresses (not in database):"))
            for addr in skipped:
                self.stdout.write(f"  - {addr}")
