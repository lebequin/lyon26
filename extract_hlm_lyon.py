#!/usr/bin/env python3
"""
Extraction des adresses de logements sociaux (HLM) à Lyon
depuis les données RPLS (Répertoire des logements locatifs des bailleurs sociaux)
publiées en open data sur data.gouv.fr — source utilisée par urbi-explore.fr/hlm.

Usage:
    python extract_hlm_lyon.py
    python extract_hlm_lyon.py --arrondissement 5
    python extract_hlm_lyon.py --output hlm_lyon5.csv
    python extract_hlm_lyon.py --financement PLAI PLUS

Codes de financement:
    PLAI  : Prêt Locatif Aidé d'Intégration (très social, loyers les plus bas)
    PLUS  : Prêt Locatif à Usage Social (logement social standard)
    PLS   : Prêt Locatif Social (intermédiaire)
    PLI   : Prêt Locatif Intermédiaire
    LLTS  : Logement locatif très social
"""

import csv
import io
import sys
import argparse
import zipfile
import urllib.request
import urllib.error
import json

# Codes INSEE des arrondissements de Lyon
LYON_INSEE_CODES = {
    1: "69381",
    2: "69382",
    3: "69383",
    4: "69384",
    5: "69385",
    6: "69386",
    7: "69387",
    8: "69388",
    9: "69389",
}

# ID du jeu de données RPLS détaillé sur data.gouv.fr
DATASET_ID = "donnees-detaillees-au-logement-du-repertoire-des-logements-locatifs-des-bailleurs-sociaux-rpls"

# URLs de secours si l'API est inaccessible
FALLBACK_URLS = [
    "https://static.data.gouv.fr/resources/donnees-detaillees-au-logement-du-repertoire-des-logements-locatifs-des-bailleurs-sociaux-rpls/20240409-150156/rpls2023logement.zip",
    "https://static.data.gouv.fr/resources/rpls-donnees-detaillees-au-1-janvier-2022/20230331-100039/rpls2022logement.zip",
]


