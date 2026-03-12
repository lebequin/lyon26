from django.db import models
from territory.models import VotingDesk


class Election(models.Model):
    TYPE_CHOICES = [
        ('muni', 'Municipales'),
        ('euro', 'Européennes'),
        ('légi', 'Législatives'),
        ('pres', 'Présidentielles'),
        ('cant', 'Cantonales'),
        ('regi', 'Régionales'),
    ]
    TOUR_CHOICES = [
        ('t1', 'Tour 1'),
        ('t2', 'Tour 2'),
    ]

    id_election = models.CharField(
        max_length=50, unique=True,
        verbose_name="ID élection",
        help_text="Format: 2020_muni_t1"
    )
    type_election = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Type")
    tour = models.CharField(max_length=2, choices=TOUR_CHOICES, verbose_name="Tour")
    year = models.PositiveIntegerField(verbose_name="Année")
    label = models.CharField(max_length=100, verbose_name="Libellé")

    class Meta:
        verbose_name = "Élection"
        verbose_name_plural = "Élections"
        ordering = ['-year', 'type_election', 'tour']

    def __str__(self):
        return self.label


class Nuance(models.Model):
    """Official party nuance code from the government data."""
    code = models.CharField(max_length=20, unique=True, verbose_name="Code nuance")
    label = models.CharField(max_length=200, verbose_name="Libellé")
    color = models.CharField(max_length=7, default="#6366f1", verbose_name="Couleur (hex)")

    class Meta:
        verbose_name = "Nuance politique"
        verbose_name_plural = "Nuances politiques"
        ordering = ['code']

    def __str__(self):
        return f"{self.code} – {self.label}"


class Alliance(models.Model):
    """
    Grouping of nuances to compare across elections.
    e.g. "Gauche unie" = LUG + LEXG + LFG + ...
    """
    label = models.CharField(max_length=100, verbose_name="Libellé")
    nuances = models.ManyToManyField(
        Nuance,
        related_name='alliances',
        verbose_name="Nuances",
        blank=True
    )
    color = models.CharField(max_length=7, default="#6366f1", verbose_name="Couleur (hex)")

    class Meta:
        verbose_name = "Alliance"
        verbose_name_plural = "Alliances"
        ordering = ['label']

    def __str__(self):
        return self.label


class ElectionParticipation(models.Model):
    """Participation data per voting desk per election."""
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE,
        related_name='participations',
        verbose_name="Élection"
    )
    voting_desk = models.ForeignKey(
        VotingDesk, on_delete=models.CASCADE,
        related_name='participations',
        verbose_name="Bureau de vote"
    )
    abstention_percent = models.FloatField(
        default=0,
        verbose_name="Abstention (%)",
        help_text="ratio_abstentions_inscrits"
    )
    blancs_percent = models.FloatField(
        default=0,
        verbose_name="Blancs/nuls (% votants)",
        help_text="ratio_blancs_votants"
    )

    class Meta:
        verbose_name = "Participation"
        verbose_name_plural = "Participations"
        unique_together = [['election', 'voting_desk']]
        ordering = ['election', 'voting_desk__code']

    def __str__(self):
        return f"{self.election} – {self.voting_desk.code}"

    @property
    def participation_percent(self):
        return round(100 - self.abstention_percent, 2)


class NuanceResult(models.Model):
    """Score of a nuance in a given election at a given voting desk."""
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE,
        related_name='nuance_results',
        verbose_name="Élection"
    )
    voting_desk = models.ForeignKey(
        VotingDesk, on_delete=models.CASCADE,
        related_name='nuance_results',
        verbose_name="Bureau de vote"
    )
    nuance = models.ForeignKey(
        Nuance, on_delete=models.CASCADE,
        related_name='results',
        verbose_name="Nuance"
    )
    ratio_voix_exprimes = models.FloatField(
        default=0,
        verbose_name="% voix exprimées"
    )

    class Meta:
        verbose_name = "Résultat par nuance"
        verbose_name_plural = "Résultats par nuance"
        unique_together = [['election', 'voting_desk', 'nuance']]
        ordering = ['election', 'voting_desk__code', '-ratio_voix_exprimes']

    def __str__(self):
        return f"{self.election} – {self.voting_desk.code} – {self.nuance.code}: {self.ratio_voix_exprimes}%"
