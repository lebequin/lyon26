from datetime import datetime

from django.views.generic import TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect

from territory.models import Building
from ..models import Visit


class AddVisitView(LoginRequiredMixin, View):
    """API endpoint to add a visit"""

    def post(self, request):
        from django.http import JsonResponse
        try:
            building_id = request.POST.get('building')
            knocked_doors = int(request.POST.get('knocked_doors', 0))
            open_doors = int(request.POST.get('open_doors', 0))
            comment = request.POST.get('comment', '')
            is_finished = request.POST.get('is_finished') == 'on'
            tour = int(request.POST.get('tour', 2))

            building = get_object_or_404(Building, pk=building_id)

            visit = Visit.objects.create(
                open_doors=open_doors,
                knocked_doors=knocked_doors,
                comment=comment,
                tour=tour
            )
            visit.buildings.add(building)

            if is_finished:
                building.is_finished = True
                building.save(update_fields=['is_finished'])

            return JsonResponse({'success': True, 'visit_id': visit.id})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


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
        tour = int(request.POST.get('tour', 2))

        visit = Visit.objects.create(
            open_doors=open_doors,
            knocked_doors=knocked_doors,
            date=date,
            comment=comment,
            tour=tour
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
        next_url = request.GET.get('next', '')
        return render(request, 'mobilisation/visit_form.html', {
            'building': building,
            'visit': visit,
            'is_edit': True,
            'next': next_url,
        })

    def post(self, request, pk):
        visit = get_object_or_404(Visit, pk=pk)
        building = visit.buildings.first()

        visit.open_doors = int(request.POST.get('open_doors', 0))
        visit.knocked_doors = int(request.POST.get('knocked_doors', 0))
        date_str = request.POST.get('date')
        if date_str:
            visit.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        visit.comment = request.POST.get('comment', '')
        visit.tour = int(request.POST.get('tour', visit.tour))
        visit.save()

        is_finished = request.POST.get('is_finished') == 'on'
        if building:
            building.is_finished = is_finished
            building.save(update_fields=['is_finished'])

        next_url = request.POST.get('next', '')
        if next_url:
            return redirect(next_url)
        if building:
            return redirect('mobilisation:building_visits', pk=building.pk)
        return redirect('mobilisation:actions_list')


class VisitDeleteView(LoginRequiredMixin, View):
    """Delete a visit"""

    def post(self, request, pk):
        visit = get_object_or_404(Visit, pk=pk)
        building = visit.buildings.first()
        building_pk = building.pk if building else None
        visit.delete()

        if building and building.is_finished:
            has_remaining_visits = building.visits.exists()
            if not has_remaining_visits:
                building.is_finished = False
                building.save(update_fields=['is_finished'])

        if building_pk:
            return redirect('mobilisation:building_visits', pk=building_pk)
        return redirect('mobilisation:dashboard')


class ActionsListView(LoginRequiredMixin, TemplateView):
    """List of all visits ordered by date descending"""
    template_name = 'mobilisation/actions_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query = self.request.GET.get('q', '').strip()
        visits = Visit.objects.prefetch_related('buildings', 'buildings__voting_desk').order_by('-date', '-created_at')

        if query:
            visits = visits.filter(
                Q(buildings__street_name__icontains=query) |
                Q(buildings__street_number__icontains=query)
            ).distinct()

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
        context['total_visits'] = len(visits_with_info)
        context['query'] = query

        return context
