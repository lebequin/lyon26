import csv
import io
from datetime import datetime

from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from import_export.admin import ImportExportModelAdmin, ExportMixin

from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Visit, Tractage, ElectionResult, UserProfile, Election, Nuance, Alliance, ElectionParticipation, NuanceResult
from .resources import VisitResource, TractageResource, ElectionResultExportResource
from territory.models import VotingDesk, Building, District


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


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Visit)
class VisitAdmin(ImportExportModelAdmin):
    resource_classes = [VisitResource]
    list_display = ('__str__', 'date', 'knocked_doors', 'open_doors', 'open_rate', 'building_display')
    list_filter = ('date', 'building__voting_desk__district', 'building__voting_desk')
    raw_id_fields = ('building',)
    date_hierarchy = 'date'
    ordering = ('-date', '-created_at')

    def building_display(self, obj):
        return str(obj.building) if obj.building else '-'
    building_display.short_description = "Immeuble"

    def open_rate(self, obj):
        return f"{obj.open_rate}%"
    open_rate.short_description = "Taux d'ouverture"


@admin.register(Tractage)
class TractageAdmin(ImportExportModelAdmin):
    resource_classes = [TractageResource]
    list_display = ('name', 'location_type', 'voting_desk', 'count', 'address')
    list_filter = ('location_type', 'voting_desk')
    search_fields = ('name', 'address')
    list_editable = ('count',)
    ordering = ('-count', 'name')


@admin.register(ElectionResult)
class ElectionResultAdmin(ExportMixin, admin.ModelAdmin):
    """Import géré via CSV custom (logique de parsing complexe), export via django-import-export."""
    resource_classes = [ElectionResultExportResource]
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
        if not value:
            return 0.0
        value = value.strip().replace('%', '').replace(',', '.').replace(' ', '')
        try:
            return float(value)
        except ValueError:
            return 0.0

    def parse_int(self, value):
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
                delimiter = '\t' if '\t' in decoded else ';'
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
                        district_code = bv_code[0] if len(bv_code) >= 1 else None
                        district = None
                        if district_code:
                            district = District.objects.filter(code=district_code).first()
                            if not district:
                                district = District.objects.filter(code=f"0{district_code}").first()

                        if district:
                            voting_desk = VotingDesk.objects.create(
                                code=bv_code,
                                name=row.get('Lieu', bv_code).strip() or bv_code,
                                location=row.get('Lieu', '').strip(),
                                district=district
                            )
                        else:
                            missing_desks.append(bv_code)
                            skipped += 1
                            continue

                    obj, was_created = ElectionResult.objects.update_or_create(
                        voting_desk=voting_desk,
                        defaults={
                            'location': row.get('Lieu', '').strip(),
                            'neighborhood': row.get('Quartier', '').strip().replace('\n', ' '),
                            'reg21_expressed': self.parse_int(row.get('21REG T2\nExprimés', row.get('21REG T2 Exprimes', ''))),
                            'reg21_uge_votes': self.parse_int(row.get('21REG T2\nExp UGE', row.get('21REG T2 Exp UGE', ''))),
                            'reg21_uge_percent': self.parse_percent(row.get('21REG T2\nVoix UGE en %', row.get('21REG T2 Voix UGE en %', ''))),
                            'reg21_abstention': self.parse_percent(row.get('21REG T2\nAbst %', row.get('21REG T2 Abst %', ''))),
                            'euro24_expressed': self.parse_int(row.get('24EURO\nExprimés', row.get('24EURO Exprimes', ''))),
                            'euro24_nfp_votes': self.parse_int(row.get('24EURO\nExp NFP ', row.get('24EURO Exp NFP', ''))),
                            'euro24_nfp_percent': self.parse_percent(row.get('24EURO\nVoix NFP en %', row.get('24EURO Voix NFP en %', ''))),
                            'euro24_abstention': self.parse_percent(row.get('24EURO\nAbst %', row.get('24EURO Abst %', ''))),
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


class NuanceResultInline(admin.TabularInline):
    model = NuanceResult
    extra = 0
    fields = ('nuance', 'vote_share')


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'election_type', 'round', 'year', 'election_code')
    list_filter = ('election_type', 'round', 'year')
    ordering = ('-year', 'election_type', 'round')


@admin.register(Nuance)
class NuanceAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'color')
    search_fields = ('code', 'name')


@admin.register(Alliance)
class AllianceAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'nuance_list')
    filter_horizontal = ('nuances',)

    def nuance_list(self, obj):
        return ", ".join(n.code for n in obj.nuances.all())
    nuance_list.short_description = "Nuances"


@admin.register(ElectionParticipation)
class ElectionParticipationAdmin(admin.ModelAdmin):
    list_display = ('election', 'voting_desk', 'abstention_percent', 'blank_percent')
    list_filter = ('election',)
    search_fields = ('voting_desk__code',)


@admin.register(NuanceResult)
class NuanceResultAdmin(admin.ModelAdmin):
    list_display = ('election', 'voting_desk', 'nuance', 'vote_share')
    list_filter = ('election', 'nuance')
    search_fields = ('voting_desk__code',)
