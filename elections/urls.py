"""
Elections URL Configuration
"""

from django.urls import path
from . import views

app_name = 'elections'

urlpatterns = [
    path('', views.home, name='home'),
    path('elections/', views.election_list, name='election_list'),
    path('elections/<int:pk>/', views.election_detail, name='election_detail'),
    path('elections/<int:election_id>/vote/<int:candidate_id>/', views.cast_vote, name='cast_vote'),
    path('elections/<int:pk>/results/json/', views.election_results_json, name='election_results_json'),
]
