from django.http import JsonResponse
from django.views.generic import TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render, redirect

from territory.models import Building, VotingDesk, District
from .exports import compute_open_rate
from ..filters import BuildingFilter


class BuildingsAPIView(LoginRequiredMixin, View):
    """JSON API endpoint for map markers - only visited buildings"""

    def get(self, request):
        tour = int(request.GET.get('tour', 2))
        tour_filter = Q(visits__tour=tour)
        buildings = Building.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).select_related('voting_desk').annotate(
            total_open=Sum('visits__open_doors', filter=tour_filter),
            total_knocked=Sum('visits__knocked_doors', filter=tour_filter),
            visit_count=Count('visits', filter=tour_filter)
        ).filter(visit_count__gt=0)

        data = []
        for bldg in buildings:
            total_open = bldg.total_open or 0
            total_knocked = bldg.total_knocked or 0
            open_rate = compute_open_rate(total_open, total_knocked)

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
        ).select_related('voting_desk').with_visit_stats().order_by('-num_electors', 'street_name', 'street_number')

        for bldg in buildings:
            bldg.total_open = bldg.total_open or 0
            bldg.total_knocked = bldg.total_knocked or 0
            bldg.open_rate = compute_open_rate(bldg.total_open, bldg.total_knocked)

        return render(request, 'mobilisation/partials/building_search_results.html', {'buildings': buildings})


class BuildingDetailView(LoginRequiredMixin, View):
    """HTMX endpoint for building details (info box)"""

    def get(self, request, pk):
        building = get_object_or_404(
            Building.objects.select_related('voting_desk').with_visit_stats(),
            pk=pk
        )

        building.total_open = building.total_open or 0
        building.total_knocked = building.total_knocked or 0
        building.open_rate = compute_open_rate(building.total_open, building.total_knocked)

        return render(request, 'mobilisation/partials/building_info.html', {'building': building})


class BuildingListView(LoginRequiredMixin, TemplateView):
    """List of buildings for a specific voting desk"""
    template_name = 'mobilisation/building_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        voting_desk_code = self.kwargs.get('voting_desk_code')
        voting_desk = get_object_or_404(VotingDesk, code=voting_desk_code)

        context['voting_desk'] = voting_desk

        buildings = Building.objects.filter(
            voting_desk=voting_desk
        ).with_visit_stats().order_by('-num_electors')

        context['buildings'] = buildings

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

        try:
            num_electors = int(request.POST.get('num_electors', 0) or 0)
        except (ValueError, TypeError):
            num_electors = 0

        latitude_raw = request.POST.get('latitude') or None
        longitude_raw = request.POST.get('longitude') or None
        try:
            latitude = float(latitude_raw) if latitude_raw else None
            longitude = float(longitude_raw) if longitude_raw else None
        except (ValueError, TypeError):
            latitude = longitude = None

        Building.objects.create(
            street_number=request.POST.get('street_number', ''),
            street_name=request.POST.get('street_name', ''),
            num_electors=num_electors,
            voting_desk=voting_desk,
            latitude=latitude,
            longitude=longitude,
            is_hlm=request.POST.get('is_hlm') == 'on'
        )

        return redirect('mobilisation:building_list', voting_desk_code=voting_desk_code)


class BuildingVisitsView(LoginRequiredMixin, TemplateView):
    """List of visits for a specific building"""
    template_name = 'mobilisation/building_visits.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        building_id = self.kwargs.get('pk')
        building = get_object_or_404(
            Building.objects.select_related('voting_desk').with_visit_stats(),
            pk=building_id
        )

        context['building'] = building
        context['visits'] = building.visits.all().order_by('-date', '-created_at')

        context['total_open'] = building.total_open or 0
        context['total_knocked'] = building.total_knocked or 0
        context['open_rate'] = compute_open_rate(context['total_open'], context['total_knocked'])

        return context


class AddressesListView(LoginRequiredMixin, TemplateView):
    """List of all addresses with filters for targeting"""
    template_name = 'mobilisation/addresses_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        base_qs = Building.objects.select_related(
            'voting_desk', 'voting_desk__district'
        ).with_visit_stats()

        f = BuildingFilter(self.request.GET, queryset=base_qs)
        buildings = f.qs.order_by('-num_electors', 'street_name', 'street_number')

        total_buildings = buildings.count()
        total_electors = buildings.aggregate(total=Sum('num_electors'))['total'] or 0
        context['total_buildings'] = total_buildings
        context['total_electors'] = total_electors
        context['avg_electors'] = round(total_electors / total_buildings, 1) if total_buildings > 0 else 0

        paginator = Paginator(buildings, 25)
        page_obj = paginator.get_page(self.request.GET.get('page'))

        for bldg in page_obj:
            bldg.total_open = bldg.total_open or 0
            bldg.total_knocked = bldg.total_knocked or 0
            bldg.open_rate = compute_open_rate(bldg.total_open, bldg.total_knocked)

        context['buildings'] = page_obj
        context['page_obj'] = page_obj

        # Valeurs courantes pour le template (inchangées)
        district_code = self.request.GET.get('district', '')
        context['priorities'] = VotingDesk.objects.exclude(
            priority__isnull=True
        ).values_list('priority', flat=True).distinct().order_by('priority')

        voting_desks_qs = VotingDesk.objects.all().order_by('code')
        if district_code:
            voting_desks_qs = voting_desks_qs.filter(district__code=district_code)
        context['voting_desks'] = voting_desks_qs
        context['districts'] = District.objects.all().order_by('code')

        context['current_priority'] = self.request.GET.get('priority', '')
        context['current_bureau'] = self.request.GET.get('bureau', '')
        context['current_district'] = district_code
        context['current_hlm'] = self.request.GET.get('hlm', '')
        context['current_finished'] = self.request.GET.get('finished', '')
        context['query'] = self.request.GET.get('q', '')

        return context
