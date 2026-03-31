from django.contrib import admin
from django.db.models import Sum

from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from import_export.admin import ImportExportModelAdmin

from .models import Visit, Tractage, ElectionResult, UserProfile, Election, Nuance, Alliance, ElectionParticipation, NuanceResult
from .resources import (
    VisitResource, TractageResource, ElectionResultResource,
    ElectionResource, NuanceResource, AllianceResource,
    ElectionParticipationResource, NuanceResultResource, UserProfileResource,
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profil'


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff')

    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return '-'
    get_role.short_description = 'Role'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Visit)
class VisitAdmin(ImportExportModelAdmin):
    resource_classes = [VisitResource]
    list_display = ('__str__', 'date', 'knocked_doors', 'open_doors', 'open_rate', 'building_list')
    list_filter = ('date', 'buildings__voting_desk__district', 'buildings__voting_desk')
    filter_horizontal = ('buildings',)
    date_hierarchy = 'date'
    ordering = ('-date', '-created_at')

    def building_list(self, obj):
        buildings = obj.buildings.all()[:3]
        result = ", ".join(str(b) for b in buildings)
        if obj.buildings.count() > 3:
            result += f" (+{obj.buildings.count() - 3})"
        return result
    building_list.short_description = "Immeubles"

    def open_rate(self, obj):
        return f"{obj.open_rate}%"
    open_rate.short_description = "Taux d'ouverture"


@admin.register(Tractage)
class TractageAdmin(ImportExportModelAdmin):
    resource_classes = [TractageResource]
    list_display = ('label', 'type_tractage', 'voting_desk', 'nb_tractage', 'address')
    list_filter = ('type_tractage', 'voting_desk')
    search_fields = ('label', 'address')
    list_editable = ('nb_tractage',)
    ordering = ('-nb_tractage', 'label')


@admin.register(ElectionResult)
class ElectionResultAdmin(ImportExportModelAdmin):
    resource_classes = [ElectionResultResource]
    list_display = ('voting_desk', 'neighborhood', 'reg21_uge_percent', 'euro24_nfp_percent', 'leg24_nfp_percent', 'delta_nfp_percent', 'trend_display')
    list_filter = ('voting_desk',)
    search_fields = ('voting_desk__code', 'neighborhood', 'location')
    ordering = ('voting_desk__code',)

    def delta_nfp_percent(self, obj):
        return obj.delta_nfp_percent
    delta_nfp_percent.short_description = "Delta NFP %"

    def trend_display(self, obj):
        if obj.delta_nfp_percent > 2:
            return 'Hausse'
        elif obj.delta_nfp_percent < -2:
            return 'Baisse'
        return 'Stable'
    trend_display.short_description = "Tendance"


class NuanceResultInline(admin.TabularInline):
    model = NuanceResult
    extra = 0
    fields = ('nuance', 'ratio_voix_exprimes')


@admin.register(Election)
class ElectionAdmin(ImportExportModelAdmin):
    resource_classes = [ElectionResource]
    list_display = ('label', 'type_election', 'tour', 'year', 'id_election')
    list_filter = ('type_election', 'tour', 'year')
    ordering = ('-year', 'type_election', 'tour')


@admin.register(Nuance)
class NuanceAdmin(ImportExportModelAdmin):
    resource_classes = [NuanceResource]
    list_display = ('code', 'label', 'color')
    search_fields = ('code', 'label')


@admin.register(Alliance)
class AllianceAdmin(ImportExportModelAdmin):
    resource_classes = [AllianceResource]
    list_display = ('label', 'color', 'nuance_list')
    filter_horizontal = ('nuances',)

    def nuance_list(self, obj):
        return ", ".join(n.code for n in obj.nuances.all())
    nuance_list.short_description = "Nuances"


@admin.register(ElectionParticipation)
class ElectionParticipationAdmin(ImportExportModelAdmin):
    resource_classes = [ElectionParticipationResource]
    list_display = ('election', 'voting_desk', 'abstention_percent', 'blancs_percent')
    list_filter = ('election',)
    search_fields = ('voting_desk__code',)


@admin.register(NuanceResult)
class NuanceResultAdmin(ImportExportModelAdmin):
    resource_classes = [NuanceResultResource]
    list_display = ('election', 'voting_desk', 'nuance', 'ratio_voix_exprimes')
    list_filter = ('election', 'nuance')
    search_fields = ('voting_desk__code',)


@admin.register(UserProfile)
class UserProfileAdmin(ImportExportModelAdmin):
    resource_classes = [UserProfileResource]
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username',)
