from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from .models import Like, Match
from authentication.models import UserProfile
from requests.models import HelpRequest

@login_required
def create_like(request, profile_id=None, request_id=None):
    """
    Create a like for a profile or request
    Check if a match is created
    """
    from_user = request.user.profile
    
    if profile_id:
        to_user = get_object_or_404(UserProfile, pk=profile_id)
        help_request = None
    elif request_id:
        help_request = get_object_or_404(HelpRequest, pk=request_id)
        to_user = help_request.military_user
    else:
        return JsonResponse({'error': 'No profile or request specified'}, status=400)
    
    # Create the like
    like, created = Like.objects.get_or_create(
        from_user=from_user,
        to_user=to_user,
        request=help_request
    )
    
    # Check if there's a match (the other user has already liked this user)
    match_created = False
    if created:
        # Check for reciprocal like
        reciprocal_like = Like.objects.filter(
            from_user=to_user,
            to_user=from_user
        ).first()
        
        if reciprocal_like:
            # Create a match
            if from_user.role == 'military':
                military_user = from_user
                volunteer_user = to_user
            else:
                military_user = to_user
                volunteer_user = from_user
            
            Match.objects.create(
                military_user=military_user,
                volunteer_user=volunteer_user,
                request=help_request
            )
            match_created = True
    
    if request.is_ajax():
        return JsonResponse({
            'success': True,
            'created': created,
            'match_created': match_created
        })
    else:
        if match_created:
            return redirect('match_detail')
        return redirect('profile_list')

class MatchListView(LoginRequiredMixin, ListView):
    model = Match
    template_name = 'matches/match_list.html'
    context_object_name = 'matches'
    
    def get_queryset(self):
        user_profile = self.request.user.profile
        
        if user_profile.role == 'military':
            return Match.objects.filter(military_user=user_profile).order_by('-created_at')
        else:  # volunteer
            return Match.objects.filter(volunteer_user=user_profile).order_by('-created_at')