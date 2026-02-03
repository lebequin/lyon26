import csv
import io
from datetime import datetime
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path

from .models import Visit, Tractage, ElectionResult
from territory.models import VotingDesk, Building, District


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'date', 'knocked_doors', 'open_doors', 'open_rate', 'building_list')
    list_filter = ('date', 'buildings__voting_desk__district', 'buildings__voting_desk')
    filter_horizontal = ('buildings',)
    date_hierarchy = 'date'
    ordering = ('-date', '-created_at')
    change_list_template = 'admin/mobilisation/visit/change_list.html'

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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv), name='mobilisation_visit_import'),
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

                created, skipped = 0, 0
                for row in reader:
                    date_str = row.get('Date', '').strip()
                    address = row.get('Adresse', '').strip()
                    bureau_code = row.get('Bureau', '').strip()

                    if not address and not bureau_code:
                        skipped += 1
                        continue

                    # Parse date
                    visit_date = None
                    if date_str:
                        try:
                            visit_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                visit_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                            except ValueError:
                                pass

                    # Find building by address or bureau
                    building = None
                    if address:
                        # Try to parse address (format: "number street_name")
                        parts = address.split(' ', 1)
                        if len(parts) == 2:
                            street_number, street_name = parts
                            building = Building.objects.filter(
                                street_number=street_number,
                                street_name__icontains=street_name.strip()
                            ).first()

                    if not building and bureau_code:
                        # Try to find any building in the bureau
                        building = Building.objects.filter(voting_desk__code=bureau_code).first()

                    # Create visit
                    visit = Visit.objects.create(
                        date=visit_date,
                        open_doors=int(row.get('Portes Ouvertes', 0) or 0),
                        knocked_doors=int(row.get('Portes Frappees', 0) or 0),
                        comment=row.get('Commentaire', '').strip()
                    )

                    if building:
                        visit.buildings.add(building)

                    created += 1

                messages.success(request, f"Import termine: {created} visites creees, {skipped} ignorees.")
            except Exception as e:
                messages.error(request, f"Erreur lors de l'import: {str(e)}")

            return redirect('..')

        return render(request, 'admin/csv_import.html', {
            'title': 'Importer des visites',
            'expected_columns': 'Date; Adresse; Bureau; Portes Ouvertes; Portes Frappees; Commentaire',
            'opts': self.model._meta,
        })


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


