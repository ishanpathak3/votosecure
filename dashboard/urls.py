"""
Dashboard URL Configuration
"""

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # ==================
    # Admin Dashboard
    # ==================
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    
    # Clubs management
    path('admin/clubs/', views.admin_clubs, name='admin_clubs'),
    path('admin/clubs/create/', views.admin_club_create, name='admin_club_create'),
    path('admin/clubs/<int:pk>/edit/', views.admin_club_edit, name='admin_club_edit'),
    path('admin/clubs/<int:pk>/delete/', views.admin_club_delete, name='admin_club_delete'),
    
    # Elections management (global)
    path('admin/elections/', views.admin_elections, name='admin_elections'),
    path('admin/elections/create/', views.admin_election_create, name='admin_election_create'),
    path('admin/elections/<int:pk>/edit/', views.admin_election_edit, name='admin_election_edit'),
    path('admin/elections/<int:pk>/delete/', views.admin_election_delete, name='admin_election_delete'),
    path('admin/elections/<int:pk>/end-early/', views.admin_election_end_early, name='admin_election_end_early'),
    
    # Candidates (admin)
    path('admin/elections/<int:election_pk>/candidates/add/', views.admin_candidate_add, name='admin_candidate_add'),
    path('admin/elections/<int:election_pk>/candidates/<int:candidate_pk>/delete/', views.admin_candidate_delete, name='admin_candidate_delete'),
    
    # Users management
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/users/create/', views.admin_user_create, name='admin_user_create'),
    path('admin/users/<int:pk>/edit/', views.admin_user_edit, name='admin_user_edit'),
    
    # ==================
    # Manager Dashboard
    # ==================
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    
    # Members management
    path('manager/members/', views.manager_members, name='manager_members'),
    path('manager/members/<int:pk>/approve/', views.manager_membership_approve, name='manager_membership_approve'),
    path('manager/members/<int:pk>/reject/', views.manager_membership_reject, name='manager_membership_reject'),
    path('manager/members/<int:pk>/remove/', views.manager_membership_remove, name='manager_membership_remove'),
    
    # Elections management (club)
    path('manager/elections/', views.manager_elections, name='manager_elections'),
    path('manager/elections/create/', views.manager_election_create, name='manager_election_create'),
    path('manager/elections/<int:pk>/edit/', views.manager_election_edit, name='manager_election_edit'),
    path('manager/elections/<int:pk>/delete/', views.manager_election_delete, name='manager_election_delete'),
    path('manager/elections/<int:pk>/end-early/', views.manager_election_end_early, name='manager_election_end_early'),
    
    # Candidates (manager)
    path('manager/elections/<int:election_pk>/candidates/add/', views.manager_candidate_add, name='manager_candidate_add'),
    path('manager/elections/<int:election_pk>/candidates/<int:candidate_pk>/delete/', views.manager_candidate_delete, name='manager_candidate_delete'),
]
