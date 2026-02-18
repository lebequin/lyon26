"""
Management command to mark buildings as HLM (social housing) using RPLS data.

The command can either:
  1. Read a pre-downloaded CSV from extract_hlm_lyon.py
  2. Download RPLS data directly from data.gouv.fr

Usage:
    # Download and mark automatically
    python manage.py mark_hlm_buildings

    # Use a pre-downloaded CSV (output of extract_hlm_lyon.py)
    python manage.py mark_hlm_buildings --input hlm_lyon.csv

    # Preview without making changes
    python manage.py mark_hlm_buildings --input hlm_lyon.csv --dry-run

    # Also export the matched buildings to a CSV
    python manage.py mark_hlm_buildings --input hlm_lyon.csv --export hlm_immeubles.csv

    # Reset all is_hlm flags before marking
    python manage.py mark_hlm_buildings --input hlm_lyon.csv --reset
"""
import csv
import io
import re
import zipfile
import urllib.request
import urllib.error
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from territory.models import Building


DATASET_ID = (
    "donnees-detaillees-au-logement-du-repertoire-des-logements-locatifs-des-bailleurs-sociaux-rpls"
)
FALLBACK_URLS = [
    "https://static.data.gouv.fr/resources/donnees-detaillees-au-logement-du-repertoire-des-logements-locatifs-des-bailleurs-sociaux-rpls/20240409-150156/rpls2023logement.zip",
]
LYON_INSEE_CODES = {
    "69381", "69382", "69383", "69384", "69385",
    "69386", "69387", "69388", "69389", "69123",
}


def _get_field(row, *keys):
    for key in keys:
        val = row.get(key)
        if val is not None:
            return str(val).strip()
    return ""


def normalize_street(name):
    """Normalize a street name for fuzzy comparison."""
    name = name.upper().strip()
    # Remove common abbreviations differences
    replacements = [
        (r"\bST\b", "SAINT"),
        (r"\bSTE\b", "SAINTE"),
        (r"\bBD\b", "BOULEVARD"),
        (r"\bAV\b", "AVENUE"),
        (r"\bAVE\b", "AVENUE"),
        (r"\bRTE\b", "ROUTE"),
        (r"\bIMP\b", "IMPASSE"),
        (r"\bPL\b", "PLACE"),
        (r"\bALL\b", "ALLEE"),
        (r"\bCHE\b", "CHEMIN"),
        (r"-", " "),
    ]
    for pattern, replacement in replacements:
        name = re.sub(pattern, replacement, name)
    # Collapse multiple spaces
    name = re.sub(r"\s+", " ", name).strip()
    return name


def build_hlm_set(rows):
    """
    Build a set of (street_number, normalized_street_name) from RPLS rows.
    Also returns a dict for more details.
    """
    hlm_addresses = set()
    hlm_details = {}

    for row in rows:
        num_voie = _get_field(row, "Numéro", "numvoie", "NUMVOIE", "num_voie")
        typ_voie = _get_field(row, "Type de voie", "typvoie", "TYPVOIE", "typ_voie")
        nom_voie = _get_field(row, "Nom de voie", "nomvoie", "NOMVOIE", "nom_voie")
        adresse = _get_field(row, "Adresse")

        if adresse:
            # Already formatted address from extract_hlm_lyon.py output
            parts = adresse.split(" ", 1)
            if parts[0].isdigit() or (len(parts) > 1 and parts[0].rstrip("ABCDEFG").isdigit()):
                key = (parts[0], normalize_street(parts[1] if len(parts) > 1 else ""))
            else:
                key = ("", normalize_street(adresse))
        else:
            full_nom = f"{typ_voie} {nom_voie}".strip() if typ_voie else nom_voie
            key = (num_voie, normalize_street(full_nom))

        hlm_addresses.add(key)
        hlm_details[key] = row

    return hlm_addresses, hlm_details


