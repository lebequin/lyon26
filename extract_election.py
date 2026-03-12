"""
Script local : télécharge les données gouvernement et génère un CSV importable en prod.

Usage:
    python3 extract_election.py 2020 muni t1 05
    python3 extract_election.py 2024 legi t1 05
    python3 extract_election.py 2024 legi t2 05

Le CSV généré est importable via :
    python3 manage.py import_election_csv <fichier.csv>
"""
import sys
import csv
import io
import requests
import pandas as pd
from urllib.parse import urlencode

PARTICIPATION_URL = "https://tabular-api.data.gouv.fr/api/resources/b8703c69-a18f-46ab-9e7f-3a8368dcb891/data/csv/"
RESULTS_PARQUET_URL = "https://object.files.data.gouv.fr/data-pipeline-open/elections/candidats_results.parquet"

TYPE_LABELS = {
    'muni': 'Municipales', 'euro': 'Européennes', 'legi': 'Législatives',
    'légi': 'Législatives', 'pres': 'Présidentielles', 'cant': 'Cantonales', 'regi': 'Régionales',
}

def miom_to_desk_code(id_brut_miom):
    return str(int(id_brut_miom.split('_')[-1]))


def main():
    if len(sys.argv) < 5:
        print("Usage: python3 extract_election.py <année> <type> <tour> <arrondissement>")
        print("Ex:    python3 extract_election.py 2020 muni t1 05")
        sys.exit(1)

    year = sys.argv[1]
    type_el = sys.argv[2]
    tour = sys.argv[3]
    arr = sys.argv[4]
    id_election = f"{year}_{type_el}_{tour}"
    type_label = TYPE_LABELS.get(type_el, type_el.capitalize())
    tour_label = "T1" if tour == 't1' else "T2"
    label = f"{type_label} {year} {tour_label}"
    output_file = f"election_{id_election}_arr{arr}.csv"

    print(f"Extraction : {label} ({id_election}) — arr. {arr}")

    # --- Participation ---
    print("  Récupération de la participation...")
    params = {
        "id_brut_miom__contains": f"69123_{arr}",
        "id_election__contains": id_election,
    }
    resp = requests.get(f"{PARTICIPATION_URL}?{urlencode(params)}", timeout=30)
    resp.raise_for_status()
    if not resp.text.strip():
        print(f"  ERREUR : aucune donnée pour '{id_election}'. Vérifiez l'identifiant.")
        sys.exit(1)
    df_part = pd.read_csv(io.StringIO(resp.text))
    print(f"  {len(df_part)} bureaux (participation)")

    # --- Résultats parquet ---
    print("  Téléchargement du parquet (peut prendre 1-2 min)...")
    resp_p = requests.get(RESULTS_PARQUET_URL, timeout=180)
    resp_p.raise_for_status()
    df_res = pd.read_parquet(
        io.BytesIO(resp_p.content),
        engine="pyarrow",
        columns=["id_election", "id_brut_miom", "nuance", "libelle_abrege_liste", "ratio_voix_exprimes"]
    )
    df_res = df_res[
        (df_res["id_election"] == id_election) &
        (df_res["id_brut_miom"].str.startswith(f"69123_{arr}"))
    ]
    df_agg = df_res.groupby(["id_brut_miom", "nuance"])["ratio_voix_exprimes"].sum().reset_index()

    # Nuance labels
    nuance_labels = df_res.groupby("nuance")["libelle_abrege_liste"].first().to_dict()

    print(f"  {len(df_agg)} lignes résultats par nuance")

    # --- Write CSV ---
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Election metadata row
        writer.writerow(['#election', id_election, label, type_el, tour, year])

        # Header
        writer.writerow(['record_type', 'bureau_code', 'nuance_code', 'nuance_label',
                         'ratio_voix_exprimes', 'abstention_percent', 'blancs_percent'])

        # Participation rows
        for _, row in df_part.iterrows():
            bureau = miom_to_desk_code(row['id_brut_miom'])
            abs_pct = row['ratio_abstentions_inscrits'] if 'ratio_abstentions_inscrits' in df_part.columns else 0
            blancs = row['ratio_blancs_votants'] if 'ratio_blancs_votants' in df_part.columns else 0
            abs_val = float(abs_pct) if abs_pct == abs_pct else 0
            blancs_val = float(blancs) if blancs == blancs else 0
            writer.writerow(['participation', bureau, '', '', '', abs_val, blancs_val])

        # Result rows
        for _, row in df_agg.iterrows():
            bureau = miom_to_desk_code(row['id_brut_miom'])
            nuance = row['nuance']
            label_nuance = str(nuance_labels.get(nuance, nuance) or nuance)
            score = float(row['ratio_voix_exprimes']) if row['ratio_voix_exprimes'] == row['ratio_voix_exprimes'] else 0
            writer.writerow(['result', bureau, nuance, label_nuance, round(score, 2), '', ''])

    print(f"\n  Fichier généré : {output_file}")
    print(f"  Importe-le en prod avec :")
    print(f"    python3 manage.py import_election_csv {output_file}")


if __name__ == '__main__':
    main()
