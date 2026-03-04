from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """
    User profile with role for access control.
    """
    ROLE_CHOICES = [
        ('dev', 'Developpeur'),
        ('coordonnateur', 'Coordonnateur'),
        ('militant', 'Militant'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name="Utilisateur"
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='militant',
        verbose_name="Role"
    )

    class Meta:
        verbose_name = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_dev(self):
        return self.role == 'dev'

    @property
    def is_coordonnateur(self):
        return self.role == 'coordonnateur'

    @property
    def is_militant(self):
        return self.role == 'militant'

    @property
    def can_edit(self):
        """Returns True if user can edit/delete visits"""
        return self.role in ('dev', 'coordonnateur')

    @property
    def can_add_visit(self):
        """Returns True if user can add visits from map"""
        return self.role in ('dev', 'coordonnateur')


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create profile when user is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Auto-save profile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
