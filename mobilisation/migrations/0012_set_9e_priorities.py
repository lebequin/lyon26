from django.db import migrations


PRIORITY_1 = ['906', '908', '918', '919', '920', '921', '925', '929']
PRIORITY_2 = ['915', '917', '922', '923', '924']


def set_9e_priorities(apps, schema_editor):
    VotingDesk = apps.get_model('territory', 'VotingDesk')
    VotingDesk.objects.filter(code__in=PRIORITY_1).update(priority=1)
    VotingDesk.objects.filter(code__in=PRIORITY_2).update(priority=2)


def reverse_9e_priorities(apps, schema_editor):
    VotingDesk = apps.get_model('territory', 'VotingDesk')
    VotingDesk.objects.filter(code__in=PRIORITY_1 + PRIORITY_2).update(priority=None)


class Migration(migrations.Migration):

    dependencies = [
        ('mobilisation', '0011_set_existing_visits_tour_1'),
    ]

    operations = [
        migrations.RunPython(set_9e_priorities, reverse_code=reverse_9e_priorities),
    ]
