import django_filters
from django.db.models import Q

from territory.models import Building


class BuildingFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_address', label='Adresse')
    bureau = django_filters.CharFilter(
        field_name='voting_desk__code', lookup_expr='exact', label='Bureau'
    )
    district = django_filters.CharFilter(
        field_name='voting_desk__district__code', lookup_expr='exact', label='Arrondissement'
    )
    priority = django_filters.NumberFilter(
        field_name='voting_desk__priority', lookup_expr='exact', label='Priorité'
    )
    hlm = django_filters.CharFilter(method='filter_hlm', label='HLM')
    finished = django_filters.CharFilter(method='filter_finished', label='Terminé')

    class Meta:
        model = Building
        fields = []

    def filter_address(self, queryset, name, value):
        return queryset.filter(
            Q(street_name__icontains=value) | Q(street_number__icontains=value)
        )

    def filter_hlm(self, queryset, name, value):
        if value == '1':
            return queryset.filter(is_hlm=True)
        if value == '0':
            return queryset.filter(is_hlm=False)
        return queryset

    def filter_finished(self, queryset, name, value):
        if value == '1':
            return queryset.filter(is_finished=True)
        if value == '0':
            return queryset.filter(is_finished=False)
        return queryset
