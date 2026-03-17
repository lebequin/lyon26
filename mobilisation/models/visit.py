from django.db import models
from datetime import date


class Visit(models.Model):
    """
    Represents a door-to-door visit session.
    Can be linked to multiple buildings (for shared entrances).
    """
    TOUR_CHOICES = [(1, '1er tour'), (2, '2nd tour')]

    buildings = models.ManyToManyField(
        'territory.Building',
        related_name='visits',
        verbose_name="Immeubles"
    )
    tour = models.PositiveSmallIntegerField(
        choices=TOUR_CHOICES,
        default=2,
        verbose_name="Tour"
    )
    date = models.DateField(default=date.today, verbose_name="Date")
    open_doors = models.PositiveIntegerField(default=0, verbose_name="Portes ouvertes")
    knocked_doors = models.PositiveIntegerField(default=0, verbose_name="Portes frappées")
    comment = models.TextField(blank=True, default="", verbose_name="Commentaire")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'mobilisation'
        verbose_name = "Visite"
        verbose_name_plural = "Visites"
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Visite du {self.date} ({self.open_doors}/{self.knocked_doors})"

    @property
    def open_rate(self):
        """Calculate the percentage of doors that opened."""
        if self.knocked_doors == 0:
            return 0
        return round((self.open_doors / self.knocked_doors) * 100, 1)
