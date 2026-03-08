from django.core.management.base import BaseCommand
from territory.models import Building


class Command(BaseCommand):
    help = "Remet is_finished=False sur les adresses sans visite"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Affiche les adresses concernées sans modifier la base",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        buildings = Building.objects.filter(is_finished=True, visits__isnull=True)
        count = buildings.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("Aucune adresse à corriger."))
            return

        for b in buildings:
            self.stdout.write(f"  - {b} (bureau {b.voting_desk.code if b.voting_desk else 'N/A'})")

        if dry_run:
            self.stdout.write(self.style.WARNING(f"\n[dry-run] {count} adresse(s) seraient remises à is_finished=False."))
        else:
            buildings.update(is_finished=False)
            self.stdout.write(self.style.SUCCESS(f"\n{count} adresse(s) remises à is_finished=False."))
