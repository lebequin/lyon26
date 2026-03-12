"""
Importe un CSV généré par extract_election.py dans la base de données.

Usage:
    python3 manage.py import_election_csv election_2024_legi_t1_arr05.csv
"""
import csv
import sys
from django.core.management.base import BaseCommand, CommandError
from mobilisation.models import Election, Nuance, ElectionParticipation, NuanceResult
from territory.models import VotingDesk


class Command(BaseCommand):
    help = "Importe un CSV d'élection généré localement par extract_election.py"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Chemin vers le fichier CSV à importer')
        parser.add_argument('--dry-run', action='store_true', help='Simule sans écrire en base')

    def handle(self, *args, **options):
        csv_path = options['csv_file']
        dry_run = options['dry_run']

        try:
            with open(csv_path, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
        except FileNotFoundError:
            raise CommandError(f"Fichier introuvable : {csv_path}")

        if not rows:
            raise CommandError("Fichier CSV vide.")

        # --- Parse metadata row ---
        meta = rows[0]
        if not meta or meta[0] != '#election':
            raise CommandError("Ligne de métadonnées manquante (doit commencer par #election).")

        id_election = meta[1]
        label = meta[2]
        type_el = meta[3]
        tour = meta[4]
        year = meta[5]

        self.stdout.write(f"Election : {label} ({id_election})")

        # --- Get or create Election ---
        if not dry_run:
            election, created = Election.objects.update_or_create(
                id_election=id_election,
                defaults={
                    'label': label,
                    'type_election': type_el,
                    'tour': tour,
                    'year': int(year),
                }
            )
            action = "créée" if created else "mise à jour"
            self.stdout.write(f"  Election {action} : {election}")
        else:
            self.stdout.write(f"  [dry-run] Election : {id_election}")

        # --- Process data rows (skip header row at index 1) ---
        data_rows = rows[2:]  # skip #election meta + header

        part_created = part_updated = 0
        res_created = res_updated = 0
        skipped_desks = set()

        for row in data_rows:
            if not row or len(row) < 7:
                continue

            record_type = row[0]
            bureau_code = row[1]

            try:
                desk = VotingDesk.objects.get(code=bureau_code)
            except VotingDesk.DoesNotExist:
                skipped_desks.add(bureau_code)
                continue

            if record_type == 'participation':
                abs_pct = float(row[5]) if row[5] else 0.0
                blancs_pct = float(row[6]) if row[6] else 0.0

                if not dry_run:
                    _, created = ElectionParticipation.objects.update_or_create(
                        election=election,
                        voting_desk=desk,
                        defaults={
                            'abstention_percent': abs_pct,
                            'blancs_percent': blancs_pct,
                        }
                    )
                    if created:
                        part_created += 1
                    else:
                        part_updated += 1
                else:
                    part_created += 1

            elif record_type == 'result':
                nuance_code = row[2]
                nuance_label = row[3]
                score = float(row[4]) if row[4] else 0.0

                if not nuance_code:
                    continue

                if not dry_run:
                    nuance, _ = Nuance.objects.get_or_create(
                        code=nuance_code,
                        defaults={'label': nuance_label, 'color': '#6b7280'}
                    )
                    _, created = NuanceResult.objects.update_or_create(
                        election=election,
                        voting_desk=desk,
                        nuance=nuance,
                        defaults={'ratio_voix_exprimes': score}
                    )
                    if created:
                        res_created += 1
                    else:
                        res_updated += 1
                else:
                    res_created += 1

        if skipped_desks:
            self.stdout.write(
                self.style.WARNING(f"  {len(skipped_desks)} bureaux ignorés (non trouvés) : {sorted(skipped_desks)}")
            )

        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(f"  {prefix}Participation : {part_created} créées, {part_updated} mises à jour")
        self.stdout.write(f"  {prefix}Résultats : {res_created} créés, {res_updated} mis à jour")
        self.stdout.write(self.style.SUCCESS(f"\n  Import terminé : {id_election}"))
