import csv
import io
from django.contrib import admin, messages
from django.db.models import Sum, Count
from django.shortcuts import render, redirect
from django.urls import path
from import_export.admin import ImportExportModelAdmin

from .models import District, VotingDesk, Building
from .resources import VotingDeskResource, BuildingResource


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'voting_desk_count', 'building_count', 'total_electors')
    search_fields = ('name', 'code')
    ordering = ('code',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _voting_desk_count=Count('voting_desks', distinct=True),
            _building_count=Count('voting_desks__buildings', distinct=True),
            _total_electors=Sum('voting_desks__buildings__num_electors'),
        )

    def voting_desk_count(self, obj):
        return obj._voting_desk_count
    voting_desk_count.short_description = "Bureaux"
    voting_desk_count.admin_order_field = '_voting_desk_count'

    def building_count(self, obj):
        return obj._building_count
    building_count.short_description = "Immeubles"
    building_count.admin_order_field = '_building_count'

    def total_electors(self, obj):
        return obj._total_electors or 0
    total_electors.short_description = "Électeurs"
    total_electors.admin_order_field = '_total_electors'


@admin.register(VotingDesk)
class VotingDeskAdmin(ImportExportModelAdmin):
    resource_classes = [VotingDeskResource]
    list_display = ('priority', 'name', 'code', 'location', 'district', 'building_count', 'total_electors')
    list_display_links = ('name', 'code')
    list_filter = ('district', 'priority')
    search_fields = ('name', 'code')
    ordering = ('code',)
    list_editable = ('priority',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _building_count=Count('buildings', distinct=True),
            _total_electors=Sum('buildings__num_electors'),
        )

    def building_count(self, obj):
        return obj._building_count
    building_count.short_description = "Immeubles"
    building_count.admin_order_field = '_building_count'

    def total_electors(self, obj):
        return obj._total_electors or 0
    total_electors.short_description = "Électeurs"
    total_electors.admin_order_field = '_total_electors'


@admin.register(Building)
class BuildingAdmin(ImportExportModelAdmin):
    resource_classes = [BuildingResource]
    list_display = (
        '__str__', 'voting_desk', 'num_electors', 'is_hlm', 'is_finished',
        'visit_count', 'total_knocked', 'total_open'
    )
    list_filter = ('is_hlm', 'is_finished', 'voting_desk__district', 'voting_desk')
    search_fields = ('street_name', 'street_number')
    ordering = ('street_name', 'street_number')
    list_editable = ('is_hlm', 'is_finished',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _visit_count=Count('visits', distinct=True),
            _total_knocked=Sum('visits__knocked_doors'),
            _total_open=Sum('visits__open_doors'),
        )

    def visit_count(self, obj):
        return obj._visit_count
    visit_count.short_description = "Visites"
    visit_count.admin_order_field = '_visit_count'

    def total_knocked(self, obj):
        return obj._total_knocked or 0
    total_knocked.short_description = "Frappées"
    total_knocked.admin_order_field = '_total_knocked'

    def total_open(self, obj):
        return obj._total_open or 0
    total_open.short_description = "Ouvertes"
    total_open.admin_order_field = '_total_open'
