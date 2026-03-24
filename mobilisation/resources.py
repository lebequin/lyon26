from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from territory.models import VotingDesk, Building
from .models import Visit, Tractage, ElectionResult


class VisitResource(resources.ModelResource):
    building = fields.Field(
        column_name='Immeuble (id)',
        attribute='building',
        widget=ForeignKeyWidget(Building, field='id'),
    )

    class Meta:
        model = Visit
        fields = ('id', 'building', 'round', 'date', 'open_doors', 'knocked_doors', 'comment')
        export_order = ('id', 'building', 'round', 'date', 'open_doors', 'knocked_doors', 'comment')
        import_id_fields = ('id',)


class TractageResource(resources.ModelResource):
    voting_desk = fields.Field(
        column_name='Bureau',
        attribute='voting_desk',
        widget=ForeignKeyWidget(VotingDesk, field='code'),
    )

    class Meta:
        model = Tractage
        fields = ('id', 'name', 'location_type', 'address', 'voting_desk',
                  'count', 'latitude', 'longitude')
        export_order = ('name', 'location_type', 'address', 'voting_desk',
                        'count', 'latitude', 'longitude')
        import_id_fields = ('name',)


class ElectionResultExportResource(resources.ModelResource):
    """Export seulement — l'import reste géré via le CSV custom (logique complexe)."""
    voting_desk = fields.Field(
        column_name='BV',
        attribute='voting_desk',
        widget=ForeignKeyWidget(VotingDesk, field='code'),
    )

    class Meta:
        model = ElectionResult
        fields = (
            'voting_desk', 'neighborhood', 'location',
            'reg21_expressed', 'reg21_uge_votes', 'reg21_uge_percent', 'reg21_abstention',
            'euro24_expressed', 'euro24_nfp_votes', 'euro24_nfp_percent', 'euro24_abstention',
            'leg24_expressed', 'leg24_nfp_votes', 'leg24_nfp_percent', 'leg24_abstention',
        )
        export_order = fields.keys() if hasattr(fields, 'keys') else None
