from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('territory', '0005_historicalbuilding'),
    ]

    operations = [
        migrations.RenameField(
            model_name='building',
            old_name='num_electors',
            new_name='elector_count',
        ),
        migrations.RenameField(
            model_name='historicalbuilding',
            old_name='num_electors',
            new_name='elector_count',
        ),
    ]
