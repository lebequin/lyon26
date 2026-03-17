from django.db import migrations


def set_existing_visits_tour_1(apps, schema_editor):
    Visit = apps.get_model('mobilisation', 'Visit')
    Visit.objects.all().update(tour=1)


class Migration(migrations.Migration):

    dependencies = [
        ('mobilisation', '0010_visit_tour'),
    ]

    operations = [
        migrations.RunPython(
            set_existing_visits_tour_1,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
