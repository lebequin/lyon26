from django.contrib import admin
from django.db.models import Sum

from .models import District, VotingDesk, Building


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'voting_desk_count', 'building_count', 'total_electors')
    search_fields = ('name', 'code')
    ordering = ('code',)

    def voting_desk_count(self, obj):
        return obj.voting_desks.count()
    voting_desk_count.short_description = "Bureaux"

    def building_count(self, obj):
        return Building.objects.filter(voting_desk__district=obj).count()
    building_count.short_description = "Immeubles"

    def total_electors(self, obj):
        return Building.objects.filter(
            voting_desk__district=obj
        ).aggregate(total=Sum('num_electors'))['total'] or 0
    total_electors.short_description = "Électeurs"


@admin.register(VotingDesk)
class VotingDeskAdmin(admin.ModelAdmin):
    list_display = ('priority', 'name', 'code', 'location', 'district', 'building_count', 'total_electors')
    list_display_links = ('name', 'code')
    list_filter = ('district', 'priority')
    search_fields = ('name', 'code')
    ordering = ('code',)
    list_editable = ('priority',)

    def building_count(self, obj):
        return obj.buildings.count()
    building_count.short_description = "Immeubles"

    def total_electors(self, obj):
        return obj.buildings.aggregate(total=Sum('num_electors'))['total'] or 0
    total_electors.short_description = "Électeurs"


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = (
        '__str__', 'voting_desk', 'num_electors', 'is_finished',
        'visit_count', 'total_knocked', 'total_open'
    )
    list_filter = ('is_finished', 'voting_desk__district', 'voting_desk')
    search_fields = ('street_name', 'street_number')
    ordering = ('street_name', 'street_number')
    list_editable = ('is_finished',)

    def visit_count(self, obj):
        return obj.visits.count()
    visit_count.short_description = "Visites"

    def total_knocked(self, obj):
        return obj.visits.aggregate(total=Sum('knocked_doors'))['total'] or 0
    total_knocked.short_description = "Frappées"

    def total_open(self, obj):
        return obj.visits.aggregate(total=Sum('open_doors'))['total'] or 0
    total_open.short_description = "Ouvertes"
