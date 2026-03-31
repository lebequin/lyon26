from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget

from django.contrib.auth.models import User
from territory.models import VotingDesk

from .models import (
    Visit, Tractage, ElectionResult,
    Election, Nuance, Alliance, ElectionParticipation, NuanceResult,
    UserProfile,
)


class VisitResource(resources.ModelResource):
    buildings = fields.Field(
        column_name='buildings',
        attribute='buildings',
        widget=ManyToManyWidget('territory.Building', field='id'),
    )

    class Meta:
        model = Visit
        fields = ('id', 'tour', 'date', 'open_doors', 'knocked_doors', 'comment', 'buildings')
        export_order = ('id', 'date', 'tour', 'open_doors', 'knocked_doors', 'comment', 'buildings')


class TractageResource(resources.ModelResource):
    voting_desk = fields.Field(
        column_name='voting_desk',
        attribute='voting_desk',
        widget=ForeignKeyWidget(VotingDesk, field='code'),
    )

    class Meta:
        model = Tractage
        fields = ('id', 'label', 'type_tractage', 'address', 'voting_desk', 'nb_tractage', 'latitude', 'longitude')
        export_order = ('id', 'label', 'type_tractage', 'address', 'voting_desk', 'nb_tractage', 'latitude', 'longitude')


class ElectionResultResource(resources.ModelResource):
    voting_desk = fields.Field(
        column_name='voting_desk',
        attribute='voting_desk',
        widget=ForeignKeyWidget(VotingDesk, field='code'),
    )

    class Meta:
        model = ElectionResult
        fields = (
            'id', 'voting_desk', 'location', 'neighborhood',
            'reg21_expressed', 'reg21_uge_votes', 'reg21_uge_percent', 'reg21_abstention',
            'euro24_expressed', 'euro24_nfp_votes', 'euro24_nfp_percent', 'euro24_abstention',
            'leg24_expressed', 'leg24_nfp_votes', 'leg24_nfp_percent', 'leg24_abstention',
        )
        export_order = (
            'id', 'voting_desk', 'location', 'neighborhood',
            'reg21_expressed', 'reg21_uge_votes', 'reg21_uge_percent', 'reg21_abstention',
            'euro24_expressed', 'euro24_nfp_votes', 'euro24_nfp_percent', 'euro24_abstention',
            'leg24_expressed', 'leg24_nfp_votes', 'leg24_nfp_percent', 'leg24_abstention',
        )


class ElectionResource(resources.ModelResource):
    class Meta:
        model = Election
        fields = ('id', 'id_election', 'type_election', 'tour', 'year', 'label')
        export_order = ('id', 'id_election', 'type_election', 'tour', 'year', 'label')
        import_id_fields = ('id_election',)


class NuanceResource(resources.ModelResource):
    class Meta:
        model = Nuance
        fields = ('id', 'code', 'label', 'color')
        export_order = ('id', 'code', 'label', 'color')
        import_id_fields = ('code',)


class AllianceResource(resources.ModelResource):
    nuances = fields.Field(
        column_name='nuances',
        attribute='nuances',
        widget=ManyToManyWidget(Nuance, field='code'),
    )

    class Meta:
        model = Alliance
        fields = ('id', 'label', 'color', 'nuances')
        export_order = ('id', 'label', 'color', 'nuances')


class ElectionParticipationResource(resources.ModelResource):
    election = fields.Field(
        column_name='election',
        attribute='election',
        widget=ForeignKeyWidget(Election, field='id_election'),
    )
    voting_desk = fields.Field(
        column_name='voting_desk',
        attribute='voting_desk',
        widget=ForeignKeyWidget(VotingDesk, field='code'),
    )

    class Meta:
        model = ElectionParticipation
        fields = ('id', 'election', 'voting_desk', 'abstention_percent', 'blancs_percent')
        export_order = ('id', 'election', 'voting_desk', 'abstention_percent', 'blancs_percent')


class NuanceResultResource(resources.ModelResource):
    election = fields.Field(
        column_name='election',
        attribute='election',
        widget=ForeignKeyWidget(Election, field='id_election'),
    )
    voting_desk = fields.Field(
        column_name='voting_desk',
        attribute='voting_desk',
        widget=ForeignKeyWidget(VotingDesk, field='code'),
    )
    nuance = fields.Field(
        column_name='nuance',
        attribute='nuance',
        widget=ForeignKeyWidget(Nuance, field='code'),
    )

    class Meta:
        model = NuanceResult
        fields = ('id', 'election', 'voting_desk', 'nuance', 'ratio_voix_exprimes')
        export_order = ('id', 'election', 'voting_desk', 'nuance', 'ratio_voix_exprimes')


class UserProfileResource(resources.ModelResource):
    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, field='username'),
    )

    class Meta:
        model = UserProfile
        fields = ('id', 'user', 'role')
        export_order = ('id', 'user', 'role')
