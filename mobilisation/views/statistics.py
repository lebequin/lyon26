from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.db.models.functions import TruncWeek, TruncMonth

from ..models import Visit, Tractage


class StatisticsView(LoginRequiredMixin, TemplateView):
    """Statistics dashboard with charts"""
    template_name = 'mobilisation/statistics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

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

        totals = Visit.objects.aggregate(
            total_knocked=Sum('knocked_doors'),
            total_open=Sum('open_doors')
        )
        context['total_knocked'] = totals['total_knocked'] or 0
        context['total_open'] = totals['total_open'] or 0
        context['total_visits'] = Visit.objects.count()

        if context['total_knocked'] > 0:
            context['open_rate'] = round((context['total_open'] / context['total_knocked']) * 100, 1)
        else:
            context['open_rate'] = 0

        tractage_totals = Tractage.objects.aggregate(
            total_tractages=Sum('count')
        )
        context['total_tractages'] = tractage_totals['total_tractages'] or 0
        context['total_tractage_locations'] = Tractage.objects.count()

        tractage_by_type = Tractage.objects.values('location_type').annotate(
            total=Sum('count')
        ).order_by('-total')

        type_labels = []
        type_data = []
        type_display_map = dict(Tractage.TYPE_CHOICES)

        for entry in tractage_by_type:
            type_labels.append(type_display_map.get(entry['location_type'], entry['location_type']))
            type_data.append(entry['total'] or 0)

        context['tractage_type_labels'] = type_labels
        context['tractage_type_data'] = type_data

        return context
