"""
Accounts Views for VotoSecure
Handles user registration, profile, and authentication.
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms

from clubs.models import ClubMembership
from elections.models import VoteReceipt


class RegistrationForm(UserCreationForm):
    """
    Extended registration form with email and name fields.
    """
    email = forms.EmailField(
        required=True,
        help_text="Enter a valid email address."
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        help_text="Enter your first name."
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        help_text="Enter your last name."
    )
    
    class Meta:
        model = User
        fields = [
            'username', 
            'email', 
            'first_name', 
            'last_name', 
            'password1', 
            'password2'
        ]
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class ProfileForm(forms.ModelForm):
    """
    Form for updating user profile.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already in use.")
        return email


def register(request):
    """
    Handle user registration.
    """
    if request.user.is_authenticated:
        return redirect('elections:home')
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Log the user in
            login(request, user)
            
            messages.success(
                request, 
                f"Welcome to VotoSecure, {user.first_name}! "
                "Your account has been created successfully."
            )
            return redirect('elections:home')
    else:
        form = RegistrationForm()
    
    context = {
        'form': form,
    }
    return render(request, 'accounts/register.html', context)


@login_required
def profile(request):
    """
    View and edit user profile.
    """
    # Get user's club memberships
    memberships = ClubMembership.objects.filter(
        user=request.user
    ).select_related('club').order_by('club__name')
    
    approved_memberships = memberships.filter(status='approved')
    pending_memberships = memberships.filter(status='pending')
    
    # Get voting history
    vote_receipts = VoteReceipt.objects.filter(
        voter=request.user
    ).select_related('election', 'election__club').order_by('-voted_at')[:10]
    
    # Check if user is a manager
    managed_club = getattr(request.user, 'managed_club', None)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
    
    context = {
        'form': form,
        'approved_memberships': approved_memberships,
        'pending_memberships': pending_memberships,
        'vote_receipts': vote_receipts,
        'managed_club': managed_club,
    }
    return render(request, 'accounts/profile.html', context)
