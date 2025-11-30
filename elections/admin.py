from django.contrib import admin
from .models import Election, Candidate, Vote, VoteReceipt


class CandidateInline(admin.TabularInline):
    model = Candidate
    extra = 1


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'club', 'is_open', 'start_time', 'end_time', 'get_status_display']
    list_filter = ['is_open', 'club', 'ended_early']
    search_fields = ['title', 'description']
    inlines = [CandidateInline]
    date_hierarchy = 'created_at'


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['name', 'election', 'position']
    list_filter = ['election']
    search_fields = ['name', 'election__title']


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['election', 'candidate', 'timestamp']
    list_filter = ['election', 'candidate']
    readonly_fields = ['election', 'candidate', 'timestamp']


@admin.register(VoteReceipt)
class VoteReceiptAdmin(admin.ModelAdmin):
    list_display = ['voter', 'election', 'voted_at', 'receipt_code']
    list_filter = ['election']
    search_fields = ['voter__username', 'receipt_code']
    readonly_fields = ['voter', 'election', 'voted_at', 'receipt_code']
