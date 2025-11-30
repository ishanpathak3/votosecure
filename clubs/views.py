"""
Clubs Views for VotoSecure
Handles club listing, detail, membership requests.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q

from .models import Club, ClubMembership, AuditLog
from elections.models import Election


@login_required
def club_list(request):
    """
    List all active clubs with membership status.
    """
    clubs = Club.objects.filter(is_active=True).annotate(
        member_count=Count(
            'memberships',
            filter=Q(memberships__status='approved')
        )
    ).order_by('name')
    
    # Get user's membership status for each club
    user_memberships = {}
    if request.user.is_authenticated:
        memberships = ClubMembership.objects.filter(
            user=request.user
        ).values('club_id', 'status')
        user_memberships = {m['club_id']: m['status'] for m in memberships}
    
    context = {
        'clubs': clubs,
        'user_memberships': user_memberships,
    }
    return render(request, 'clubs/club_list.html', context)


@login_required
def club_detail(request, pk):
    """
    Show club details including elections if member.
    """
    club = get_object_or_404(
        Club.objects.select_related('manager'),
        pk=pk,
        is_active=True
    )
    
    # Get user's membership
    membership = ClubMembership.objects.filter(
        club=club,
        user=request.user
    ).first()
    
    membership_status = membership.status if membership else None
    is_member = membership_status == 'approved'
    is_manager = club.manager == request.user
    is_admin = request.user.is_superuser
    
    # Get elections if member/manager/admin
    elections = None
    if is_member or is_manager or is_admin:
        elections = club.elections.all().order_by('-created_at')
    
    # Get member count
    member_count = club.get_member_count()
    
    context = {
        'club': club,
        'membership': membership,
        'membership_status': membership_status,
        'is_member': is_member,
        'is_manager': is_manager,
        'is_admin': is_admin,
        'elections': elections,
        'member_count': member_count,
    }
    return render(request, 'clubs/club_detail.html', context)


@login_required
def request_membership(request, pk):
    """
    Request to join a club.
    """
    if request.method != 'POST':
        return redirect('clubs:club_detail', pk=pk)
    
    club = get_object_or_404(Club, pk=pk, is_active=True)
    
    # Check if already has membership
    existing = ClubMembership.objects.filter(
        club=club,
        user=request.user
    ).first()
    
    if existing:
        if existing.status == 'pending':
            messages.info(request, "Your membership request is already pending.")
        elif existing.status == 'approved':
            messages.info(request, "You are already a member of this club.")
        elif existing.status == 'rejected':
            # Allow re-requesting if previously rejected
            existing.status = 'pending'
            existing.requested_at = timezone.now()
            existing.reviewed_at = None
            existing.reviewed_by = None
            existing.review_note = ''
            existing.save()
            messages.success(request, "Your membership request has been submitted.")
    else:
        ClubMembership.objects.create(
            club=club,
            user=request.user,
            status='pending'
        )
        messages.success(
            request, 
            f"Your request to join {club.name} has been submitted. "
            "You will be notified once it's reviewed."
        )
    
    return redirect('clubs:club_detail', pk=pk)


@login_required
def cancel_membership_request(request, pk):
    """
    Cancel a pending membership request.
    """
    if request.method != 'POST':
        return redirect('clubs:club_detail', pk=pk)
    
    club = get_object_or_404(Club, pk=pk)
    
    membership = ClubMembership.objects.filter(
        club=club,
        user=request.user,
        status='pending'
    ).first()
    
    if membership:
        membership.delete()
        messages.success(request, "Your membership request has been cancelled.")
    else:
        messages.error(request, "No pending request found.")
    
    return redirect('clubs:club_detail', pk=pk)


@login_required
def leave_club(request, pk):
    """
    Leave a club (remove membership).
    """
    if request.method != 'POST':
        return redirect('clubs:club_detail', pk=pk)
    
    club = get_object_or_404(Club, pk=pk)
    
    # Managers cannot leave (they must be removed by admin)
    if club.manager == request.user:
        messages.error(
            request, 
            "As the club manager, you cannot leave. "
            "Contact an administrator to transfer management."
        )
        return redirect('clubs:club_detail', pk=pk)
    
    membership = ClubMembership.objects.filter(
        club=club,
        user=request.user,
        status='approved'
    ).first()
    
    if membership:
        membership.delete()
        messages.success(request, f"You have left {club.name}.")
    else:
        messages.error(request, "You are not a member of this club.")
    
    return redirect('clubs:club_list')


@login_required
def club_elections(request, pk):
    """
    List all elections for a club (members only).
    """
    club = get_object_or_404(Club, pk=pk, is_active=True)
    
    # Check membership
    is_member = club.is_member(request.user)
    is_manager = club.manager == request.user
    is_admin = request.user.is_superuser
    
    if not (is_member or is_manager or is_admin):
        messages.error(request, "You must be a member to view club elections.")
        return redirect('clubs:club_detail', pk=pk)
    
    elections = club.elections.all().order_by('-created_at')
    
    context = {
        'club': club,
        'elections': elections,
        'is_manager': is_manager,
    }
    return render(request, 'clubs/club_elections.html', context)
