from django.urls import path
from .views import (
    DashboardView,
    AddVisitView,
    BuildingsAPIView,
    BuildingSearchView,
    BuildingDetailView,
    VotingDeskListView,
    BuildingListView,
    BuildingVisitsView,
    VisitCreateView,
    VisitEditView,
    VisitDeleteView,
)

app_name = 'mobilisation'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('bureaux/', VotingDeskListView.as_view(), name='voting_desk_list'),
    path('bureaux/<str:voting_desk_code>/', BuildingListView.as_view(), name='building_list'),
    path('immeuble/<int:pk>/visites/', BuildingVisitsView.as_view(), name='building_visits'),
    path('immeuble/<int:building_pk>/visites/nouvelle/', VisitCreateView.as_view(), name='visit_create'),
    path('visite/<int:pk>/modifier/', VisitEditView.as_view(), name='visit_edit'),
    path('visite/<int:pk>/supprimer/', VisitDeleteView.as_view(), name='visit_delete'),
    path('api/buildings/', BuildingsAPIView.as_view(), name='buildings_api'),
    path('api/buildings/search/', BuildingSearchView.as_view(), name='building_search'),
    path('api/buildings/<int:pk>/', BuildingDetailView.as_view(), name='building_detail'),
    path('api/visit/', AddVisitView.as_view(), name='add_visit'),
]
