"""
Elections Models for VotoSecure
Handles elections, candidates, votes, and vote receipts.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Election(models.Model):
    """
    A voting election - can be global (club=None) or club-specific.
    """
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='created_elections'
    )
    
    # Club association - None means global election
    club = models.ForeignKey(
        'clubs.Club',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='elections',
        help_text="Leave empty for global elections"
    )
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_open = models.BooleanField(
        default=False,
        help_text="Must be True for voting to be allowed"
    )
    
    # Early termination tracking
    ended_early = models.BooleanField(default=False)
    ended_early_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ended_elections'
    )
    ended_early_at = models.DateTimeField(null=True, blank=True)
    ended_early_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        prefix = f"[{self.club.name}]" if self.club else "[Global]"
        return f"{prefix} {self.title}"

    def is_active(self):
        """Check if election is currently active for voting."""
        if self.ended_early:
            return False
        now = timezone.now()
        return self.is_open and self.start_time <= now <= self.end_time

    def is_ended(self):
        """Check if election has ended (either naturally or early)."""
        if self.ended_early:
            return True
        return timezone.now() > self.end_time

    def is_upcoming(self):
        """Check if election hasn't started yet."""
        return timezone.now() < self.start_time

    def get_status(self):
        """Return human-readable status."""
        if self.ended_early:
            return 'ended_early'
        if not self.is_open:
            return 'draft'
        now = timezone.now()
        if now < self.start_time:
            return 'upcoming'
        if now > self.end_time:
            return 'ended'
        return 'active'

    def get_status_display(self):
        """Return display-friendly status."""
        status_map = {
            'draft': 'Draft',
            'upcoming': 'Upcoming',
            'active': 'Active',
            'ended': 'Ended',
            'ended_early': 'Ended Early'
        }
        return status_map.get(self.get_status(), 'Unknown')

    def get_total_votes(self):
        """Return total number of votes cast."""
        return self.votes.count()

    def can_user_vote(self, user):
        """
        Check if a user is eligible to vote in this election.
        Returns (can_vote: bool, reason: str)
        """
        if not user.is_authenticated:
            return False, "You must be logged in to vote."
        
        if not self.is_active():
            return False, "This election is not currently active."
        
        # Check if already voted
        if VoteReceipt.objects.filter(election=self, voter=user).exists():
            return False, "You have already voted in this election."
        
        # For club elections, check membership
        if self.club:
            from clubs.models import ClubMembership
            is_member = ClubMembership.objects.filter(
                club=self.club,
                user=user,
                status='approved'
            ).exists()
            if not is_member:
                return False, "You must be an approved member of this club to vote."
        
        return True, "You are eligible to vote."

    def can_user_view(self, user):
        """
        Check if a user can view this election.
        Global elections are visible to all authenticated users.
        Club elections are visible to club members.
        """
        if not user.is_authenticated:
            return False
        
        # Super admins can see everything
        if user.is_superuser:
            return True
        
        # Global elections visible to all
        if not self.club:
            return True
        
        # Club elections visible to members
        from clubs.models import ClubMembership
        return ClubMembership.objects.filter(
            club=self.club,
            user=user,
            status='approved'
        ).exists()

    def can_user_manage(self, user):
        """Check if user can manage this election."""
        if user.is_superuser:
            return True
        
        if self.club and self.club.manager == user:
            return True
        
        return False

    def results_visible(self):
        """Check if results should be visible."""
        return self.is_ended()

    def end_early(self, user, reason=''):
        """End the election early."""
        self.ended_early = True
        self.ended_early_by = user
        self.ended_early_at = timezone.now()
        self.ended_early_reason = reason
        self.save()


class Candidate(models.Model):
    """A candidate in an election."""
    election = models.ForeignKey(
        Election, 
        on_delete=models.CASCADE,
        related_name='candidates'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(
        default=0,
        help_text="Display order on ballot"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position', 'name']

    def __str__(self):
        return f"{self.name} - {self.election.title}"

    def get_vote_count(self):
        """Return number of votes for this candidate."""
        return self.votes.count()

    def get_vote_percentage(self, total_votes=None):
        """Return percentage of votes."""
        if total_votes is None:
            total_votes = self.election.get_total_votes()
        if total_votes == 0:
            return 0
        return (self.get_vote_count() / total_votes) * 100


class Vote(models.Model):
    """
    A vote record - NO voter field for anonymity.
    The separation between Vote and VoteReceipt ensures
    we can verify WHO voted without knowing WHAT they voted for.
    """
    election = models.ForeignKey(
        Election, 
        on_delete=models.CASCADE,
        related_name='votes'
    )
    candidate = models.ForeignKey(
        Candidate, 
        on_delete=models.CASCADE,
        related_name='votes'
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Vote for {self.candidate.name} in {self.election.title}"


class VoteReceipt(models.Model):
    """
    Track who voted (not what they voted for).
    This provides accountability while maintaining ballot secrecy.
    """
    election = models.ForeignKey(
        Election, 
        on_delete=models.CASCADE,
        related_name='receipts'
    )
    voter = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='vote_receipts'
    )
    voted_at = models.DateTimeField(auto_now_add=True)
    
    # Optional: store a hash for receipt verification
    receipt_code = models.CharField(max_length=64, blank=True)

    class Meta:
        unique_together = ('election', 'voter')
        ordering = ['-voted_at']

    def __str__(self):
        return f"{self.voter.username} voted in {self.election.title}"

    def save(self, *args, **kwargs):
        if not self.receipt_code:
            import hashlib
            import uuid
            data = f"{self.election_id}-{self.voter_id}-{uuid.uuid4()}"
            self.receipt_code = hashlib.sha256(data.encode()).hexdigest()[:16].upper()
        super().save(*args, **kwargs)
