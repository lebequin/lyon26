from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mobilisation', '0014_historicalvisit'),
    ]

    operations = [
        # Alliance
        migrations.RenameField(model_name='alliance', old_name='label', new_name='name'),
        migrations.AlterModelOptions(
            name='alliance',
            options={'ordering': ['name'], 'verbose_name': 'Alliance', 'verbose_name_plural': 'Alliances'},
        ),
        # Election
        migrations.RenameField(model_name='election', old_name='id_election', new_name='election_code'),
        migrations.RenameField(model_name='election', old_name='type_election', new_name='election_type'),
        migrations.RenameField(model_name='election', old_name='label', new_name='name'),
        migrations.RenameField(model_name='election', old_name='tour', new_name='round'),
        migrations.AlterModelOptions(
            name='election',
            options={'ordering': ['-year', 'election_type', 'round'], 'verbose_name': 'Élection', 'verbose_name_plural': 'Élections'},
        ),
        # ElectionParticipation
        migrations.RenameField(model_name='electionparticipation', old_name='blancs_percent', new_name='blank_percent'),
        # HistoricalVisit (simple_history mirror)
        migrations.RenameField(model_name='historicalvisit', old_name='tour', new_name='round'),
        # Nuance
        migrations.RenameField(model_name='nuance', old_name='label', new_name='name'),
        # NuanceResult
        migrations.RenameField(model_name='nuanceresult', old_name='ratio_voix_exprimes', new_name='vote_share'),
        migrations.AlterModelOptions(
            name='nuanceresult',
            options={'ordering': ['election', 'voting_desk__code', '-vote_share'], 'verbose_name': 'Résultat par nuance', 'verbose_name_plural': 'Résultats par nuance'},
        ),
        # Tractage
        migrations.RenameField(model_name='tractage', old_name='label', new_name='name'),
        migrations.RenameField(model_name='tractage', old_name='nb_tractage', new_name='count'),
        migrations.RenameField(model_name='tractage', old_name='type_tractage', new_name='location_type'),
        migrations.AlterModelOptions(
            name='tractage',
            options={'ordering': ['-count', 'name'], 'verbose_name': 'Tractage', 'verbose_name_plural': 'Tractages'},
        ),
        # Visit
        migrations.RenameField(model_name='visit', old_name='tour', new_name='round'),
    ]
