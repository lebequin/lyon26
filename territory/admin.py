import csv
import io
from django.contrib import admin, messages
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.urls import path

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
    change_list_template = 'admin/territory/votingdesk/change_list.html'

    def building_count(self, obj):
        return obj.buildings.count()
    building_count.short_description = "Immeubles"

    def total_electors(self, obj):
        return obj.buildings.aggregate(total=Sum('num_electors'))['total'] or 0
    total_electors.short_description = "Électeurs"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv), name='territory_votingdesk_import'),
        ]
        return custom_urls + urls

    def import_csv(self, request):
        if request.method == 'POST':
            csv_file = request.FILES.get('csv_file')
            if not csv_file:
                messages.error(request, "Veuillez selectionner un fichier CSV.")
                return redirect('..')

            try:
                decoded = csv_file.read().decode('utf-8-sig')
                reader = csv.DictReader(io.StringIO(decoded), delimiter=';')

                created, updated = 0, 0
                for row in reader:
                    code = row.get('Code', '').strip()
                    if not code:
                        continue

                    district = None
                    district_code = row.get('District', '').strip()
                    if district_code:
                        district, _ = District.objects.get_or_create(
                            code=district_code,
                            defaults={'name': district_code}
                        )

                    obj, was_created = VotingDesk.objects.update_or_create(
                        code=code,
                        defaults={
                            'name': row.get('Nom', code).strip(),
                            'location': row.get('Adresse', '').strip(),
                            'district': district,
                            'priority': int(row.get('Priorite', 0) or 0) if row.get('Priorite') else None,
                        }
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

                messages.success(request, f"Import termine: {created} crees, {updated} mis a jour.")
            except Exception as e:
                messages.error(request, f"Erreur lors de l'import: {str(e)}")

            return redirect('..')

        return render(request, 'admin/csv_import.html', {
            'title': 'Importer des bureaux de vote',
            'expected_columns': 'Code; Nom; Adresse; District; Priorite',
            'opts': self.model._meta,
        })


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
    change_list_template = 'admin/territory/building/change_list.html'

    def visit_count(self, obj):
        return obj.visits.count()
    visit_count.short_description = "Visites"

    def total_knocked(self, obj):
        return obj.visits.aggregate(total=Sum('knocked_doors'))['total'] or 0
    total_knocked.short_description = "Frappées"

    def total_open(self, obj):
        return obj.visits.aggregate(total=Sum('open_doors'))['total'] or 0
    total_open.short_description = "Ouvertes"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv), name='territory_building_import'),
        ]
        return custom_urls + urls

    def import_csv(self, request):
        if request.method == 'POST':
            csv_file = request.FILES.get('csv_file')
            if not csv_file:
                messages.error(request, "Veuillez selectionner un fichier CSV.")
                return redirect('..')

            try:
                decoded = csv_file.read().decode('utf-8-sig')
                reader = csv.DictReader(io.StringIO(decoded), delimiter=';')

                created, updated, skipped = 0, 0, 0
                for row in reader:
                    bureau_code = row.get('Bureau', '').strip()
                    street_number = row.get('Numero', '').strip()
                    street_name = row.get('Rue', '').strip()

                    if not bureau_code or not street_name:
                        skipped += 1
                        continue

                    try:
                        voting_desk = VotingDesk.objects.get(code=bureau_code)
                    except VotingDesk.DoesNotExist:
                        skipped += 1
                        continue

                    latitude = row.get('Latitude', '').strip()
                    longitude = row.get('Longitude', '').strip()

                    obj, was_created = Building.objects.update_or_create(
                        voting_desk=voting_desk,
                        street_number=street_number,
                        street_name=street_name,
                        defaults={
                            'num_electors': int(row.get('Electeurs', 0) or 0),
                            'is_finished': row.get('Termine', '').strip().lower() in ('oui', 'true', '1'),
                            'latitude': float(latitude) if latitude else None,
                            'longitude': float(longitude) if longitude else None,
                        }
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

                messages.success(request, f"Import termine: {created} crees, {updated} mis a jour, {skipped} ignores.")
            except Exception as e:
                messages.error(request, f"Erreur lors de l'import: {str(e)}")

            return redirect('..')

        return render(request, 'admin/csv_import.html', {
            'title': 'Importer des immeubles',
            'expected_columns': 'Bureau; Numero; Rue; Electeurs; Termine; Latitude; Longitude',
            'opts': self.model._meta,
        })