def download_rpls():
    """Download RPLS data from data.gouv.fr and return CSV content (bytes)."""
    # Try API first
    url = None
    try:
        api_url = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_ID}/"
        req = urllib.request.Request(api_url, headers={"User-Agent": "django-lyon26/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        resources = data.get("resources", [])
        candidates = [
            r for r in resources
            if r.get("format", "").lower() in ("csv", "zip")
        ]
        if candidates:
            latest = sorted(candidates, key=lambda r: r.get("created_at", ""), reverse=True)[0]
            url = latest["url"]
    except Exception:
        url = FALLBACK_URLS[0] if FALLBACK_URLS else None

    if not url:
        raise CommandError("Impossible de trouver l'URL des données RPLS")

    req = urllib.request.Request(url, headers={"User-Agent": "django-lyon26/1.0"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        content = resp.read()

    if url.endswith(".zip") or content[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                raise CommandError("Aucun CSV dans le ZIP RPLS")
            content = zf.read(csv_names[0])

    return content


def parse_csv_content(content, communes=None):
    """Parse RPLS CSV content and filter by commune codes."""
    for encoding in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = content.decode("latin-1", errors="replace")

    first_line = text.split("\n")[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    rows = []
    for row in reader:
        if communes:
            code_com = _get_field(
                row,
                "codecom", "CODECOM", "code_commune", "Code commune",
                "depcom", "DEPCOM",
            )
            if code_com not in communes and not any(
                code_com.endswith(c[-3:]) and c in communes for c in communes
            ):
                continue
        rows.append(row)
    return rows


class Command(BaseCommand):
    help = "Mark buildings as HLM (social housing) using RPLS open data from data.gouv.fr."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            metavar="FILE",
            help=(
                "CSV file of HLM addresses (output of extract_hlm_lyon.py). "
                "If omitted, downloads from data.gouv.fr automatically."
            ),
        )
        parser.add_argument(
            "--export",
            metavar="FILE",
            help="Export matched HLM buildings to this CSV file.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset all is_hlm=False before applying new data.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show results without saving to the database.",
        )

    def handle(self, *args, **options):
        input_file = options["input"]
        export_file = options["export"]
        dry_run = options["dry_run"]
        reset = options["reset"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — aucun changement en base"))

        # --- Load HLM address data ---
        if input_file:
            path = Path(input_file)
            if not path.exists():
                raise CommandError(f"Fichier introuvable: {input_file}")
            self.stdout.write(f"Lecture de {input_file}...")
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rpls_rows = list(reader)
            self.stdout.write(f"  {len(rpls_rows)} adresses HLM chargées")
        else:
            self.stdout.write("Téléchargement des données RPLS depuis data.gouv.fr...")
            try:
                content = download_rpls()
                rpls_rows = parse_csv_content(content, LYON_INSEE_CODES)
                self.stdout.write(f"  {len(rpls_rows)} adresses HLM Lyon téléchargées")
            except (urllib.error.URLError, Exception) as e:
                raise CommandError(
                    f"Téléchargement échoué: {e}\n"
                    "Conseil: téléchargez d'abord le fichier manuellement avec extract_hlm_lyon.py "
                    "puis relancez avec --input hlm_lyon.csv"
                )

        if not rpls_rows:
            self.stdout.write(self.style.WARNING("Aucune donnée HLM — vérifiez le fichier ou les filtres."))
            return

        hlm_set, _ = build_hlm_set(rpls_rows)
        self.stdout.write(f"  {len(hlm_set)} adresses uniques à comparer")

        # --- Reset if requested ---
        if reset and not dry_run:
            count = Building.objects.filter(is_hlm=True).count()
            Building.objects.all().update(is_hlm=False)
            self.stdout.write(f"  Réinitialisation: {count} immeubles remis à is_hlm=False")

        # --- Match buildings ---
        buildings = Building.objects.select_related("voting_desk").all()
        matched = []
        unmatched_hlm = 0

        for building in buildings:
            num = building.street_number.strip()
            street_norm = normalize_street(building.street_name)

            hit = False
            # Exact match
            if (num, street_norm) in hlm_set:
                hit = True
            # Match without street number (entire building block is HLM)
            elif ("", street_norm) in hlm_set:
                hit = True
            # Try partial: just street name without number
            else:
                for (hlm_num, hlm_street) in hlm_set:
                    if hlm_street == street_norm and (not hlm_num or hlm_num == num):
                        hit = True
                        break

            if hit:
                matched.append(building)
                if not dry_run:
                    building.is_hlm = True
                    building.save(update_fields=["is_hlm"])

        # --- Report ---
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{len(matched)} immeuble(s) identifié(s) comme HLM"
                f" sur {buildings.count()} immeubles en base"
            )
        )
        for b in matched:
            self.stdout.write(f"  [HLM] {b.street_number} {b.street_name} (bureau {b.voting_desk.code})")

        # --- Export CSV ---
        if export_file and matched:
            export_path = Path(export_file)
            with open(export_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Numéro", "Rue", "Bureau de vote", "Arrondissement",
                    "Nb électeurs", "Latitude", "Longitude",
                ])
                for b in sorted(matched, key=lambda x: (x.street_name, x.street_number)):
                    writer.writerow([
                        b.street_number,
                        b.street_name,
                        b.voting_desk.code,
                        b.voting_desk.district.name if hasattr(b.voting_desk, "district") else "",
                        b.num_electors,
                        b.latitude or "",
                        b.longitude or "",
                    ])
            self.stdout.write(self.style.SUCCESS(f"Export: {export_path} ({len(matched)} lignes)"))
