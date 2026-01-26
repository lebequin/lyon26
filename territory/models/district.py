from django.db import models


class District(models.Model):
    """
    Represents an electoral district (arrondissement).
    Top level of the hierarchy: District -> VotingDesk -> Building
    """
    name = models.CharField(max_length=100, verbose_name="Nom")
    code = models.CharField(max_length=20, unique=True, verbose_name="Code")
    description = models.TextField(blank=True, default="", verbose_name="Description")

    class Meta:
        verbose_name = "District"
        verbose_name_plural = "Districts"
        ordering = ['code']

    def __str__(self):
        return self.name