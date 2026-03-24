from django.http import JsonResponse
from django.views.generic import TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render, redirect

from territory.models import VotingDesk
from ..models import Tractage


class TractageListView(LoginRequiredMixin, TemplateView):
    """List of tractage locations"""
    template_name = 'mobilisation/tractage_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tractages'] = Tractage.objects.select_related('voting_desk').all()
        context['total_tractages'] = Tractage.objects.aggregate(total=Sum('count'))['total'] or 0
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
        try:
            count = int(request.POST.get('count', 0) or 0)
        except (ValueError, TypeError):
            count = 0

        latitude_raw = request.POST.get('latitude') or None
        longitude_raw = request.POST.get('longitude') or None
        try:
            latitude = float(latitude_raw) if latitude_raw else None
            longitude = float(longitude_raw) if longitude_raw else None
        except (ValueError, TypeError):
            latitude = longitude = None

        Tractage.objects.create(
            name=request.POST.get('name', ''),
            address=request.POST.get('address', ''),
            latitude=latitude,
            longitude=longitude,
            count=count,
            voting_desk_id=request.POST.get('voting_desk') or None,
            location_type=request.POST.get('location_type', 'autre')
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
        tractage.name = request.POST.get('name', '')
        tractage.address = request.POST.get('address', '')

        latitude_raw = request.POST.get('latitude') or None
        longitude_raw = request.POST.get('longitude') or None
        try:
            tractage.latitude = float(latitude_raw) if latitude_raw else None
            tractage.longitude = float(longitude_raw) if longitude_raw else None
        except (ValueError, TypeError):
            tractage.latitude = tractage.longitude = None

        try:
            tractage.count = int(request.POST.get('count', 0) or 0)
        except (ValueError, TypeError):
            tractage.count = 0

        tractage.voting_desk_id = request.POST.get('voting_desk') or None
        tractage.location_type = request.POST.get('location_type', 'autre')
        tractage.save()
        return redirect('mobilisation:tractage_list')


class TractageDeleteView(LoginRequiredMixin, View):
    """Delete a tractage location"""

    def post(self, request, pk):
        tractage = get_object_or_404(Tractage, pk=pk)
        tractage.delete()
        return redirect('mobilisation:tractage_list')


class TractageIncrementView(LoginRequiredMixin, View):
    """Increment count by 1"""

    def post(self, request, pk):
        tractage = get_object_or_404(Tractage, pk=pk)
        tractage.count += 1
        tractage.save(update_fields=['count'])
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
                'name': t.name,
                'address': t.address,
                'latitude': t.latitude,
                'longitude': t.longitude,
                'count': t.count,
                'type': t.location_type,
                'type_display': t.get_location_type_display(),
                'voting_desk': t.voting_desk.code if t.voting_desk else None,
            })

        return JsonResponse({'tractages': data})
