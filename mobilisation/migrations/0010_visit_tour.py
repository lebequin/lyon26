from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mobilisation', '0009_election_generic'),
    ]

    operations = [
        migrations.AddField(
            model_name='visit',
            name='tour',
            field=models.PositiveSmallIntegerField(
                choices=[(1, '1er tour'), (2, '2nd tour')],
                default=2,
                verbose_name='Tour',
            ),
        ),
    ]
