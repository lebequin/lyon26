"""
Management command to import buildings from CSV files.

Usage:
    python manage.py import_buildings /path/to/502.csv
    python manage.py import_buildings /path/to/*.csv
    python manage.py import_buildings /path/to/502.csv --district-code 5

The voting desk code is extracted from the filename (e.g., 502.csv -> code "502").
"""
import csv
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from territory.models import District, VotingDesk, Building


class Command(BaseCommand):
    help = 'Import buildings from CSV files. Filename is used as voting desk code.'

    def add_arguments(self, parser):
        parser.add_argument(
            'files',
            nargs='+',
            help='CSV file(s) to import. Filename (without extension) is the voting desk code.'
        )
        parser.add_argument(
            '--district-code',
            type=str,
            default=None,
            help='District code to use. If not provided, extracts first digit(s) from voting desk code.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without making changes.'
        )

    def handle(self, *args, **options):
        files = options['files']
        district_code = options['district_code']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))

        total_created = 0
        total_updated = 0

        for filepath in files:
            path = Path(filepath)
            if not path.exists():
                self.stderr.write(self.style.ERROR(f'File not found: {filepath}'))
                continue

            voting_desk_code = path.stem  # filename without extension
            created, updated = self.import_file(path, voting_desk_code, district_code, dry_run)
            total_created += created
            total_updated += updated

        self.stdout.write(self.style.SUCCESS(
            f'Import complete: {total_created} created, {total_updated} updated'
        ))

    def import_file(self, filepath, voting_desk_code, district_code, dry_run):
        """Import a single CSV file."""
        self.stdout.write(f'Processing {filepath} (voting desk: {voting_desk_code})...')

        # Determine district code from voting desk code if not provided
        if district_code is None:
            # Extract first digit(s) as district (e.g., 502 -> 5, 1201 -> 12)
            district_code = voting_desk_code[0] if len(voting_desk_code) <= 3 else voting_desk_code[:2]

        if dry_run:
            self.stdout.write(f'  Would use district code: {district_code}')
        else:
            # Get or create district
            district, created = District.objects.get_or_create(
                code=district_code,
                defaults={'name': f'Arrondissement {district_code}'}
            )
            if created:
                self.stdout.write(f'  Created district: {district}')

            # Get or create voting desk
            voting_desk, created = VotingDesk.objects.get_or_create(
                code=voting_desk_code,
                defaults={
                    'name': f'Bureau {voting_desk_code}',
                    'location': '',
                    'district': district
                }
            )
            if created:
                self.stdout.write(f'  Created voting desk: {voting_desk}')

        # Read and import CSV
        created_count = 0
        updated_count = 0

        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                street_number = row.get('N° rue', '').strip()
                street_name = row.get('Nom rue', '').strip()
                num_electors_str = row.get('Nb electeurs', '0').strip()

                # Parse electors count
                try:
                    num_electors = int(num_electors_str) if num_electors_str else 0
                except ValueError:
                    num_electors = 0

                if not street_number or not street_name:
                    continue

                if dry_run:
                    self.stdout.write(
                        f'  Would import: {street_number} {street_name} ({num_electors} electors)'
                    )
                    created_count += 1
                else:
                    with transaction.atomic():
                        building, created = Building.objects.update_or_create(
                            voting_desk=voting_desk,
                            street_number=street_number,
                            street_name=street_name,
                            defaults={'num_electors': num_electors}
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

        self.stdout.write(
            f'  {filepath.name}: {created_count} created, {updated_count} updated'
        )
        return created_count, updated_count