@admin.register(ElectionResult)
class ElectionResultAdmin(admin.ModelAdmin):
    list_display = ('voting_desk', 'neighborhood', 'reg21_uge_percent', 'euro24_nfp_percent', 'leg24_nfp_percent', 'delta_nfp_percent', 'trend_display')
    list_filter = ('voting_desk',)
    search_fields = ('voting_desk__code', 'neighborhood', 'location')
    ordering = ('voting_desk__code',)
    change_list_template = 'admin/mobilisation/electionresult/change_list.html'

    def trend_display(self, obj):
        if obj.delta_nfp_percent > 2:
            return 'Hausse'
        elif obj.delta_nfp_percent < -2:
            return 'Baisse'
        return 'Stable'
    trend_display.short_description = "Tendance"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv), name='mobilisation_electionresult_import'),
        ]
        return custom_urls + urls

    def parse_percent(self, value):
        """Parse percentage string like '28,35%' to float"""
        if not value:
            return 0.0
        value = value.strip().replace('%', '').replace(',', '.').replace(' ', '')
        try:
            return float(value)
        except ValueError:
            return 0.0

    def parse_int(self, value):
        """Parse integer string"""
        if not value:
            return 0
        value = value.strip().replace(' ', '')
        try:
            return int(value)
        except ValueError:
            return 0

    def import_csv(self, request):
        if request.method == 'POST':
            csv_file = request.FILES.get('csv_file')
            if not csv_file:
                messages.error(request, "Veuillez selectionner un fichier CSV.")
                return redirect('..')

            try:
                decoded = csv_file.read().decode('utf-8-sig')
                # Handle tab-separated values as well
                if '\t' in decoded:
                    delimiter = '\t'
                else:
                    delimiter = ';'

                reader = csv.DictReader(io.StringIO(decoded), delimiter=delimiter)

                created, updated, skipped = 0, 0, 0
                missing_desks = []
                for row in reader:
                    bv_code = row.get('BV', '').strip()
                    if not bv_code:
                        skipped += 1
                        continue

                    try:
                        voting_desk = VotingDesk.objects.get(code=bv_code)
                    except VotingDesk.DoesNotExist:
                        # Try to find a matching district based on code prefix (e.g., 501 -> district 5)
                        district_code = bv_code[0] if len(bv_code) >= 1 else None
                        district = None
                        if district_code:
                            district = District.objects.filter(code=district_code).first()
                            if not district:
                                district = District.objects.filter(code=f"0{district_code}").first()

                        if district:
                            # Create voting desk with found district
                            voting_desk = VotingDesk.objects.create(
                                code=bv_code,
                                name=row.get('Lieu', bv_code).strip() or bv_code,
                                location=row.get('Lieu', '').strip(),
                                district=district
                            )
                        else:
                            # Skip if no matching district found
                            missing_desks.append(bv_code)
                            skipped += 1
                            continue

                    obj, was_created = ElectionResult.objects.update_or_create(
                        voting_desk=voting_desk,
                        defaults={
                            'location': row.get('Lieu', '').strip(),
                            'neighborhood': row.get('Quartier', '').strip().replace('\n', ' '),
                            # REG21
                            'reg21_expressed': self.parse_int(row.get('21REG T2\nExprimés', row.get('21REG T2 Exprimes', ''))),
                            'reg21_uge_votes': self.parse_int(row.get('21REG T2\nExp UGE', row.get('21REG T2 Exp UGE', ''))),
                            'reg21_uge_percent': self.parse_percent(row.get('21REG T2\nVoix UGE en %', row.get('21REG T2 Voix UGE en %', ''))),
                            'reg21_abstention': self.parse_percent(row.get('21REG T2\nAbst %', row.get('21REG T2 Abst %', ''))),
                            # EURO24
                            'euro24_expressed': self.parse_int(row.get('24EURO\nExprimés', row.get('24EURO Exprimes', ''))),
                            'euro24_nfp_votes': self.parse_int(row.get('24EURO\nExp NFP ', row.get('24EURO Exp NFP', ''))),
                            'euro24_nfp_percent': self.parse_percent(row.get('24EURO\nVoix NFP en %', row.get('24EURO Voix NFP en %', ''))),
                            'euro24_abstention': self.parse_percent(row.get('24EURO\nAbst %', row.get('24EURO Abst %', ''))),
                            # LEG24
                            'leg24_expressed': self.parse_int(row.get('24LEG T2\nExprimés', row.get('24LEG T2 Exprimes', ''))),
                            'leg24_nfp_votes': self.parse_int(row.get('24LEG T2\nExp NFP ', row.get('24LEG T2 Exp NFP', ''))),
                            'leg24_nfp_percent': self.parse_percent(row.get('24 LEG T2\nVoix NFP en %', row.get('24LEG T2 Voix NFP en %', row.get('24 LEG T2 Voix NFP en %', '')))),
                            'leg24_abstention': self.parse_percent(row.get('24LEG T2\nAbst %', row.get('24LEG T2 Abst %', ''))),
                        }
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

                msg = f"Import termine: {created} crees, {updated} mis a jour, {skipped} ignores."
                if missing_desks:
                    msg += f" Bureaux manquants: {', '.join(missing_desks)}"
                messages.success(request, msg)
            except Exception as e:
                messages.error(request, f"Erreur lors de l'import: {str(e)}")

            return redirect('..')

        return render(request, 'admin/csv_import.html', {
            'title': 'Importer des resultats electoraux',
            'expected_columns': 'BV; Lieu; Quartier; 21REG T2 Exprimes; ... (format Excel copie-colle)',
            'opts': self.model._meta,
        })
