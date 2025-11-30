"""
Clubs Models for VotoSecure
Handles clubs and membership management.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Club(models.Model):
    """
    A club/organization that can hold elections.
    Each club has exactly one Election Manager.
    """
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    
    # The election manager for this club (one per club)
    manager = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_club',
        help_text="The Election Manager for this club"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_clubs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Optional fields for richer club profiles
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive clubs cannot hold new elections"
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_member_count(self):
        """Return count of approved members."""
        return self.memberships.filter(status='approved').count()

    def get_pending_requests_count(self):
        """Return count of pending membership requests."""
        return self.memberships.filter(status='pending').count()

    def get_active_elections_count(self):
        """Return count of currently active elections."""
        return self.elections.filter(
            is_open=True,
            start_time__lte=timezone.now(),
            end_time__gte=timezone.now(),
            ended_early=False
        ).count()

    def is_member(self, user):
        """Check if user is an approved member."""
        if not user.is_authenticated:
            return False
        return self.memberships.filter(
            user=user, 
            status='approved'
        ).exists()

    def is_manager(self, user):
        """Check if user is the manager of this club."""
        return self.manager == user

    def get_membership_status(self, user):
        """Get user's membership status for this club."""
        if not user.is_authenticated:
            return None
        membership = self.memberships.filter(user=user).first()
        return membership.status if membership else None


class ClubMembership(models.Model):
    """
    Membership record linking users to clubs.
    Users request membership, managers approve/reject.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='club_memberships'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_memberships'
    )
    
    # Optional note from manager
    review_note = models.TextField(blank=True)

    class Meta:
        unique_together = ('club', 'user')
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.user.username} - {self.club.name} ({self.status})"

    def approve(self, reviewer):
        """Approve the membership request."""
        self.status = 'approved'
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.save()

    def reject(self, reviewer, note=''):
        """Reject the membership request."""
        self.status = 'rejected'
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.review_note = note
        self.save()


class AuditLog(models.Model):
    """
    Audit trail for tracking important actions.
    Useful for accountability and debugging.
    """
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('vote', 'Vote Cast'),
        ('membership_approve', 'Membership Approved'),
        ('membership_reject', 'Membership Rejected'),
        ('election_end_early', 'Election Ended Early'),
        ('manager_assign', 'Manager Assigned'),
        ('manager_remove', 'Manager Removed'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name}"

    @classmethod
    def log(cls, user, action, obj, details=None, ip_address=None):
        """Helper method to create audit log entries."""
        return cls.objects.create(
            user=user,
            action=action,
            model_name=obj.__class__.__name__,
            object_id=obj.pk if obj.pk else None,
            object_repr=str(obj)[:200],
            details=details or {},
            ip_address=ip_address
        )
