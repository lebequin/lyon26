from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count

from territory.models import Building, VotingDesk


class VotingDeskListView(LoginRequiredMixin, TemplateView):
    """List of voting desks with statistics"""
    template_name = 'mobilisation/voting_desk_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        voting_desks = VotingDesk.objects.annotate(
            total_electors=Sum('buildings__num_electors'),
            total_knocked=Sum('buildings__visits__knocked_doors'),
            total_open=Sum('buildings__visits__open_doors'),
            building_count=Count('buildings')
        ).filter(building_count__gt=0).order_by('code')

        desks_with_coverage = []
        for desk in voting_desks:
            desk.coverage = 0
            if desk.total_electors and desk.total_electors > 0:
                desk.coverage = (desk.total_knocked or 0) / desk.total_electors * 100
            desks_with_coverage.append(desk)

        context['voting_desks'] = desks_with_coverage

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
