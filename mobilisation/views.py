from django.http import JsonResponse
from django.views.generic import TemplateView, ListView
from django.views import View
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404, render

from territory.models import Building, VotingDesk
from .models import Visit


class DashboardView(TemplateView):
    """Main dashboard with map and visit form"""
    template_name = 'mobilisation/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['buildings'] = Building.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).select_related('voting_desk').order_by('street_name', 'street_number')
        return context


class AddVisitView(View):
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


class BuildingsAPIView(View):
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


class VotingDeskListView(TemplateView):
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


class BuildingSearchView(View):
    """HTMX endpoint for building search autocomplete"""

    def get(self, request):
        query = request.GET.get('q', '').strip()

        if len(query) < 1:
            return render(request, 'mobilisation/partials/building_search_results.html', {'buildings': []})

        buildings = Building.objects.filter(
            Q(street_name__icontains=query) | Q(street_number__icontains=query),
            latitude__isnull=False,
            longitude__isnull=False
        ).order_by('street_name', 'street_number')

        return render(request, 'mobilisation/partials/building_search_results.html', {'buildings': buildings})


class BuildingDetailView(View):
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


class BuildingListView(TemplateView):
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

        # Calculate totals
        totals = buildings.aggregate(
            total_electors=Sum('num_electors'),
            total_knocked=Sum('total_knocked'),
            total_open=Sum('total_open')
        )

        context['total_electors'] = totals['total_electors'] or 0
        context['total_knocked'] = totals['total_knocked'] or 0
        context['total_open'] = totals['total_open'] or 0

        if context['total_electors'] > 0:
            context['coverage'] = context['total_knocked'] / context['total_electors'] * 100
        else:
            context['coverage'] = 0

        return context
