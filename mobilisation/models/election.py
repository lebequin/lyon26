from django.db import models
from territory.models import VotingDesk


class ElectionResult(models.Model):
    """
    Stores election results by voting desk for different elections.
    """
    voting_desk = models.ForeignKey(
        VotingDesk,
        on_delete=models.CASCADE,
        related_name='election_results',
        verbose_name="Bureau de vote"
    )
    location = models.CharField(max_length=200, blank=True, default="", verbose_name="Lieu")
    neighborhood = models.CharField(max_length=200, blank=True, default="", verbose_name="Quartier")

    # 2021 Regional T2
    reg21_expressed = models.PositiveIntegerField(default=0, verbose_name="REG21 Exprimés")
    reg21_uge_votes = models.PositiveIntegerField(default=0, verbose_name="REG21 Voix UGE")
    reg21_uge_percent = models.FloatField(default=0, verbose_name="REG21 % UGE")
    reg21_abstention = models.FloatField(default=0, verbose_name="REG21 Abstention %")

    # 2024 European
    euro24_expressed = models.PositiveIntegerField(default=0, verbose_name="EURO24 Exprimés")
    euro24_nfp_votes = models.PositiveIntegerField(default=0, verbose_name="EURO24 Voix NFP")
    euro24_nfp_percent = models.FloatField(default=0, verbose_name="EURO24 % NFP")
    euro24_abstention = models.FloatField(default=0, verbose_name="EURO24 Abstention %")

    # 2024 Legislative T2
    leg24_expressed = models.PositiveIntegerField(default=0, verbose_name="LEG24 Exprimés")
    leg24_nfp_votes = models.PositiveIntegerField(default=0, verbose_name="LEG24 Voix NFP")
    leg24_nfp_percent = models.FloatField(default=0, verbose_name="LEG24 % NFP")
    leg24_abstention = models.FloatField(default=0, verbose_name="LEG24 Abstention %")

    class Meta:
        verbose_name = "Résultat électoral"
        verbose_name_plural = "Résultats électoraux"
        ordering = ['voting_desk__code']
        unique_together = [['voting_desk']]

    def __str__(self):
        return f"Élections - {self.voting_desk.code}"

    @property
    def delta_nfp_percent(self):
        """Calculate delta between LEG24 and REG21"""
        return round(self.leg24_nfp_percent - self.reg21_uge_percent, 2)

    @property
    def trend_direction(self):
        """Returns 'up', 'down', or 'stable' based on delta"""
        if self.delta_nfp_percent > 2:
            return 'up'
        elif self.delta_nfp_percent < -2:
            return 'down'
        return 'stable'
