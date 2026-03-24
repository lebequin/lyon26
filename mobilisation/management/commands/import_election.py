"""
Import election results from the French government open data API.

Usage:
    python3 manage.py import_election 2020 muni t1 05
    python3 manage.py import_election 2024 euro t1 05
    python3 manage.py import_election 2024 légi t2 05

Data source: https://tabular-api.data.gouv.fr
"""
import requests
import io
from urllib.parse import urlencode

import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from mobilisation.models import Election, Nuance, ElectionParticipation, NuanceResult
from territory.models import VotingDesk

PARTICIPATION_URL = "https://tabular-api.data.gouv.fr/api/resources/b8703c69-a18f-46ab-9e7f-3a8368dcb891/data/csv/"
RESULTS_PARQUET_URL = "https://object.files.data.gouv.fr/data-pipeline-open/elections/candidats_results.parquet"

TYPE_LABELS = {
    'muni': 'Municipales',
    'euro': 'Européennes',
    'légi': 'Législatives',
    'pres': 'Présidentielles',
    'cant': 'Cantonales',
    'regi': 'Régionales',
}


def miom_to_desk_code(id_brut_miom):
    """Convert '69123_0501' → '501'"""
    suffix = id_brut_miom.split('_')[-1]  # '0501'
    return str(int(suffix))               # '501'