def get_rpls_download_url():
    """Récupère l'URL de téléchargement du dernier fichier RPLS via l'API data.gouv.fr."""
    api_url = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_ID}/"
    print(f"Interrogation de l'API data.gouv.fr...")
    req = urllib.request.Request(api_url, headers={"User-Agent": "python-extract-hlm/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    resources = data.get("resources", [])
    # Cherche les fichiers CSV ou ZIP
    candidates = [
        r for r in resources
        if r.get("format", "").lower() in ("csv", "zip")
        and "logement" in r.get("title", "").lower()
    ]
    if not candidates:
        candidates = [r for r in resources if r.get("format", "").lower() in ("csv", "zip")]

    if not candidates:
        raise ValueError("Aucune ressource CSV/ZIP trouvée dans le jeu de données")

    # Prend la plus récente
    latest = sorted(candidates, key=lambda r: r.get("created_at", ""), reverse=True)[0]
    return latest["url"], latest.get("title", "")


def download_data(url):
    """Télécharge le fichier (CSV ou ZIP) et retourne le contenu CSV en bytes."""
    print(f"Téléchargement: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "python-extract-hlm/1.0"})
    with urllib.request.urlopen(req, timeout=300) as response:
        content = response.read()

    # Si c'est un ZIP, extrait le CSV
    if url.endswith(".zip") or content[:2] == b"PK":
        print("Extraction du ZIP...")
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError("Aucun fichier CSV dans le ZIP")
            print(f"  Fichier trouvé: {csv_names[0]}")
            content = zf.read(csv_names[0])

    return content


def _get_field(row, *keys):
    """Cherche une valeur dans un dict en testant plusieurs noms de colonnes."""
    for key in keys:
        val = row.get(key)
        if val is not None:
            return str(val).strip()
    return ""


def parse_rpls(content, communes):
    """Parse le CSV RPLS et retourne les adresses filtrées par communes."""
    # Le RPLS utilise souvent l'encodage latin-1 et le séparateur point-virgule
    for encoding in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = content.decode("latin-1", errors="replace")

    # Détecte le séparateur
    first_line = text.split("\n")[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    addresses = []
    total_rows = 0
    for row in reader:
        total_rows += 1

        # Code commune (plusieurs noms possibles selon le millésime)
        code_com = _get_field(
            row,
            "codecom", "CODECOM", "code_commune", "Code commune",
            "depcom", "DEPCOM",
        )
        # Parfois le code est préfixé par le département (ex: "69385")
        # ou préfixé différemment — on cherche dans les 5 derniers chiffres
        matched = code_com in communes or any(
            code_com.endswith(c[-3:]) and c in communes
            for c in communes
        )
        if not matched:
            continue

        num_voie = _get_field(row, "numvoie", "NUMVOIE", "num_voie", "Numéro de voie", "numero_voie")
        typ_voie = _get_field(row, "typvoie", "TYPVOIE", "typ_voie", "Type de voie", "type_voie")
        nom_voie = _get_field(row, "nomvoie", "NOMVOIE", "nom_voie", "Nom de voie", "nom_rue")
        code_postal = _get_field(row, "codepostal", "CODEPOSTAL", "code_postal", "Code postal")
        finan = _get_field(row, "finan", "FINAN", "financement", "Financement", "typefinanc")
        lat = _get_field(row, "lat", "LAT", "latitude", "Latitude")
        lon = _get_field(row, "lon", "LON", "longitude", "Longitude")

        if not nom_voie:
            continue

        # Reconstitue l'adresse complète façon BAN
        full_nom = f"{typ_voie} {nom_voie}".strip() if typ_voie else nom_voie
        full_address = f"{num_voie} {full_nom}".strip() if num_voie else full_nom

        addresses.append({
            "Numéro": num_voie,
            "Type de voie": typ_voie,
            "Nom de voie": nom_voie,
            "Adresse": full_address,
            "Code postal": code_postal,
            "Code commune": code_com,
            "Financement": finan,
            "Latitude": lat,
            "Longitude": lon,
        })

    print(f"  {total_rows} lignes lues, {len(addresses)} adresses dans la zone sélectionnée")
    return addresses


def deduplicate_and_sort(addresses):
    """Déduplique par adresse et trie."""
    seen = set()
    unique = []
    for addr in addresses:
        key = addr["Adresse"].upper()
        if key not in seen:
            seen.add(key)
            unique.append(addr)

    unique.sort(key=lambda x: (x["Nom de voie"].upper(), x["Numéro"].zfill(10)))
    return unique


def write_csv(addresses, output_path):
    """Écrit les adresses dans un fichier CSV."""
    if not addresses:
        print("Aucune adresse à exporter.")
        return

    fieldnames = list(addresses[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(addresses)

    print(f"\n{len(addresses)} adresses exportées -> {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Extraire les adresses HLM à Lyon depuis le RPLS (data.gouv.fr)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--arrondissement",
        type=int,
        choices=range(1, 10),
        metavar="N",
        help="Arrondissement de Lyon 1-9. Sans ce paramètre: tous les arrondissements.",
    )
    parser.add_argument(
        "--financement",
        nargs="+",
        metavar="CODE",
        help="Filtrer par type de financement: PLAI PLUS PLS PLI LLTS (sans filtre = tous)",
    )
    parser.add_argument(
        "--output",
        default="hlm_lyon.csv",
        help="Fichier CSV de sortie (défaut: hlm_lyon.csv)",
    )
    args = parser.parse_args()

    # Communes à filtrer
    if args.arrondissement:
        communes = {LYON_INSEE_CODES[args.arrondissement]}
        label = f"Lyon {args.arrondissement}e arrondissement (INSEE {LYON_INSEE_CODES[args.arrondissement]})"
    else:
        communes = set(LYON_INSEE_CODES.values())
        label = "Tous les arrondissements de Lyon"

    print(f"Zone: {label}")
    if args.financement:
        print(f"Financement: {', '.join(args.financement)}")

    # Récupère l'URL du fichier RPLS
    url = None
    try:
        url, title = get_rpls_download_url()
        print(f"Ressource: {title}")
    except Exception as e:
        print(f"API data.gouv.fr inaccessible ({e}), essai avec les URLs de secours...")
        for fallback_url in FALLBACK_URLS:
            url = fallback_url
            break

    if not url:
        print("Impossible de trouver les données RPLS. Vérifiez votre connexion internet.")
        sys.exit(1)

    # Télécharge
    try:
        content = download_data(url)
    except urllib.error.URLError as e:
        print(f"Erreur de téléchargement: {e}")
        sys.exit(1)

    # Parse et filtre
    addresses = parse_rpls(content, communes)

    # Filtre par financement si demandé
    if args.financement:
        finan_upper = [f.upper() for f in args.financement]
        addresses = [a for a in addresses if a["Financement"].upper() in finan_upper]
        print(f"  Après filtre financement: {len(addresses)} adresses")

    # Déduplique et trie
    addresses = deduplicate_and_sort(addresses)

    # Export CSV
    write_csv(addresses, args.output)


if __name__ == "__main__":
    main()
