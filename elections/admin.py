from django.contrib import admin
from .models import Election, Candidate, Vote, VoteReceipt


class CandidateInline(admin.TabularInline):
    """Add candidates when creating an election"""
    model = Candidate
    extra = 3


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by', 'start_time', 'end_time', 'is_open']
    list_filter = ['is_open', 'created_at']
    search_fields = ['title', 'description']
    inlines = [CandidateInline]


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['name', 'election']
    list_filter = ['election']


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['election', 'candidate', 'timestamp']
    list_filter = ['election', 'timestamp']
    
    def has_add_permission(self, request):
        return False


@admin.register(VoteReceipt)
class VoteReceiptAdmin(admin.ModelAdmin):
    list_display = ['voter', 'election', 'voted_at']
    list_filter = ['election']
    
    def has_add_permission(self, request):
        return False