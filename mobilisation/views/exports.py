import csv

from django.http import HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count

from territory.models import Building, VotingDesk
from ..models import Visit, Tractage, ElectionResult


class ExportElectionsCSV(LoginRequiredMixin, View):
    """Export election results to CSV"""

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="elections.csv"'
        response.write('\ufeff'.encode('utf-8'))  # BOM for Excel

        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'BV', 'Lieu', 'Quartier',
            'REG21 Exprimes', 'REG21 Voix UGE', 'REG21 % UGE', 'REG21 Abst %',
            'EURO24 Exprimes', 'EURO24 Voix NFP', 'EURO24 % NFP', 'EURO24 Abst %',
            'LEG24 Exprimes', 'LEG24 Voix NFP', 'LEG24 % NFP', 'LEG24 Abst %',
            'Delta % NFP'
        ])

        results = ElectionResult.objects.select_related('voting_desk').order_by('voting_desk__code')

        for r in results:
            writer.writerow([
                r.voting_desk.code,
                r.location,
                r.neighborhood,
                r.reg21_expressed, r.reg21_uge_votes, r.reg21_uge_percent, r.reg21_abstention,
                r.euro24_expressed, r.euro24_nfp_votes, r.euro24_nfp_percent, r.euro24_abstention,
                r.leg24_expressed, r.leg24_nfp_votes, r.leg24_nfp_percent, r.leg24_abstention,
                r.delta_nfp_percent
            ])

        return response


class ExportVisitsCSV(LoginRequiredMixin, View):
    """Export visits data to CSV"""

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="visites.csv"'
        response.write('\ufeff'.encode('utf-8'))  # BOM for Excel

        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Date', 'Adresse', 'Bureau', 'Portes Ouvertes', 'Portes Frappees', 'Commentaire'])

        visits = Visit.objects.prefetch_related('buildings', 'buildings__voting_desk').order_by('-date', '-created_at')

        for visit in visits:
            building = visit.buildings.first()
            writer.writerow([
                visit.date.strftime('%Y-%m-%d') if visit.date else '',
                str(building) if building else '',
                building.voting_desk.code if building and building.voting_desk else '',
                visit.open_doors,
                visit.knocked_doors,
                visit.comment or ''
            ])

        return response


class ExportVotingDesksCSV(LoginRequiredMixin, View):
    """Export voting desks data to CSV"""

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="bureaux_de_vote.csv"'
        response.write('\ufeff'.encode('utf-8'))  # BOM for Excel

        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Code', 'Nom', 'Adresse', 'Priorite', 'Nb Immeubles', 'Nb Electeurs', 'Portes Frappees', 'Portes Ouvertes', 'Couverture %'])

        voting_desks = VotingDesk.objects.annotate(
            total_electors=Sum('buildings__num_electors'),
            total_knocked=Sum('buildings__visits__knocked_doors'),
            total_open=Sum('buildings__visits__open_doors'),
            building_count=Count('buildings')
        ).order_by('code')

        for desk in voting_desks:
            total_electors = desk.total_electors or 0
            total_knocked = desk.total_knocked or 0
            coverage = round((total_knocked / total_electors * 100), 1) if total_electors > 0 else 0

            writer.writerow([
                desk.code,
                desk.name,
                desk.location,
                desk.priority or '',
                desk.building_count,
                total_electors,
                total_knocked,
                desk.total_open or 0,
                coverage
            ])

        return response


class ExportBuildingsCSV(LoginRequiredMixin, View):
    """Export buildings data to CSV"""

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="immeubles.csv"'
        response.write('\ufeff'.encode('utf-8'))  # BOM for Excel

        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Bureau', 'Numero', 'Rue', 'Electeurs', 'Portes Frappees', 'Portes Ouvertes', 'Nb Visites', 'Termine', 'Latitude', 'Longitude'])

        buildings = Building.objects.select_related('voting_desk').annotate(
            total_knocked=Sum('visits__knocked_doors'),
            total_open=Sum('visits__open_doors'),
            visit_count=Count('visits')
        ).order_by('voting_desk__code', 'street_name', 'street_number')

        for bldg in buildings:
            writer.writerow([
                bldg.voting_desk.code,
                bldg.street_number,
                bldg.street_name,
                bldg.num_electors,
                bldg.total_knocked or 0,
                bldg.total_open or 0,
                bldg.visit_count,
                'Oui' if bldg.is_finished else 'Non',
                bldg.latitude or '',
                bldg.longitude or ''
            ])

        return response


class ExportTractagesCSV(LoginRequiredMixin, View):
    """Export tractages data to CSV"""

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tractages.csv"'
        response.write('\ufeff'.encode('utf-8'))  # BOM for Excel

        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Nom', 'Type', 'Adresse', 'Bureau', 'Nb Tractages', 'Latitude', 'Longitude'])

        tractages = Tractage.objects.select_related('voting_desk').order_by('label')

        for t in tractages:
            writer.writerow([
                t.label,
                t.get_type_tractage_display(),
                t.address,
                t.voting_desk.code if t.voting_desk else '',
                t.nb_tractage,
                t.latitude or '',
                t.longitude or ''
            ])

        return response
