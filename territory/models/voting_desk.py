from django.db import models
from .district import District

class VotingDesk(models.Model):
    """
    Represents a voting desk (bureau de vote).
    Belongs to a District, contains Buildings.
    """
    name = models.CharField(max_length=100, verbose_name="Nom")
    location = models.CharField(max_length=200, verbose_name="Localisation")
    code = models.CharField(max_length=20, unique=True, verbose_name="Code")
    district = models.ForeignKey(
        District,
        on_delete=models.CASCADE,
        related_name='voting_desks',
        verbose_name="District"
    )

    class Meta:
        verbose_name = "Bureau de vote"
        verbose_name_plural = "Bureaux de vote"
        ordering = ['code']

    def __str__(self):
        return self.name