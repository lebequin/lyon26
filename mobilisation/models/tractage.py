from django.db import models


class Tractage(models.Model):
    """
    Represents a leafleting/flyer distribution location.
    """
    TYPE_CHOICES = [
        ('marche', 'Marché'),
        ('metro', 'Métro'),
        ('bus', 'Arrêt de bus'),
        ('commerce', 'Commerce'),
        ('ecole', 'École'),
        ('autre', 'Autre'),
    ]

    label = models.CharField(max_length=200, verbose_name="Nom du lieu")
    address = models.CharField(max_length=300, blank=True, default="", verbose_name="Adresse")
    latitude = models.FloatField(null=True, blank=True, verbose_name="Latitude")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Longitude")
    nb_tractage = models.PositiveIntegerField(default=0, verbose_name="Nombre de tractages")
    voting_desk = models.ForeignKey(
        'territory.VotingDesk',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tractages',
        verbose_name="Bureau de vote"
    )
    type_tractage = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='autre',
        verbose_name="Type de lieu"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'mobilisation'
        verbose_name = "Tractage"
        verbose_name_plural = "Tractages"
        ordering = ['-nb_tractage', 'label']

    def __str__(self):
        return self.label