class Command(BaseCommand):
    help = "Importe les résultats électoraux depuis l'API data.gouv.fr"

    def add_arguments(self, parser):
        parser.add_argument('year', type=int, help="Année (ex: 2020)")
        parser.add_argument('type_election', type=str, help="Type: muni, euro, légi, pres, cant, regi")
        parser.add_argument('tour', type=str, help="Tour: t1 ou t2")
        parser.add_argument('arrondissement', type=str, help="Arrondissement Lyon (ex: 05)")
        parser.add_argument('--label', type=str, default='', help="Libellé personnalisé de l'élection")
        parser.add_argument('--dry-run', action='store_true', help="Affiche sans sauvegarder")

    def handle(self, *args, **options):
        year = options['year']
        type_el = options['type_election']
        tour = options['tour']
        arr = options['arrondissement']
        dry_run = options['dry_run']

        election_code = f"{year}_{type_el}_{tour}"
        type_label = TYPE_LABELS.get(type_el, type_el.capitalize())
        tour_label = "T1" if tour == 't1' else "T2"
        election_name = options['label'] or f"{type_label} {year} {tour_label}"

        self.stdout.write(f"\nImport : {election_name} ({election_code}) — arr. {arr}")

        # --- Fetch participation ---
        self.stdout.write("  Récupération de la participation...")
        params = {
            "id_brut_miom__contains": f"69123_{arr}",
            "id_election__contains": election_code,  # paramètre API data.gouv.fr
        }
        url = f"{PARTICIPATION_URL}?{urlencode(params)}"
        self.stdout.write(f"  URL: {url}")
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            raise CommandError(f"Erreur API participation: {resp.status_code}")

        if not resp.text.strip():
            raise CommandError(
                f"L'API a renvoyé une réponse vide pour '{election_code}'.\n"
                f"Vérifiez l'identifiant exact sur https://tabular-api.data.gouv.fr/"
                f"api/resources/b8703c69-a18f-46ab-9e7f-3a8368dcb891/data/csv/"
                f"?id_brut_miom__contains=69123_{arr}&page_size=5"
            )

        try:
            df_part = pd.read_csv(io.StringIO(resp.text))
        except Exception as e:
            raise CommandError(
                f"Impossible de parser la réponse CSV : {e}\n"
                f"Début de la réponse : {resp.text[:300]}"
            )

        if df_part.empty:
            raise CommandError(
                f"Aucun bureau trouvé pour '{election_code}' / arrondissement '{arr}'.\n"
                f"Vérifiez le type d'élection (muni, euro, légi, pres) et l'arrondissement."
            )

        self.stdout.write(f"  {len(df_part)} bureaux récupérés (participation)")

        # --- Fetch results ---
        # Download via requests (handles macOS SSL certs) then pass bytes to pandas
        self.stdout.write("  Récupération des résultats par nuance (parquet)...")
        resp_parquet = requests.get(RESULTS_PARQUET_URL, timeout=120)
        if resp_parquet.status_code != 200:
            raise CommandError(f"Erreur téléchargement parquet: {resp_parquet.status_code}")
        df_res = pd.read_parquet(
            io.BytesIO(resp_parquet.content),
            engine="pyarrow",
            columns=["id_election", "id_brut_miom", "nuance", "libelle_abrege_liste", "ratio_voix_exprimes"]
        )
        df_res = df_res[
            (df_res["id_election"] == election_code) &  # colonne parquet data.gouv.fr
            (df_res["id_brut_miom"].str.startswith(f"69123_{arr}"))
        ]
        self.stdout.write(f"  {len(df_res)} lignes de résultats par nuance")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[dry-run] Aucune donnée sauvegardée."))
            self.stdout.write("Nuances trouvées : " + ", ".join(df_res['nuance'].unique()))
            return

        # --- Get or create Election ---
        election, created = Election.objects.get_or_create(
            election_code=election_code,
            defaults={
                'election_type': type_el,
                'round': tour,
                'year': year,
                'name': election_name,
            }
        )
        action = "créée" if created else "existante"
        self.stdout.write(f"  Election {action} : {election}")

        # --- Auto-create Nuances ---
        nuance_codes = df_res['nuance'].dropna().unique()
        for code in nuance_codes:
            # Use libelle_abrege_liste if available for first occurrence
            rows = df_res[df_res['nuance'] == code]
            libelle = rows['libelle_abrege_liste'].dropna().iloc[0] if not rows['libelle_abrege_liste'].dropna().empty else code
            Nuance.objects.get_or_create(code=code, defaults={'label': str(libelle)})

        nuances_map = {n.code: n for n in Nuance.objects.filter(code__in=nuance_codes)}

        # --- Import per bureau ---
        created_part, updated_part = 0, 0
        created_res, updated_res = 0, 0
        skipped = 0

        for _, row in df_part.iterrows():
            desk_code = miom_to_desk_code(row['id_brut_miom'])
            try:
                desk = VotingDesk.objects.get(code=desk_code)
            except VotingDesk.DoesNotExist:
                skipped += 1
                continue

            abstention = row['ratio_abstentions_inscrits'] if 'ratio_abstentions_inscrits' in df_part.columns else 0
            blancs = row['ratio_blancs_votants'] if 'ratio_blancs_votants' in df_part.columns else 0

            obj, was_created = ElectionParticipation.objects.update_or_create(
                election=election,
                voting_desk=desk,
                defaults={
                    'abstention_percent': float(abstention) if abstention == abstention else 0,  # NaN check
                    'blank_percent': float(blancs) if blancs == blancs else 0,
                }
            )
            if was_created:
                created_part += 1
            else:
                updated_part += 1

        # Group results by bureau + nuance and sum ratios
        df_agg = df_res.groupby(['id_brut_miom', 'nuance'])['ratio_voix_exprimes'].sum().reset_index()

        for _, row in df_agg.iterrows():
            desk_code = miom_to_desk_code(row['id_brut_miom'])
            nuance = nuances_map.get(row['nuance'])
            if not nuance:
                continue
            try:
                desk = VotingDesk.objects.get(code=desk_code)
            except VotingDesk.DoesNotExist:
                continue

            obj, was_created = NuanceResult.objects.update_or_create(
                election=election,
                voting_desk=desk,
                nuance=nuance,
                defaults={'vote_share': float(row['ratio_voix_exprimes'] or 0)}  # 'ratio_voix_exprimes' = col. parquet
            )
            if was_created:
                created_res += 1
            else:
                updated_res += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé :\n"
            f"  Participation : {created_part} créées, {updated_part} mises à jour\n"
            f"  Résultats nuances : {created_res} créés, {updated_res} mis à jour\n"
            f"  Bureaux introuvables : {skipped}"
        ))
