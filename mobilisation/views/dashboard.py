from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from territory.models import Building


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
