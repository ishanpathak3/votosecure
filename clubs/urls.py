"""
Clubs URL Configuration
"""

from django.urls import path
from . import views

app_name = 'clubs'

urlpatterns = [
    path('', views.club_list, name='club_list'),
    path('<int:pk>/', views.club_detail, name='club_detail'),
    path('<int:pk>/join/', views.request_membership, name='request_membership'),
    path('<int:pk>/cancel-request/', views.cancel_membership_request, name='cancel_membership_request'),
    path('<int:pk>/leave/', views.leave_club, name='leave_club'),
    path('<int:pk>/elections/', views.club_elections, name='club_elections'),
]
