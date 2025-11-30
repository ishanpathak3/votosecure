"""
Elections Views for VotoSecure
Handles election listing, detail, and voting.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse

from .models import Election, Candidate, Vote, VoteReceipt
from clubs.models import ClubMembership, AuditLog


def home(request):
    """
    Home page showing active global elections and user's club elections.
    """
    now = timezone.now()
    
    # Base queryset for active elections
    active_filter = Q(
        is_open=True,
        start_time__lte=now,
        end_time__gte=now,
        ended_early=False
    )
    
    # Upcoming elections filter
    upcoming_filter = Q(
        is_open=True,
        start_time__gt=now,
        ended_early=False
    )
    
    if request.user.is_authenticated:
        # Get user's approved club memberships
        user_club_ids = ClubMembership.objects.filter(
            user=request.user,
            status='approved'
        ).values_list('club_id', flat=True)
        
        # Show global elections + user's club elections
        visibility_filter = Q(club__isnull=True) | Q(club_id__in=user_club_ids)
        
        # Super admin sees everything
        if request.user.is_superuser:
            visibility_filter = Q()
        
        active_elections = Election.objects.filter(
            active_filter & visibility_filter
        ).select_related('club', 'created_by').order_by('end_time')
        
        upcoming_elections = Election.objects.filter(
            upcoming_filter & visibility_filter
        ).select_related('club', 'created_by').order_by('start_time')[:5]
    else:
        # Anonymous users only see global elections
        active_elections = Election.objects.filter(
            active_filter & Q(club__isnull=True)
        ).select_related('created_by').order_by('end_time')
        
        upcoming_elections = Election.objects.filter(
            upcoming_filter & Q(club__isnull=True)
        ).select_related('created_by').order_by('start_time')[:5]
    
    context = {
        'active_elections': active_elections,
        'upcoming_elections': upcoming_elections,
    }
    return render(request, 'elections/home.html', context)


def election_list(request):
    """
    List all elections visible to the user.
    """
    if request.user.is_authenticated:
        # Get user's approved club memberships
        user_club_ids = ClubMembership.objects.filter(
            user=request.user,
            status='approved'
        ).values_list('club_id', flat=True)
        
        # Show global elections + user's club elections
        visibility_filter = Q(club__isnull=True) | Q(club_id__in=user_club_ids)
        
        # Super admin sees everything
        if request.user.is_superuser:
            visibility_filter = Q()
        
        elections = Election.objects.filter(
            visibility_filter
        ).select_related('club', 'created_by').order_by('-created_at')
    else:
        # Anonymous users only see global elections
        elections = Election.objects.filter(
            club__isnull=True
        ).select_related('created_by').order_by('-created_at')
    
    # Filter by status if requested
    status = request.GET.get('status')
    if status == 'active':
        now = timezone.now()
        elections = elections.filter(
            is_open=True,
            start_time__lte=now,
            end_time__gte=now,
            ended_early=False
        )
    elif status == 'upcoming':
        elections = elections.filter(
            is_open=True,
            start_time__gt=timezone.now(),
            ended_early=False
        )
    elif status == 'ended':
        now = timezone.now()
        elections = elections.filter(
            Q(end_time__lt=now) | Q(ended_early=True)
        )
    
    context = {
        'elections': elections,
        'current_status': status,
    }
    return render(request, 'elections/election_list.html', context)


def election_detail(request, pk):
    """
    Show details of a specific election.
    Includes voting form if eligible, results if election ended.
    """
    election = get_object_or_404(
        Election.objects.select_related('club', 'created_by'),
        pk=pk
    )
    
    # Check if user can view this election
    if election.club and request.user.is_authenticated:
        if not election.can_user_view(request.user):
            messages.error(request, "You don't have access to this election.")
            return redirect('elections:election_list')
    elif election.club and not request.user.is_authenticated:
        messages.info(request, "Please log in to view this club election.")
        return redirect('accounts:login')
    
    candidates = election.candidates.all()
    
    # Check if user has voted
    has_voted = False
    can_vote = False
    vote_message = ""
    
    if request.user.is_authenticated:
        has_voted = VoteReceipt.objects.filter(
            election=election,
            voter=request.user
        ).exists()
        can_vote, vote_message = election.can_user_vote(request.user)
    
    # Get results if election has ended
    show_results = election.results_visible()
    results = None
    total_votes = 0
    
    if show_results:
        total_votes = election.get_total_votes()
        results = []
        for candidate in candidates:
            vote_count = candidate.get_vote_count()
            percentage = candidate.get_vote_percentage(total_votes)
            results.append({
                'candidate': candidate,
                'votes': vote_count,
                'percentage': percentage
            })
        # Sort by votes descending
        results.sort(key=lambda x: x['votes'], reverse=True)
    
    context = {
        'election': election,
        'candidates': candidates,
        'has_voted': has_voted,
        'can_vote': can_vote,
        'vote_message': vote_message,
        'show_results': show_results,
        'results': results,
        'total_votes': total_votes,
    }
    return render(request, 'elections/election_detail.html', context)


@login_required
def cast_vote(request, election_id, candidate_id):
    """
    Cast a vote for a candidate.
    Uses atomic transaction to ensure vote integrity.
    """
    election = get_object_or_404(Election, pk=election_id)
    candidate = get_object_or_404(
        Candidate, 
        pk=candidate_id, 
        election=election
    )
    
    # Check if user can vote
    can_vote, message = election.can_user_vote(request.user)
    if not can_vote:
        messages.error(request, message)
        return redirect('elections:election_detail', pk=election_id)
    
    # Cast the vote atomically
    try:
        with transaction.atomic():
            # Create anonymous vote
            Vote.objects.create(
                election=election,
                candidate=candidate
            )
            
            # Create receipt (proves user voted, but not for whom)
            receipt = VoteReceipt.objects.create(
                election=election,
                voter=request.user
            )
            
            # Log the vote (without revealing the candidate)
            AuditLog.log(
                user=request.user,
                action='vote',
                obj=election,
                details={'receipt_code': receipt.receipt_code},
                ip_address=get_client_ip(request)
            )
            
            messages.success(
                request, 
                f"Your vote has been cast successfully! "
                f"Receipt code: {receipt.receipt_code}"
            )
            
    except Exception as e:
        messages.error(
            request, 
            "An error occurred while casting your vote. Please try again."
        )
    
    return redirect('elections:election_detail', pk=election_id)


@login_required
def election_results_json(request, pk):
    """
    Return election results as JSON for chart rendering.
    Only available after election ends.
    """
    election = get_object_or_404(Election, pk=pk)
    
    # Check if results should be visible
    if not election.results_visible():
        return JsonResponse({'error': 'Results not yet available'}, status=403)
    
    # Check if user can view this election
    if not election.can_user_view(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    candidates = election.candidates.all()
    total_votes = election.get_total_votes()
    
    data = {
        'labels': [c.name for c in candidates],
        'votes': [c.get_vote_count() for c in candidates],
        'percentages': [round(c.get_vote_percentage(total_votes), 1) for c in candidates],
        'total_votes': total_votes,
        'election_title': election.title,
    }
    
    return JsonResponse(data)


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
