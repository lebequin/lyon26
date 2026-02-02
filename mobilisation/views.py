import csv
from django.http import JsonResponse, HttpResponse
from django.views.generic import TemplateView, ListView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncWeek, TruncMonth
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from datetime import datetime, timedelta

from territory.models import Building, VotingDesk
from .models import Visit, Tractage


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard with map and visit form"""
    template_name = 'mobilisation/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['buildings'] = Building.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).select_related('voting_desk').order_by('street_name', 'street_number')
        return context


class AddVisitView(LoginRequiredMixin, View):
    """API endpoint to add a visit"""

    def post(self, request):
        try:
            building_id = request.POST.get('building')
            knocked_doors = int(request.POST.get('knocked_doors', 0))
            open_doors = int(request.POST.get('open_doors', 0))
            comment = request.POST.get('comment', '')
            is_finished = request.POST.get('is_finished') == 'on'

            building = get_object_or_404(Building, pk=building_id)

            # Create visit
            visit = Visit.objects.create(
                open_doors=open_doors,
                knocked_doors=knocked_doors,
                comment=comment
            )
            visit.buildings.add(building)

            # Update building finished status
            if is_finished:
                building.is_finished = True
                building.save(update_fields=['is_finished'])

            return JsonResponse({'success': True, 'visit_id': visit.id})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class BuildingsAPIView(LoginRequiredMixin, View):
    """JSON API endpoint for map markers - only visited buildings"""

    def get(self, request):
        buildings = Building.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).select_related('voting_desk').annotate(
            total_open=Sum('visits__open_doors'),
            total_knocked=Sum('visits__knocked_doors'),
            visit_count=Count('visits')
        ).filter(visit_count__gt=0)

        data = []
        for bldg in buildings:
            total_open = bldg.total_open or 0
            total_knocked = bldg.total_knocked or 0
            open_rate = round((total_open / total_knocked * 100), 1) if total_knocked > 0 else 0

            data.append({
                'id': bldg.pk,
                'address': str(bldg),
                'latitude': bldg.latitude,
                'longitude': bldg.longitude,
                'num_electors': bldg.num_electors,
                'voting_desk': bldg.voting_desk.code,
                'is_finished': bldg.is_finished,
                'total_open': total_open,
                'total_knocked': total_knocked,
                'open_rate': open_rate,
            })

        return JsonResponse({'buildings': data})


class VotingDeskListView(LoginRequiredMixin, TemplateView):
    """List of voting desks with statistics"""
    template_name = 'mobilisation/voting_desk_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get voting desks with stats
        voting_desks = VotingDesk.objects.annotate(
            total_electors=Sum('buildings__num_electors'),
            total_knocked=Sum('buildings__visits__knocked_doors'),
            total_open=Sum('buildings__visits__open_doors'),
            building_count=Count('buildings')
        ).filter(building_count__gt=0).order_by('code')

        # Calculate coverage for each desk
        desks_with_coverage = []
        for desk in voting_desks:
            desk.coverage = 0
            if desk.total_electors and desk.total_electors > 0:
                desk.coverage = (desk.total_knocked or 0) / desk.total_electors * 100
            desks_with_coverage.append(desk)

        context['voting_desks'] = desks_with_coverage

        # Global stats
        totals = Building.objects.aggregate(
            total_electors=Sum('num_electors'),
            total_knocked=Sum('visits__knocked_doors'),
            total_open=Sum('visits__open_doors')
        )

        context['total_electors'] = totals['total_electors'] or 0
        context['total_knocked'] = totals['total_knocked'] or 0
        context['total_open'] = totals['total_open'] or 0

        if context['total_electors'] > 0:
            context['coverage_percent'] = context['total_knocked'] / context['total_electors'] * 100
        else:
            context['coverage_percent'] = 0

        return context


class BuildingSearchView(LoginRequiredMixin, View):
    """HTMX endpoint for building search autocomplete"""

    def get(self, request):
        query = request.GET.get('q', '').strip()

        if len(query) < 1:
            return render(request, 'mobilisation/partials/building_search_results.html', {'buildings': []})

        buildings = Building.objects.filter(
            Q(street_name__icontains=query) | Q(street_number__icontains=query),
            latitude__isnull=False,
            longitude__isnull=False
        ).select_related('voting_desk').annotate(
            total_open=Sum('visits__open_doors'),
            total_knocked=Sum('visits__knocked_doors'),
            visit_count=Count('visits')
        ).order_by('street_name', 'street_number')

        # Calculate open rate for each building
        for bldg in buildings:
            bldg.total_open = bldg.total_open or 0
            bldg.total_knocked = bldg.total_knocked or 0
            bldg.open_rate = round((bldg.total_open / bldg.total_knocked * 100), 1) if bldg.total_knocked > 0 else 0

        return render(request, 'mobilisation/partials/building_search_results.html', {'buildings': buildings})


class BuildingDetailView(LoginRequiredMixin, View):
    """HTMX endpoint for building details (info box)"""

    def get(self, request, pk):
        building = get_object_or_404(
            Building.objects.select_related('voting_desk').annotate(
                total_open=Sum('visits__open_doors'),
                total_knocked=Sum('visits__knocked_doors'),
                visit_count=Count('visits')
            ),
            pk=pk
        )

        building.total_open = building.total_open or 0
        building.total_knocked = building.total_knocked or 0
        building.open_rate = round((building.total_open / building.total_knocked * 100), 1) if building.total_knocked > 0 else 0

        return render(request, 'mobilisation/partials/building_info.html', {'building': building})


class BuildingListView(LoginRequiredMixin, TemplateView):
    """List of buildings for a specific voting desk"""
    template_name = 'mobilisation/building_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        voting_desk_code = self.kwargs.get('voting_desk_code')
        voting_desk = get_object_or_404(VotingDesk, code=voting_desk_code)

        context['voting_desk'] = voting_desk

        # Get buildings with visit stats
        buildings = Building.objects.filter(
            voting_desk=voting_desk
        ).annotate(
            total_knocked=Sum('visits__knocked_doors'),
            total_open=Sum('visits__open_doors'),
            visit_count=Count('visits')
        ).order_by('-num_electors')

        context['buildings'] = buildings

        # Calculate totals - use original fields, not annotated ones (PostgreSQL compatibility)
        totals = Building.objects.filter(voting_desk=voting_desk).aggregate(
            total_electors=Sum('num_electors'),
            total_knocked=Sum('visits__knocked_doors'),
            total_open=Sum('visits__open_doors')
        )

        context['total_electors'] = totals['total_electors'] or 0
        context['total_knocked'] = totals['total_knocked'] or 0
        context['total_open'] = totals['total_open'] or 0

        if context['total_electors'] > 0:
            context['coverage'] = context['total_knocked'] / context['total_electors'] * 100
        else:
            context['coverage'] = 0

        return context


class BuildingCreateView(LoginRequiredMixin, View):
    """Create a new building for a voting desk"""

    def get(self, request, voting_desk_code):
        voting_desk = get_object_or_404(VotingDesk, code=voting_desk_code)
        return render(request, 'mobilisation/building_form.html', {
            'voting_desk': voting_desk,
            'building': None,
            'is_edit': False
        })

    def post(self, request, voting_desk_code):
        voting_desk = get_object_or_404(VotingDesk, code=voting_desk_code)

        building = Building.objects.create(
            street_number=request.POST.get('street_number', ''),
            street_name=request.POST.get('street_name', ''),
            num_electors=int(request.POST.get('num_electors', 0)),
            voting_desk=voting_desk,
            latitude=request.POST.get('latitude') or None,
            longitude=request.POST.get('longitude') or None
        )

        return redirect('mobilisation:building_list', voting_desk_code=voting_desk_code)


class BuildingVisitsView(LoginRequiredMixin, TemplateView):
    """List of visits for a specific building"""
    template_name = 'mobilisation/building_visits.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        building_id = self.kwargs.get('pk')
        building = get_object_or_404(
            Building.objects.select_related('voting_desk').annotate(
                total_open=Sum('visits__open_doors'),
                total_knocked=Sum('visits__knocked_doors'),
                visit_count=Count('visits')
            ),
            pk=building_id
        )

        context['building'] = building
        context['visits'] = building.visits.all().order_by('-date', '-created_at')

        # Calculate stats
        context['total_open'] = building.total_open or 0
        context['total_knocked'] = building.total_knocked or 0
        context['open_rate'] = round((context['total_open'] / context['total_knocked'] * 100), 1) if context['total_knocked'] > 0 else 0

        return context


class VisitCreateView(LoginRequiredMixin, View):
    """Create a new visit for a building"""

    def get(self, request, building_pk):
        building = get_object_or_404(Building.objects.select_related('voting_desk'), pk=building_pk)
        return render(request, 'mobilisation/visit_form.html', {
            'building': building,
            'visit': None,
            'is_edit': False
        })

    def post(self, request, building_pk):
        building = get_object_or_404(Building, pk=building_pk)

        open_doors = int(request.POST.get('open_doors', 0))
        knocked_doors = int(request.POST.get('knocked_doors', 0))
        date = request.POST.get('date')
        comment = request.POST.get('comment', '')
        is_finished = request.POST.get('is_finished') == 'on'

        visit = Visit.objects.create(
            open_doors=open_doors,
            knocked_doors=knocked_doors,
            date=date,
            comment=comment
        )
        visit.buildings.add(building)

        if is_finished:
            building.is_finished = True
            building.save(update_fields=['is_finished'])

        return redirect('mobilisation:building_visits', pk=building_pk)


class VisitEditView(LoginRequiredMixin, View):
    """Edit an existing visit"""

    def get(self, request, pk):
        visit = get_object_or_404(Visit, pk=pk)
        building = visit.buildings.first()
        return render(request, 'mobilisation/visit_form.html', {
            'building': building,
            'visit': visit,
            'is_edit': True
        })

    def post(self, request, pk):
        visit = get_object_or_404(Visit, pk=pk)
        building = visit.buildings.first()

        visit.open_doors = int(request.POST.get('open_doors', 0))
        visit.knocked_doors = int(request.POST.get('knocked_doors', 0))
        visit.date = request.POST.get('date')
        visit.comment = request.POST.get('comment', '')
        visit.save()

        is_finished = request.POST.get('is_finished') == 'on'
        if building:
            building.is_finished = is_finished
            building.save(update_fields=['is_finished'])

        return redirect('mobilisation:building_visits', pk=building.pk if building else 1)


class VisitDeleteView(LoginRequiredMixin, View):
    """Delete a visit"""

    def post(self, request, pk):
        visit = get_object_or_404(Visit, pk=pk)
        building = visit.buildings.first()
        building_pk = building.pk if building else None
        visit.delete()

        if building_pk:
            return redirect('mobilisation:building_visits', pk=building_pk)
        return redirect('mobilisation:dashboard')


class TractageListView(LoginRequiredMixin, TemplateView):
    """List of tractage locations"""
    template_name = 'mobilisation/tractage_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tractages'] = Tractage.objects.select_related('voting_desk').all()
        context['total_tractages'] = Tractage.objects.aggregate(total=Sum('nb_tractage'))['total'] or 0
        context['type_choices'] = Tractage.TYPE_CHOICES
        return context


class TractageCreateView(LoginRequiredMixin, View):
    """Create a new tractage location"""

    def get(self, request):
        voting_desks = VotingDesk.objects.all().order_by('code')
        return render(request, 'mobilisation/tractage_form.html', {
            'tractage': None,
            'voting_desks': voting_desks,
            'type_choices': Tractage.TYPE_CHOICES,
            'is_edit': False
        })

    def post(self, request):
        tractage = Tractage.objects.create(
            label=request.POST.get('label', ''),
            address=request.POST.get('address', ''),
            latitude=request.POST.get('latitude') or None,
            longitude=request.POST.get('longitude') or None,
            nb_tractage=int(request.POST.get('nb_tractage', 0)),
            voting_desk_id=request.POST.get('voting_desk') or None,
            type_tractage=request.POST.get('type_tractage', 'autre')
        )
        return redirect('mobilisation:tractage_list')


class TractageEditView(LoginRequiredMixin, View):
    """Edit an existing tractage location"""

    def get(self, request, pk):
        tractage = get_object_or_404(Tractage, pk=pk)
        voting_desks = VotingDesk.objects.all().order_by('code')
        return render(request, 'mobilisation/tractage_form.html', {
            'tractage': tractage,
            'voting_desks': voting_desks,
            'type_choices': Tractage.TYPE_CHOICES,
            'is_edit': True
        })

    def post(self, request, pk):
        tractage = get_object_or_404(Tractage, pk=pk)
        tractage.label = request.POST.get('label', '')
        tractage.address = request.POST.get('address', '')
        tractage.latitude = request.POST.get('latitude') or None
        tractage.longitude = request.POST.get('longitude') or None
        tractage.nb_tractage = int(request.POST.get('nb_tractage', 0))
        tractage.voting_desk_id = request.POST.get('voting_desk') or None
        tractage.type_tractage = request.POST.get('type_tractage', 'autre')
        tractage.save()
        return redirect('mobilisation:tractage_list')


class TractageDeleteView(LoginRequiredMixin, View):
    """Delete a tractage location"""

    def post(self, request, pk):
        tractage = get_object_or_404(Tractage, pk=pk)
        tractage.delete()
        return redirect('mobilisation:tractage_list')


class TractageIncrementView(LoginRequiredMixin, View):
    """Increment nb_tractage by 1"""

    def post(self, request, pk):
        tractage = get_object_or_404(Tractage, pk=pk)
        tractage.nb_tractage += 1
        tractage.save(update_fields=['nb_tractage'])
        return render(request, 'mobilisation/partials/tractage_count.html', {'tractage': tractage})


class TractageAPIView(LoginRequiredMixin, View):
    """JSON API endpoint for tractage map markers"""

    def get(self, request):
        tractages = Tractage.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).select_related('voting_desk')

        data = []
        for t in tractages:
            data.append({
                'id': t.pk,
                'label': t.label,
                'address': t.address,
                'latitude': t.latitude,
                'longitude': t.longitude,
                'nb_tractage': t.nb_tractage,
                'type': t.type_tractage,
                'type_display': t.get_type_tractage_display(),
                'voting_desk': t.voting_desk.code if t.voting_desk else None,
            })

        return JsonResponse({'tractages': data})


class ActionsListView(LoginRequiredMixin, TemplateView):
    """List of all visits ordered by date descending"""
    template_name = 'mobilisation/actions_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        visits = Visit.objects.prefetch_related('buildings', 'buildings__voting_desk').order_by('-date', '-created_at')

        # Add building info to each visit
        visits_with_info = []
        for visit in visits:
            building = visit.buildings.first()
            visits_with_info.append({
                'visit': visit,
                'building': building,
                'address': str(building) if building else 'N/A',
                'voting_desk': building.voting_desk.code if building and building.voting_desk else 'N/A',
            })

        context['visits'] = visits_with_info
        context['total_visits'] = visits.count()

        return context


class StatisticsView(LoginRequiredMixin, TemplateView):
    """Statistics dashboard with charts"""
    template_name = 'mobilisation/statistics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Weekly evolution of visits
        weekly_visits = Visit.objects.annotate(
            week=TruncWeek('date')
        ).values('week').annotate(
            total_knocked=Sum('knocked_doors'),
            total_open=Sum('open_doors')
        ).order_by('week')

        weeks_labels = []
        weekly_knocked_data = []
        weekly_open_data = []

        for entry in weekly_visits:
            if entry['week']:
                weeks_labels.append(entry['week'].strftime('%d/%m'))
                weekly_knocked_data.append(entry['total_knocked'] or 0)
                weekly_open_data.append(entry['total_open'] or 0)

        context['weeks_labels'] = weeks_labels
        context['weekly_knocked_data'] = weekly_knocked_data
        context['weekly_open_data'] = weekly_open_data

        # Monthly evolution of visits
        monthly_visits = Visit.objects.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total_knocked=Sum('knocked_doors'),
            total_open=Sum('open_doors')
        ).order_by('month')

        months_labels = []
        monthly_knocked_data = []
        monthly_open_data = []

        for entry in monthly_visits:
            if entry['month']:
                months_labels.append(entry['month'].strftime('%b %Y'))
                monthly_knocked_data.append(entry['total_knocked'] or 0)
                monthly_open_data.append(entry['total_open'] or 0)

        context['months_labels'] = months_labels
        context['monthly_knocked_data'] = monthly_knocked_data
        context['monthly_open_data'] = monthly_open_data

        # Total stats
        totals = Visit.objects.aggregate(
            total_knocked=Sum('knocked_doors'),
            total_open=Sum('open_doors')
        )
        context['total_knocked'] = totals['total_knocked'] or 0
        context['total_open'] = totals['total_open'] or 0
        context['total_visits'] = Visit.objects.count()

        # Calculate open rate
        if context['total_knocked'] > 0:
            context['open_rate'] = round((context['total_open'] / context['total_knocked']) * 100, 1)
        else:
            context['open_rate'] = 0

        # Tractage stats
        tractage_totals = Tractage.objects.aggregate(
            total_tractages=Sum('nb_tractage')
        )
        context['total_tractages'] = tractage_totals['total_tractages'] or 0
        context['total_tractage_locations'] = Tractage.objects.count()

        # Tractage by type
        tractage_by_type = Tractage.objects.values('type_tractage').annotate(
            total=Sum('nb_tractage')
        ).order_by('-total')

        type_labels = []
        type_data = []
        type_display_map = dict(Tractage.TYPE_CHOICES)

        for entry in tractage_by_type:
            type_labels.append(type_display_map.get(entry['type_tractage'], entry['type_tractage']))
            type_data.append(entry['total'] or 0)

        context['tractage_type_labels'] = type_labels
        context['tractage_type_data'] = type_data

        return context


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
