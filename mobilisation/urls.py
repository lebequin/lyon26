from django.urls import path
from .views import (
    DashboardView,
    AddVisitView,
    BuildingsAPIView,
    BuildingSearchView,
    BuildingDetailView,
    VotingDeskListView,
    BuildingListView
)

app_name = 'mobilisation'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('bureaux/', VotingDeskListView.as_view(), name='voting_desk_list'),
    path('bureaux/<str:voting_desk_code>/', BuildingListView.as_view(), name='building_list'),
    path('api/buildings/', BuildingsAPIView.as_view(), name='buildings_api'),
    path('api/buildings/search/', BuildingSearchView.as_view(), name='building_search'),
    path('api/buildings/<int:pk>/', BuildingDetailView.as_view(), name='building_detail'),
    path('api/visit/', AddVisitView.as_view(), name='add_visit'),
]
