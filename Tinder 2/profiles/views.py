from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.utils.decorators import method_decorator
from authentication.models import UserProfile
from requests.models import HelpRequest

@method_decorator(login_required, name='dispatch')
class ProfileListView(ListView):
    model = UserProfile
    template_name = 'profiles/profile_list.html'
    context_object_name = 'profiles'
    
    def get_queryset(self):
        user_role = self.request.user.profile.role
        
        # Military users see volunteers, volunteers see military users
        if user_role == 'military':
            return UserProfile.objects.filter(role='volunteer', verified=True)
        else:  # volunteer
            return UserProfile.objects.filter(role='military', verified=True)

@method_decorator(login_required, name='dispatch')
class ProfileDetailView(DetailView):
    model = UserProfile
    template_name = 'profiles/profile_detail.html'
    context_object_name = 'profile'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        viewed_profile = self.get_object()
        
        # If viewing a military profile, show their requests
        if viewed_profile.role == 'military':
            context['requests'] = HelpRequest.objects.filter(
                military_user=viewed_profile
            ).order_by('-created_at')
        
        return context

@login_required
def view_next_profile(request):
    """
    Tinder-like functionality to show next available profile
    """
    user_role = request.user.profile.role
    
    # Determine which profiles to show based on user role
    if user_role == 'military':
        profiles = UserProfile.objects.filter(role='volunteer', verified=True)
    else:  # volunteer
        profiles = UserProfile.objects.filter(role='military', verified=True)
    
    # TODO: Implement logic to show unseen profiles or filter by preferences
    next_profile = profiles.first()
    
    return render(request, 'profiles/swipe_profile.html', {'profile': next_profile})