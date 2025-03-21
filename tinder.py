# Project Structure:
# military_tinder/
#   manage.py
#   military_tinder/
#     __init__.py
#     settings.py
#     urls.py
#     asgi.py
#     wsgi.py
#   core/
#     __init__.py
#     models.py
#     views.py
#     urls.py
#     forms.py
#     admin.py
#     templates/
#       core/
#         index.html
#         profile.html
#         request_detail.html
#         volunteer_dashboard.html
#         military_dashboard.html

# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('military', 'Військовий'),
        ('volunteer', 'Волонтер'),
    )
    
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True)
    location = models.CharField(max_length=100, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username

class HelpRequest(models.Model):
    URGENCY_CHOICES = (
        ('low', 'ТЕРМІНОВІСТЬ: НИЗЬКА'),
        ('medium', 'ТЕРМІНОВІСТЬ: СЕРЕДНЯ'),
        ('high', 'ТЕРМІНОВІСТЬ: ВИСОКА'),
    )
    
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests')
    title = models.CharField(max_length=100)
    description = models.TextField()
    help_type = models.CharField(max_length=100)  # e.g., "Тактична медицина"
    location = models.CharField(max_length=100)
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='medium')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    contact_person = models.CharField(max_length=100, blank=True)
    contact_position = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.requester.username}"

class Response(models.Model):
    STATUS_CHOICES = (
        ('pending', 'В очікуванні'),
        ('accepted', 'Прийнято'),
        ('completed', 'Виконано'),
        ('cancelled', 'Скасовано'),
    )
    
    request = models.ForeignKey(HelpRequest, on_delete=models.CASCADE, related_name='responses')
    volunteer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='responses')
    message = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Response from {self.volunteer.username} to {self.request.title}"

class Chat(models.Model):
    request = models.ForeignKey(HelpRequest, on_delete=models.CASCADE, related_name='chats')
    military = models.ForeignKey(User, on_delete=models.CASCADE, related_name='military_chats')
    volunteer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='volunteer_chats')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Chat between {self.military.username} and {self.volunteer.username}"

class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Message from {self.sender.username} at {self.sent_at}"

# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.db.models import Q
from .models import User, HelpRequest, Response, Chat, Message
from .forms import UserRegistrationForm, HelpRequestForm, ResponseForm, MessageForm

def index(request):
    """Landing page view"""
    return render(request, 'core/index.html')

def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            if user.user_type == 'military':
                return redirect('military_dashboard')
            else:
                return redirect('volunteer_dashboard')
    else:
        form = UserRegistrationForm()
    return render(request, 'core/register.html', {'form': form})

@login_required
def profile(request):
    """User profile view"""
    return render(request, 'core/profile.html', {'user': request.user})

@login_required
def military_dashboard(request):
    """Dashboard for military users"""
    if request.user.user_type != 'military':
        return redirect('volunteer_dashboard')
    
    requests = HelpRequest.objects.filter(requester=request.user).order_by('-created_at')
    return render(request, 'core/military_dashboard.html', {'requests': requests})

@login_required
def volunteer_dashboard(request):
    """Dashboard for volunteer users"""
    if request.user.user_type != 'volunteer':
        return redirect('military_dashboard')
    
    active_requests = HelpRequest.objects.filter(is_active=True).order_by('-created_at')
    responded_requests = HelpRequest.objects.filter(
        responses__volunteer=request.user
    ).distinct().order_by('-created_at')
    
    return render(request, 'core/volunteer_dashboard.html', {
        'active_requests': active_requests,
        'responded_requests': responded_requests
    })

@login_required
def create_request(request):
    """Create a new help request"""
    if request.user.user_type != 'military':
        return redirect('volunteer_dashboard')
    
    if request.method == 'POST':
        form = HelpRequestForm(request.POST)
        if form.is_valid():
            help_request = form.save(commit=False)
            help_request.requester = request.user
            help_request.save()
            return redirect('military_dashboard')
    else:
        form = HelpRequestForm()
    
    return render(request, 'core/create_request.html', {'form': form})

