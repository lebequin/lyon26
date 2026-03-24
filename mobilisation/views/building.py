from django.http import JsonResponse
from django.views.generic import TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render, redirect

from territory.models import Building, VotingDesk, District


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
        ).order_by('-num_electors', 'street_name', 'street_number')

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

        buildings = Building.objects.filter(
            voting_desk=voting_desk
        ).annotate(
            total_knocked=Sum('visits__knocked_doors'),
            total_open=Sum('visits__open_doors'),
            visit_count=Count('visits')
        ).order_by('-num_electors')

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

        Building.objects.create(
            street_number=request.POST.get('street_number', ''),
            street_name=request.POST.get('street_name', ''),
            num_electors=int(request.POST.get('num_electors', 0)),
            voting_desk=voting_desk,
            latitude=request.POST.get('latitude') or None,
            longitude=request.POST.get('longitude') or None,
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
            Building.objects.select_related('voting_desk').annotate(
                total_open=Sum('visits__open_doors'),
                total_knocked=Sum('visits__knocked_doors'),
                visit_count=Count('visits')
            ),
            pk=building_id
        )

        context['building'] = building
        context['visits'] = building.visits.all().order_by('-date', '-created_at')

        context['total_open'] = building.total_open or 0
        context['total_knocked'] = building.total_knocked or 0
        context['open_rate'] = round((context['total_open'] / context['total_knocked'] * 100), 1) if context['total_knocked'] > 0 else 0

        return context


class AddressesListView(LoginRequiredMixin, TemplateView):
    """List of all addresses with filters for targeting"""
    template_name = 'mobilisation/addresses_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        priority = self.request.GET.get('priority', '')
        voting_desk_code = self.request.GET.get('bureau', '')
        district_code = self.request.GET.get('district', '')
        is_hlm = self.request.GET.get('hlm', '')
        is_finished = self.request.GET.get('finished', '')
        query = self.request.GET.get('q', '').strip()

        buildings = Building.objects.select_related('voting_desk', 'voting_desk__district').annotate(
            total_open=Sum('visits__open_doors'),
            total_knocked=Sum('visits__knocked_doors'),
            visit_count=Count('visits')
        )

        if district_code:
            buildings = buildings.filter(voting_desk__district__code=district_code)

        if voting_desk_code:
            buildings = buildings.filter(voting_desk__code=voting_desk_code)

        if priority:
            buildings = buildings.filter(voting_desk__priority=int(priority))

        if is_hlm == '1':
            buildings = buildings.filter(is_hlm=True)
        elif is_hlm == '0':
            buildings = buildings.filter(is_hlm=False)

        if is_finished == '1':
            buildings = buildings.filter(is_finished=True)
        elif is_finished == '0':
            buildings = buildings.filter(is_finished=False)

        if query:
            buildings = buildings.filter(
                Q(street_name__icontains=query) |
                Q(street_number__icontains=query)
            )

        buildings = buildings.order_by('-num_electors', 'street_name', 'street_number')

        total_buildings = buildings.count()
        total_electors = buildings.aggregate(total=Sum('num_electors'))['total'] or 0
        context['total_buildings'] = total_buildings
        context['total_electors'] = total_electors
        context['avg_electors'] = round(total_electors / total_buildings, 1) if total_buildings > 0 else 0

        paginator = Paginator(buildings, 25)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        for bldg in page_obj:
            bldg.total_open = bldg.total_open or 0
            bldg.total_knocked = bldg.total_knocked or 0
            bldg.open_rate = round((bldg.total_open / bldg.total_knocked * 100), 1) if bldg.total_knocked > 0 else 0

        context['buildings'] = page_obj
        context['page_obj'] = page_obj

        context['priorities'] = VotingDesk.objects.exclude(
            priority__isnull=True
        ).values_list('priority', flat=True).distinct().order_by('priority')

        voting_desks_qs = VotingDesk.objects.all().order_by('code')
        if district_code:
            voting_desks_qs = voting_desks_qs.filter(district__code=district_code)
        context['voting_desks'] = voting_desks_qs

        context['districts'] = District.objects.all().order_by('code')

        context['current_priority'] = priority
        context['current_bureau'] = voting_desk_code
        context['current_district'] = district_code
        context['current_hlm'] = is_hlm
        context['current_finished'] = is_finished
        context['query'] = query

        return context
