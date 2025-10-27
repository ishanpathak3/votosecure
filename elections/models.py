from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
class Election(models.Model):
    """A voting election"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_open = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    def is_active(self):
        """Check if election is currently active"""
        now = timezone.now()
        return self.is_open and self.start_time <= now <= self.end_time
    
class Candidate(models.Model):
    """A candidate in an election"""
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.election.title}"

class Vote(models.Model):
    """A vote - NO voter field for anonymity"""
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Vote in {self.election.title}"
    
class VoteReceipt(models.Model):
    """Track who voted (not what they voted for)"""
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    voter = models.ForeignKey(User, on_delete=models.CASCADE)
    voted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('election', 'voter')
    
    def __str__(self):
        return f"{self.voter.username} voted in {self.election.title}"