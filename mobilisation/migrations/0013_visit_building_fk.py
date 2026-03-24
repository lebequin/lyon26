"""
Migration: Visit.buildings (M2M) -> Visit.building (ForeignKey)

Chaque visite était techniquement liée à plusieurs immeubles via une M2M,
mais dans la pratique seul le premier immeuble était utilisé partout.
Cette migration convertit le champ en ForeignKey nullable en préservant les données.
"""
import django.db.models.deletion
from django.db import migrations, models


def m2m_to_fk(apps, schema_editor):
    Visit = apps.get_model('mobilisation', 'Visit')
    for visit in Visit.objects.prefetch_related('buildings').all():
        building = visit.buildings.first()
        if building:
            visit.building_fk = building
            visit.save(update_fields=['building_fk'])


class Migration(migrations.Migration):

    dependencies = [
        ('mobilisation', '0012_set_9e_priorities'),
        ('territory', '0004_building_is_hlm'),
    ]

    operations = [
        # 1. Ajouter le FK nullable avec un nom temporaire pour éviter le conflit avec le related_name M2M
        migrations.AddField(
            model_name='visit',
            name='building_fk',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='visits_fk',
                to='territory.building',
                verbose_name='Immeuble',
            ),
        ),
        # 2. Copier les données M2M vers le FK
        migrations.RunPython(m2m_to_fk, migrations.RunPython.noop),
        # 3. Supprimer la M2M
        migrations.RemoveField(
            model_name='visit',
            name='buildings',
        ),
        # 4. Renommer building_fk -> building avec le bon related_name
        migrations.RenameField(
            model_name='visit',
            old_name='building_fk',
            new_name='building',
        ),
        # 5. Mettre à jour related_name de 'visits_fk' à 'visits'
        migrations.AlterField(
            model_name='visit',
            name='building',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='visits',
                to='territory.building',
                verbose_name='Immeuble',
            ),
        ),
    ]
