from django.db import models
from .voting_desk import VotingDesk


class Building(models.Model):
    """
    Represents a building with electors.
    Belongs to a VotingDesk.
    """
    street_number = models.CharField(max_length=20, verbose_name="Numéro")
    street_name = models.CharField(max_length=200, verbose_name="Rue")
    num_electors = models.PositiveIntegerField(default=0, verbose_name="Nombre d'électeurs")
    voting_desk = models.ForeignKey(
        VotingDesk,
        on_delete=models.CASCADE,
        related_name='buildings',
        verbose_name="Bureau de vote"
    )
    # Geocoding for map display
    latitude = models.FloatField(null=True, blank=True, verbose_name="Latitude")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Longitude")
    # Mobilisation tracking
    is_finished = models.BooleanField(default=False, verbose_name="Terminé")
    # Social housing flag (HLM - from RPLS data)
    is_hlm = models.BooleanField(default=False, verbose_name="Logement social (HLM)")

    class Meta:
        verbose_name = "Immeuble"
        verbose_name_plural = "Immeubles"
        ordering = ['street_name', 'street_number']
        unique_together = [['voting_desk', 'street_number', 'street_name']]

    def __str__(self):
        return f"{self.street_number} {self.street_name}"

    @property
    def full_address(self):
        """Return full address for geocoding."""
        return f"{self.street_number} {self.street_name}, Lyon"
