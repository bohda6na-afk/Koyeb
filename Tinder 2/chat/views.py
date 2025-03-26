from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Message
from matches.models import Match
from .forms import MessageForm

@login_required
def chat_view(request, match_id):
    match = get_object_or_404(Match, pk=match_id)
    user_profile = request.user.profile
    
    # Ensure the user is part of this match
    if not (match.military_user == user_profile or match.volunteer_user == user_profile):
        return redirect('match_list')
    
    # Mark all messages from the other user as read
    Message.objects.filter(
        match=match,
        sender__in=[match.military_user, match.volunteer_user],
        sender__isnull=False  # Redundant but explicit
    ).exclude(sender=user_profile).update(is_read=True)
    
    # Get all messages for this match
    messages = Message.objects.filter(match=match).order_by('created_at')
    
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.match = match
            message.sender = user_profile
            message.save()
            
            if request.is_ajax():
                return JsonResponse({
                    'status': 'success',
                    'message': {
                        'id': message.id,
                        'content': message.content,
                        'sender_id': message.sender.id,
                        'created_at': message.created_at.strftime('%H:%M %d-%m-%Y'),
                    }
                })
            return redirect('chat', match_id=match_id)
    else:
        form = MessageForm()
    
    # Determine who the other user is
    if user_profile == match.military_user:
        other_user = match.volunteer_user
    else:
        other_user = match.military_user
    
    context = {
        'match': match,
        'messages': messages,
        'form': form,
        'other_user': other_user,
    }
    
    return render(request, 'chat/chat.html', context)

class ChatListView(LoginRequiredMixin, ListView):
    model = Match
    template_name = 'chat/chat_list.html'
    context_object_name = 'matches'
    
    def get_queryset(self):
        user_profile = self.request.user.profile
        
        if user_profile.role == 'military':
            return Match.objects.filter(military_user=user_profile).order_by('-created_at')
        else:  # volunteer
            return Match.objects.filter(volunteer_user=user_profile).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_profile = self.request.user.profile
        
        # Count unread messages for each match
        unread_counts = {}
        for match in context['matches']:
            unread_counts[match.id] = Message.objects.filter(
                match=match, 
                is_read=False
            ).exclude(sender=user_profile).count()
        
        context['unread_counts'] = unread_counts
        return context