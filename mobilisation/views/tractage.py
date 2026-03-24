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
        Tractage.objects.create(
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