@login_required
def request_detail(request, request_id):
    """View details of a specific help request"""
    help_request = get_object_or_404(HelpRequest, id=request_id)
    responses = Response.objects.filter(request=help_request).order_by('-created_at')
    
    if request.method == 'POST' and request.user.user_type == 'volunteer':
        form = ResponseForm(request.POST)
        if form.is_valid():
            response = form.save(commit=False)
            response.request = help_request
            response.volunteer = request.user
            response.save()
            return redirect('request_detail', request_id=request_id)
    else:
        form = ResponseForm()
    
    context = {
        'help_request': help_request,
        'responses': responses,
        'form': form
    }
    
    return render(request, 'core/request_detail.html', context)

@login_required
def swipe_interface(request):
    """Tinder-like swipe interface for volunteers"""
    if request.user.user_type != 'volunteer':
        return redirect('military_dashboard')
    
    # Get requests the volunteer hasn't responded to yet
    responded_requests = Response.objects.filter(volunteer=request.user).values_list('request_id', flat=True)
    available_requests = HelpRequest.objects.filter(is_active=True).exclude(id__in=responded_requests)
    
    if not available_requests:
        return render(request, 'core/no_requests.html')
    
    current_request = available_requests.first()
    
    return render(request, 'core/swipe_interface.html', {'help_request': current_request})

@login_required
def handle_response(request, request_id, action):
    """Handle volunteer's response (accept/decline) to a help request"""
    if request.user.user_type != 'volunteer':
        return redirect('military_dashboard')
    
    help_request = get_object_or_404(HelpRequest, id=request_id)
    
    if action == 'accept':
        # Create a response object
        Response.objects.create(
            request=help_request,
            volunteer=request.user,
            message="I can help with this request",
            status='pending'
        )
        # Create a chat
        Chat.objects.create(
            request=help_request,
            military=help_request.requester,
            volunteer=request.user
        )
    
    # Redirect to next request
    return redirect('swipe_interface')

@login_required
def chats(request):
    """View all chats for the current user"""
    if request.user.user_type == 'military':
        chats = Chat.objects.filter(military=request.user).order_by('-created_at')
    else:
        chats = Chat.objects.filter(volunteer=request.user).order_by('-created_at')
    
    return render(request, 'core/chats.html', {'chats': chats})

@login_required
def chat_detail(request, chat_id):
    """View a specific chat and send messages"""
    chat = get_object_or_404(Chat, id=chat_id)
    
    # Check if user is part of this chat
    if request.user != chat.military and request.user != chat.volunteer:
        return redirect('chats')
    
    messages = Message.objects.filter(chat=chat).order_by('sent_at')
    
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.chat = chat
            message.sender = request.user
            message.save()
            return redirect('chat_detail', chat_id=chat_id)
    else:
        form = MessageForm()
    
    context = {
        'chat': chat,
        'messages': messages,
        'form': form
    }
    
    return render(request, 'core/chat_detail.html', context)

# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, HelpRequest, Response, Message

class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'first_name', 'last_name', 
                 'user_type', 'phone_number', 'location', 'profile_picture']

class HelpRequestForm(forms.ModelForm):
    class Meta:
        model = HelpRequest
        fields = ['title', 'description', 'help_type', 'location', 'urgency', 
                 'contact_person', 'contact_position']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class ResponseForm(forms.ModelForm):
    class Meta:
        model = Response
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3}),
        }

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2}),
        }

# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('military/dashboard/', views.military_dashboard, name='military_dashboard'),
    path('volunteer/dashboard/', views.volunteer_dashboard, name='volunteer_dashboard'),
    path('request/create/', views.create_request, name='create_request'),
    path('request/<int:request_id>/', views.request_detail, name='request_detail'),
    path('swipe/', views.swipe_interface, name='swipe_interface'),
    path('request/<int:request_id>/<str:action>/', views.handle_response, name='handle_response'),
    path('chats/', views.chats, name='chats'),
    path('chat/<int:chat_id>/', views.chat_detail, name='chat_detail'),
]

# admin.py
from django.contrib import admin
from .models import User, HelpRequest, Response, Chat, Message

admin.site.register(User)
admin.site.register(HelpRequest)
admin.site.register(Response)
admin.site.register(Chat)
admin.site.register(Message)

# settings.py (additions)
# Add these to your project's settings.py

INSTALLED_APPS = [
    # ... other apps
    'core',
]

AUTH_USER_MODEL = 'core.User'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Main project urls.py (additions)
# Add these to your project's main urls.py

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... other patterns
    path('', include('core.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)