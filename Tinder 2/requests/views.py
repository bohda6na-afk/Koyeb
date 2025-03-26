from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from .models import HelpRequest
from .forms import HelpRequestForm
from authentication.models import UserProfile

class MilitaryRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.profile.role == 'military'

class RequestListView(LoginRequiredMixin, ListView):
    model = HelpRequest
    template_name = 'requests/request_list.html'
    context_object_name = 'requests'
    ordering = ['-created_at']
    
    def get_queryset(self):
        user_role = self.request.user.profile.role
        
        if user_role == 'military':
            # Military users see only their own requests
            return HelpRequest.objects.filter(
                military_user=self.request.user.profile
            ).order_by('-created_at')
        else:  # volunteer
            # Volunteers see all active requests from military users
            return HelpRequest.objects.filter(
                status='active'
            ).order_by('-created_at')

class RequestDetailView(LoginRequiredMixin, DetailView):
    model = HelpRequest
    template_name = 'requests/request_detail.html'
    context_object_name = 'request'

class CreateRequestView(LoginRequiredMixin, MilitaryRequiredMixin, CreateView):
    model = HelpRequest
    form_class = HelpRequestForm
    template_name = 'requests/request_form.html'
    success_url = reverse_lazy('request_list')
    
    def form_valid(self, form):
        form.instance.military_user = self.request.user.profile
        return super().form_valid(form)

class UpdateRequestView(LoginRequiredMixin, MilitaryRequiredMixin, UpdateView):
    model = HelpRequest
    form_class = HelpRequestForm
    template_name = 'requests/request_form.html'
    
    def get_queryset(self):
        # Ensure users can only update their own requests
        return HelpRequest.objects.filter(military_user=self.request.user.profile)

@login_required
def change_request_status(request, pk, status):
    help_request = get_object_or_404(HelpRequest, pk=pk)
    
    # Military users can change status of their own requests
    # Volunteers can only mark requests as "in_progress"
    user_role = request.user.profile.role
    
    if (user_role == 'military' and help_request.military_user == request.user.profile) or \
       (user_role == 'volunteer' and status == 'in_progress'):
        help_request.status = status
        help_request.save()
    
    return redirect('request_detail', pk=pk)