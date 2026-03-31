from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from .models import District, VotingDesk, Building


class DistrictResource(resources.ModelResource):
    class Meta:
        model = District
        fields = ('id', 'code', 'name', 'description')
        export_order = ('id', 'code', 'name', 'description')
        import_id_fields = ('code',)


class VotingDeskResource(resources.ModelResource):
    district = fields.Field(
        column_name='district',
        attribute='district',
        widget=ForeignKeyWidget(District, field='code'),
    )

    class Meta:
        model = VotingDesk
        fields = ('id', 'code', 'name', 'location', 'district', 'priority')
        export_order = ('id', 'code', 'name', 'location', 'district', 'priority')
        import_id_fields = ('code',)


class BuildingResource(resources.ModelResource):
    voting_desk = fields.Field(
        column_name='voting_desk',
        attribute='voting_desk',
        widget=ForeignKeyWidget(VotingDesk, field='code'),
    )

    class Meta:
        model = Building
        fields = (
            'id', 'voting_desk', 'street_number', 'street_name',
            'num_electors', 'is_hlm', 'is_finished', 'latitude', 'longitude',
        )
        export_order = (
            'id', 'voting_desk', 'street_number', 'street_name',
            'num_electors', 'is_hlm', 'is_finished', 'latitude', 'longitude',
        )
