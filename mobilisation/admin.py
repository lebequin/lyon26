import csv
import io
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path

from .models import Visit, Tractage
from territory.models import VotingDesk


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
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
class TractageAdmin(admin.ModelAdmin):
    list_display = ('label', 'type_tractage', 'voting_desk', 'nb_tractage', 'address')
    list_filter = ('type_tractage', 'voting_desk')
    search_fields = ('label', 'address')
    list_editable = ('nb_tractage',)
    ordering = ('-nb_tractage', 'label')
    change_list_template = 'admin/mobilisation/tractage/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv), name='mobilisation_tractage_import'),
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

                # Map type display names to codes
                type_map = {v.lower(): k for k, v in Tractage.TYPE_CHOICES}

                created, updated = 0, 0
                for row in reader:
                    label = row.get('Nom', '').strip()
                    if not label:
                        continue

                    # Get voting desk if provided
                    voting_desk = None
                    bureau_code = row.get('Bureau', '').strip()
                    if bureau_code:
                        try:
                            voting_desk = VotingDesk.objects.get(code=bureau_code)
                        except VotingDesk.DoesNotExist:
                            pass

                    # Parse type
                    type_value = row.get('Type', '').strip().lower()
                    type_tractage = type_map.get(type_value, 'autre')

                    # Parse coordinates
                    latitude = row.get('Latitude', '').strip()
                    longitude = row.get('Longitude', '').strip()

                    obj, was_created = Tractage.objects.update_or_create(
                        label=label,
                        defaults={
                            'type_tractage': type_tractage,
                            'address': row.get('Adresse', '').strip(),
                            'voting_desk': voting_desk,
                            'nb_tractage': int(row.get('Nb Tractages', 0) or 0),
                            'latitude': float(latitude) if latitude else None,
                            'longitude': float(longitude) if longitude else None,
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
            'title': 'Importer des lieux de tractage',
            'expected_columns': 'Nom; Type; Adresse; Bureau; Nb Tractages; Latitude; Longitude',
            'opts': self.model._meta,
        })
