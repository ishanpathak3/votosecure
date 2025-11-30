"""
Dashboard Views for VotoSecure
Admin dashboard and Election Manager dashboard.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django import forms

from elections.models import Election, Candidate, Vote, VoteReceipt
from clubs.models import Club, ClubMembership, AuditLog


# =====================
# Permission Decorators
# =====================

def is_superuser(user):
    """Check if user is a superuser (admin)."""
    return user.is_superuser


def is_manager(user):
    """Check if user is a club manager."""
    return hasattr(user, 'managed_club') and user.managed_club is not None


def is_admin_or_manager(user):
    """Check if user is admin or manager."""
    return user.is_superuser or is_manager(user)


# =====================
# Forms
# =====================

class ClubForm(forms.ModelForm):
    """Form for creating/editing clubs."""
    class Meta:
        model = Club
        fields = ['name', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class ClubManagerForm(forms.Form):
    """Form for assigning a manager to a club."""
    manager = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        empty_label="-- No Manager --",
        help_text="Select a user to be the Election Manager for this club."
    )
    
    def __init__(self, *args, club=None, **kwargs):
        super().__init__(*args, **kwargs)
        if club:
            # Exclude users who already manage other clubs
            existing_managers = Club.objects.exclude(pk=club.pk).exclude(
                manager__isnull=True
            ).values_list('manager_id', flat=True)
            self.fields['manager'].queryset = User.objects.filter(
                is_active=True
            ).exclude(pk__in=existing_managers).exclude(is_superuser=True)


class ElectionForm(forms.ModelForm):
    """Form for creating/editing elections."""
    class Meta:
        model = Election
        fields = ['title', 'description', 'start_time', 'end_time', 'is_open']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'start_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'end_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make datetime inputs work properly
        if self.instance.pk:
            if self.instance.start_time:
                self.initial['start_time'] = self.instance.start_time.strftime('%Y-%m-%dT%H:%M')
            if self.instance.end_time:
                self.initial['end_time'] = self.instance.end_time.strftime('%Y-%m-%dT%H:%M')


class CandidateForm(forms.ModelForm):
    """Form for creating/editing candidates."""
    class Meta:
        model = Candidate
        fields = ['name', 'description', 'position']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class UserForm(forms.ModelForm):
    """Form for creating/editing users (admin only)."""
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Leave blank to keep current password (for editing)."
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


# =====================
# Admin Dashboard Views
# =====================

@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_dashboard(request):
    """
    Main admin dashboard with overview statistics.
    """
    now = timezone.now()
    
    # Statistics
    total_users = User.objects.filter(is_active=True).count()
    total_clubs = Club.objects.filter(is_active=True).count()
    total_elections = Election.objects.count()
    active_elections = Election.objects.filter(
        is_open=True,
        start_time__lte=now,
        end_time__gte=now,
        ended_early=False
    ).count()
    total_votes = Vote.objects.count()
    pending_memberships = ClubMembership.objects.filter(status='pending').count()
    
    # Recent activity
    recent_elections = Election.objects.select_related(
        'club', 'created_by'
    ).order_by('-created_at')[:5]
    
    recent_users = User.objects.order_by('-date_joined')[:5]
    
    recent_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]
    
    context = {
        'total_users': total_users,
        'total_clubs': total_clubs,
        'total_elections': total_elections,
        'active_elections': active_elections,
        'total_votes': total_votes,
        'pending_memberships': pending_memberships,
        'recent_elections': recent_elections,
        'recent_users': recent_users,
        'recent_logs': recent_logs,
    }
    return render(request, 'dashboard/admin/dashboard.html', context)


@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_clubs(request):
    """
    Admin view for managing clubs.
    """
    clubs = Club.objects.annotate(
        member_count=Count('memberships', filter=Q(memberships__status='approved')),
        election_count=Count('elections')
    ).select_related('manager').order_by('name')
    
    context = {
        'clubs': clubs,
    }
    return render(request, 'dashboard/admin/clubs.html', context)


@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_club_create(request):
    """
    Create a new club.
    """
    if request.method == 'POST':
        form = ClubForm(request.POST)
        if form.is_valid():
            club = form.save(commit=False)
            club.created_by = request.user
            club.save()
            
            AuditLog.log(
                user=request.user,
                action='create',
                obj=club,
                details={'name': club.name}
            )
            
            messages.success(request, f"Club '{club.name}' has been created.")
            return redirect('dashboard:admin_club_edit', pk=club.pk)
    else:
        form = ClubForm()
    
    context = {
        'form': form,
        'title': 'Create Club',
    }
    return render(request, 'dashboard/admin/club_form.html', context)


@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_club_edit(request, pk):
    """
    Edit a club and assign manager.
    """
    club = get_object_or_404(Club, pk=pk)
    
    if request.method == 'POST':
        if 'save_club' in request.POST:
            form = ClubForm(request.POST, instance=club)
            manager_form = ClubManagerForm(club=club)
            if form.is_valid():
                form.save()
                AuditLog.log(
                    user=request.user,
                    action='update',
                    obj=club,
                    details={'name': club.name}
                )
                messages.success(request, f"Club '{club.name}' has been updated.")
                return redirect('dashboard:admin_clubs')
        
        elif 'assign_manager' in request.POST:
            form = ClubForm(instance=club)
            manager_form = ClubManagerForm(request.POST, club=club)
            if manager_form.is_valid():
                old_manager = club.manager
                new_manager = manager_form.cleaned_data['manager']
                
                club.manager = new_manager
                club.save()
                
                if old_manager != new_manager:
                    action = 'manager_assign' if new_manager else 'manager_remove'
                    AuditLog.log(
                        user=request.user,
                        action=action,
                        obj=club,
                        details={
                            'old_manager': str(old_manager) if old_manager else None,
                            'new_manager': str(new_manager) if new_manager else None
                        }
                    )
                
                if new_manager:
                    messages.success(
                        request, 
                        f"{new_manager.username} is now the manager of {club.name}."
                    )
                else:
                    messages.success(request, f"Manager removed from {club.name}.")
                return redirect('dashboard:admin_club_edit', pk=pk)
    else:
        form = ClubForm(instance=club)
        manager_form = ClubManagerForm(club=club, initial={'manager': club.manager})
    
    context = {
        'form': form,
        'manager_form': manager_form,
        'club': club,
        'title': f'Edit Club: {club.name}',
    }
    return render(request, 'dashboard/admin/club_form.html', context)


@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_club_delete(request, pk):
    """
    Delete a club.
    """
    club = get_object_or_404(Club, pk=pk)
    
    if request.method == 'POST':
        name = club.name
        AuditLog.log(
            user=request.user,
            action='delete',
            obj=club,
            details={'name': name}
        )
        club.delete()
        messages.success(request, f"Club '{name}' has been deleted.")
        return redirect('dashboard:admin_clubs')
    
    context = {
        'club': club,
    }
    return render(request, 'dashboard/admin/club_delete.html', context)


@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_elections(request):
    """
    Admin view for managing all elections (primarily global elections).
    """
    elections = Election.objects.select_related(
        'club', 'created_by'
    ).annotate(
        vote_count=Count('votes')
    ).order_by('-created_at')
    
    # Filter options
    filter_type = request.GET.get('type', 'all')
    if filter_type == 'global':
        elections = elections.filter(club__isnull=True)
    elif filter_type == 'club':
        elections = elections.filter(club__isnull=False)
    
    context = {
        'elections': elections,
        'filter_type': filter_type,
    }
    return render(request, 'dashboard/admin/elections.html', context)


@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_election_create(request):
    """
    Create a new global election.
    """
    if request.method == 'POST':
        form = ElectionForm(request.POST)
        if form.is_valid():
            election = form.save(commit=False)
            election.created_by = request.user
            election.club = None  # Global election
            election.save()
            
            AuditLog.log(
                user=request.user,
                action='create',
                obj=election,
                details={'title': election.title, 'type': 'global'}
            )
            
            messages.success(
                request, 
                f"Global election '{election.title}' has been created. "
                "Now add candidates."
            )
            return redirect('dashboard:admin_election_edit', pk=election.pk)
    else:
        form = ElectionForm()
    
    context = {
        'form': form,
        'title': 'Create Global Election',
    }
    return render(request, 'dashboard/admin/election_form.html', context)


@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_election_edit(request, pk):
    """
    Edit an election (admin can edit any election).
    """
    election = get_object_or_404(Election, pk=pk)
    candidates = election.candidates.all()
    
    if request.method == 'POST':
        form = ElectionForm(request.POST, instance=election)
        if form.is_valid():
            form.save()
            AuditLog.log(
                user=request.user,
                action='update',
                obj=election,
                details={'title': election.title}
            )
            messages.success(request, f"Election '{election.title}' has been updated.")
            return redirect('dashboard:admin_elections')
    else:
        form = ElectionForm(instance=election)
    
    candidate_form = CandidateForm()
    
    context = {
        'form': form,
        'candidate_form': candidate_form,
        'election': election,
        'candidates': candidates,
        'title': f'Edit Election: {election.title}',
    }
    return render(request, 'dashboard/admin/election_form.html', context)


@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_election_delete(request, pk):
    """
    Delete an election.
    """
    election = get_object_or_404(Election, pk=pk)
    
    if request.method == 'POST':
        title = election.title
        AuditLog.log(
            user=request.user,
            action='delete',
            obj=election,
            details={'title': title}
        )
        election.delete()
        messages.success(request, f"Election '{title}' has been deleted.")
        return redirect('dashboard:admin_elections')
    
    context = {
        'election': election,
    }
    return render(request, 'dashboard/admin/election_delete.html', context)


@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_election_end_early(request, pk):
    """
    End an election early.
    """
    election = get_object_or_404(Election, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        election.end_early(request.user, reason)
        
        AuditLog.log(
            user=request.user,
            action='election_end_early',
            obj=election,
            details={'reason': reason}
        )
        
        messages.success(request, f"Election '{election.title}' has been ended early.")
        return redirect('dashboard:admin_elections')
    
    context = {
        'election': election,
    }
    return render(request, 'dashboard/admin/election_end_early.html', context)


@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_candidate_add(request, election_pk):
    """
    Add a candidate to an election.
    """
    election = get_object_or_404(Election, pk=election_pk)
    
    if request.method == 'POST':
        form = CandidateForm(request.POST)
        if form.is_valid():
            candidate = form.save(commit=False)
            candidate.election = election
            candidate.save()
            messages.success(request, f"Candidate '{candidate.name}' has been added.")
            return redirect('dashboard:admin_election_edit', pk=election_pk)
    
    return redirect('dashboard:admin_election_edit', pk=election_pk)


@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_candidate_delete(request, election_pk, candidate_pk):
    """
    Delete a candidate from an election.
    """
    election = get_object_or_404(Election, pk=election_pk)
    candidate = get_object_or_404(Candidate, pk=candidate_pk, election=election)
    
    if request.method == 'POST':
        # Don't allow deleting candidates from active elections with votes
        if election.is_active() and candidate.votes.exists():
            messages.error(
                request, 
                "Cannot delete a candidate who has received votes in an active election."
            )
        else:
            name = candidate.name
            candidate.delete()
            messages.success(request, f"Candidate '{name}' has been removed.")
    
    return redirect('dashboard:admin_election_edit', pk=election_pk)


@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_users(request):
    """
    Admin view for managing users.
    """
    users = User.objects.annotate(
        vote_count=Count('vote_receipts')
    ).order_by('-date_joined')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    context = {
        'users': users,
        'search': search,
    }
    return render(request, 'dashboard/admin/users.html', context)


@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_user_create(request):
    """
    Create a new user.
    """
    if request.method == 'POST':
        form = UserForm(request.POST)
        password = request.POST.get('password')
        if form.is_valid():
            user = form.save(commit=False)
            if password:
                user.set_password(password)
            else:
                messages.error(request, "Password is required for new users.")
                return render(request, 'dashboard/admin/user_form.html', {
                    'form': form,
                    'title': 'Create User'
                })
            user.save()
            
            AuditLog.log(
                user=request.user,
                action='create',
                obj=user,
                details={'username': user.username}
            )
            
            messages.success(request, f"User '{user.username}' has been created.")
            return redirect('dashboard:admin_users')
    else:
        form = UserForm()
    
    context = {
        'form': form,
        'title': 'Create User',
        'is_create': True,
    }
    return render(request, 'dashboard/admin/user_form.html', context)


@login_required
@user_passes_test(is_superuser, login_url='elections:home')
def admin_user_edit(request, pk):
    """
    Edit a user.
    """
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            AuditLog.log(
                user=request.user,
                action='update',
                obj=user,
                details={'username': user.username}
            )
            messages.success(request, f"User '{user.username}' has been updated.")
            return redirect('dashboard:admin_users')
    else:
        form = UserForm(instance=user)
    
    context = {
        'form': form,
        'edit_user': user,
        'title': f'Edit User: {user.username}',
        'is_create': False,
    }
    return render(request, 'dashboard/admin/user_form.html', context)


# =====================
# Manager Dashboard Views
# =====================

@login_required
@user_passes_test(is_manager, login_url='elections:home')
def manager_dashboard(request):
    """
    Election Manager dashboard for their club.
    """
    club = request.user.managed_club
    now = timezone.now()
    
    # Statistics
    member_count = club.get_member_count()
    pending_requests = club.get_pending_requests_count()
    total_elections = club.elections.count()
    active_elections = club.elections.filter(
        is_open=True,
        start_time__lte=now,
        end_time__gte=now,
        ended_early=False
    ).count()
    
    # Recent elections
    recent_elections = club.elections.annotate(
        vote_count=Count('votes')
    ).order_by('-created_at')[:5]
    
    # Pending membership requests
    pending_memberships = ClubMembership.objects.filter(
        club=club,
        status='pending'
    ).select_related('user').order_by('requested_at')[:5]
    
    context = {
        'club': club,
        'member_count': member_count,
        'pending_requests': pending_requests,
        'total_elections': total_elections,
        'active_elections': active_elections,
        'recent_elections': recent_elections,
        'pending_memberships': pending_memberships,
    }
    return render(request, 'dashboard/manager/dashboard.html', context)


@login_required
@user_passes_test(is_manager, login_url='elections:home')
def manager_members(request):
    """
    Manage club membership requests.
    """
    club = request.user.managed_club
    
    # Get all memberships
    pending = ClubMembership.objects.filter(
        club=club,
        status='pending'
    ).select_related('user').order_by('requested_at')
    
    approved = ClubMembership.objects.filter(
        club=club,
        status='approved'
    ).select_related('user').order_by('user__username')
    
    rejected = ClubMembership.objects.filter(
        club=club,
        status='rejected'
    ).select_related('user').order_by('-reviewed_at')[:20]
    
    context = {
        'club': club,
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
    }
    return render(request, 'dashboard/manager/members.html', context)


@login_required
@user_passes_test(is_manager, login_url='elections:home')
def manager_membership_approve(request, pk):
    """
    Approve a membership request.
    """
    club = request.user.managed_club
    membership = get_object_or_404(
        ClubMembership,
        pk=pk,
        club=club,
        status='pending'
    )
    
    if request.method == 'POST':
        membership.approve(request.user)
        
        AuditLog.log(
            user=request.user,
            action='membership_approve',
            obj=membership,
            details={
                'member': membership.user.username,
                'club': club.name
            }
        )
        
        messages.success(
            request,
            f"{membership.user.username} has been approved as a member."
        )
    
    return redirect('dashboard:manager_members')


@login_required
@user_passes_test(is_manager, login_url='elections:home')
def manager_membership_reject(request, pk):
    """
    Reject a membership request.
    """
    club = request.user.managed_club
    membership = get_object_or_404(
        ClubMembership,
        pk=pk,
        club=club,
        status='pending'
    )
    
    if request.method == 'POST':
        note = request.POST.get('note', '')
        membership.reject(request.user, note)
        
        AuditLog.log(
            user=request.user,
            action='membership_reject',
            obj=membership,
            details={
                'member': membership.user.username,
                'club': club.name,
                'note': note
            }
        )
        
        messages.success(
            request,
            f"{membership.user.username}'s request has been rejected."
        )
    
    return redirect('dashboard:manager_members')


@login_required
@user_passes_test(is_manager, login_url='elections:home')
def manager_membership_remove(request, pk):
    """
    Remove a member from the club.
    """
    club = request.user.managed_club
    membership = get_object_or_404(
        ClubMembership,
        pk=pk,
        club=club,
        status='approved'
    )
    
    if request.method == 'POST':
        username = membership.user.username
        membership.delete()
        messages.success(request, f"{username} has been removed from the club.")
    
    return redirect('dashboard:manager_members')


@login_required
@user_passes_test(is_manager, login_url='elections:home')
def manager_elections(request):
    """
    Manage club elections.
    """
    club = request.user.managed_club
    
    elections = club.elections.annotate(
        vote_count=Count('votes')
    ).order_by('-created_at')
    
    context = {
        'club': club,
        'elections': elections,
    }
    return render(request, 'dashboard/manager/elections.html', context)


@login_required
@user_passes_test(is_manager, login_url='elections:home')
def manager_election_create(request):
    """
    Create a new club election.
    """
    club = request.user.managed_club
    
    if request.method == 'POST':
        form = ElectionForm(request.POST)
        if form.is_valid():
            election = form.save(commit=False)
            election.created_by = request.user
            election.club = club
            election.save()
            
            AuditLog.log(
                user=request.user,
                action='create',
                obj=election,
                details={'title': election.title, 'club': club.name}
            )
            
            messages.success(
                request,
                f"Election '{election.title}' has been created. Now add candidates."
            )
            return redirect('dashboard:manager_election_edit', pk=election.pk)
    else:
        form = ElectionForm()
    
    context = {
        'form': form,
        'club': club,
        'title': 'Create Club Election',
    }
    return render(request, 'dashboard/manager/election_form.html', context)


@login_required
@user_passes_test(is_manager, login_url='elections:home')
def manager_election_edit(request, pk):
    """
    Edit a club election.
    """
    club = request.user.managed_club
    election = get_object_or_404(Election, pk=pk, club=club)
    candidates = election.candidates.all()
    
    if request.method == 'POST':
        form = ElectionForm(request.POST, instance=election)
        if form.is_valid():
            form.save()
            AuditLog.log(
                user=request.user,
                action='update',
                obj=election,
                details={'title': election.title}
            )
            messages.success(request, f"Election '{election.title}' has been updated.")
            return redirect('dashboard:manager_elections')
    else:
        form = ElectionForm(instance=election)
    
    candidate_form = CandidateForm()
    
    context = {
        'form': form,
        'candidate_form': candidate_form,
        'election': election,
        'candidates': candidates,
        'club': club,
        'title': f'Edit Election: {election.title}',
    }
    return render(request, 'dashboard/manager/election_form.html', context)


@login_required
@user_passes_test(is_manager, login_url='elections:home')
def manager_election_delete(request, pk):
    """
    Delete a club election.
    """
    club = request.user.managed_club
    election = get_object_or_404(Election, pk=pk, club=club)
    
    if request.method == 'POST':
        title = election.title
        AuditLog.log(
            user=request.user,
            action='delete',
            obj=election,
            details={'title': title, 'club': club.name}
        )
        election.delete()
        messages.success(request, f"Election '{title}' has been deleted.")
        return redirect('dashboard:manager_elections')
    
    context = {
        'election': election,
        'club': club,
    }
    return render(request, 'dashboard/manager/election_delete.html', context)


@login_required
@user_passes_test(is_manager, login_url='elections:home')
def manager_election_end_early(request, pk):
    """
    End a club election early.
    """
    club = request.user.managed_club
    election = get_object_or_404(Election, pk=pk, club=club)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        election.end_early(request.user, reason)
        
        AuditLog.log(
            user=request.user,
            action='election_end_early',
            obj=election,
            details={'reason': reason, 'club': club.name}
        )
        
        messages.success(request, f"Election '{election.title}' has been ended early.")
        return redirect('dashboard:manager_elections')
    
    context = {
        'election': election,
        'club': club,
    }
    return render(request, 'dashboard/manager/election_end_early.html', context)


@login_required
@user_passes_test(is_manager, login_url='elections:home')
def manager_candidate_add(request, election_pk):
    """
    Add a candidate to a club election.
    """
    club = request.user.managed_club
    election = get_object_or_404(Election, pk=election_pk, club=club)
    
    if request.method == 'POST':
        form = CandidateForm(request.POST)
        if form.is_valid():
            candidate = form.save(commit=False)
            candidate.election = election
            candidate.save()
            messages.success(request, f"Candidate '{candidate.name}' has been added.")
    
    return redirect('dashboard:manager_election_edit', pk=election_pk)


@login_required
@user_passes_test(is_manager, login_url='elections:home')
def manager_candidate_delete(request, election_pk, candidate_pk):
    """
    Delete a candidate from a club election.
    """
    club = request.user.managed_club
    election = get_object_or_404(Election, pk=election_pk, club=club)
    candidate = get_object_or_404(Candidate, pk=candidate_pk, election=election)
    
    if request.method == 'POST':
        if election.is_active() and candidate.votes.exists():
            messages.error(
                request,
                "Cannot delete a candidate who has received votes in an active election."
            )
        else:
            name = candidate.name
            candidate.delete()
            messages.success(request, f"Candidate '{name}' has been removed.")
    
    return redirect('dashboard:manager_election_edit', pk=election_pk)
