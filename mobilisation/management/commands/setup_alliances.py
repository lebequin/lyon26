"""
Pré-remplit les nuances et alliances politiques usuelles.

Usage:
    python3 manage.py setup_alliances
"""
from django.core.management.base import BaseCommand
from mobilisation.models import Nuance, Alliance

NUANCES = [
    # Législatives 2024
    ('UG',   'Union de la Gauche (NFP)',         '#e11d48'),
    ('EXG',  'Extrême Gauche',                   '#991b1b'),
    ('ECO',  'Écologistes',                      '#16a34a'),
    ('ENS',  'Ensemble (Macron)',                '#e2b70b'),
    ('DIV',  'Divers',                           '#6b7280'),
    ('LR',   'Les Républicains',                 '#1d4ed8'),
    ('REC',  'Reconquête',                       '#7c3aed'),
    ('RN',   'Rassemblement National',            '#1f2937'),
    # Municipales 2020
    ('LUG',  'Liste Union de la Gauche',         '#e11d48'),
    ('LDVG', 'Liste Divers Gauche',              '#f43f5e'),
    ('LEXG', 'Liste Extrême Gauche',             '#991b1b'),
    ('LVEC', 'Liste Verts / Europe Écologie',    '#16a34a'),
    ('LDVC', 'Liste Divers Centre',              '#e2b70b'),
    ('LUC',  'Liste Union du Centre',            "#d3c509"),
    ('LLR',  'Liste Les Républicains',           '#1d4ed8'),
    ('LRN',  'Liste Rassemblement National',     '#1f2937'),
]

ALLIANCES = [
    {
        'label': 'Gauche unie (NFP / muni)',
        'color': '#e11d48',
        'nuances': ['UG', 'EXG', 'LUG', 'LDVG', 'LEXG'],
    },
    {
        'label': 'Écologistes',
        'color': '#16a34a',
        'nuances': ['ECO', 'LVEC'],
    },
    {
        'label': 'Centre (EPR)',
        'color': '#e2b70b',
        'nuances': ['ENS', 'LDVC', 'LUC'],
    },
    {
        'label': 'Droite (LR)',
        'color': '#1d4ed8',
        'nuances': ['LR', 'LLR'],
    },
    {
        'label': 'Extrême droite (RN + Reconquête)',
        'color': '#1f2937',
        'nuances': ['RN', 'REC', 'LRN'],
    },
]


class Command(BaseCommand):
    help = "Crée les nuances et alliances politiques usuelles"

    def handle(self, *args, **options):
        # Create nuances
        created_n, updated_n = 0, 0
        for code, label, color in NUANCES:
            obj, created = Nuance.objects.update_or_create(
                code=code,
                defaults={'label': label, 'color': color}
            )
            if created:
                created_n += 1
            else:
                updated_n += 1

        self.stdout.write(f"Nuances : {created_n} créées, {updated_n} mises à jour")

        # Create alliances
        created_a, updated_a = 0, 0
        for a_data in ALLIANCES:
            nuances = Nuance.objects.filter(code__in=a_data['nuances'])
            alliance, created = Alliance.objects.update_or_create(
                label=a_data['label'],
                defaults={'color': a_data['color']}
            )
            alliance.nuances.set(nuances)

            nuance_codes = list(nuances.values_list('code', flat=True))
            status = "créée" if created else "mise à jour"
            self.stdout.write(f"  Alliance {status} : {alliance.label} → {nuance_codes}")

            if created:
                created_a += 1
            else:
                updated_a += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nAlliances : {created_a} créées, {updated_a} mises à jour"
        ))
