from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.views import LoginView, LogoutView
from .forms import UserRegistrationForm, UserProfileForm
from .models import UserProfile

class CustomLoginView(LoginView):
    template_name = 'authentication/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        user_role = self.request.user.profile.role
        if user_role == 'military':
            return reverse_lazy('volunteer_list')
        else:  # volunteer
            return reverse_lazy('request_list')

class CustomLogoutView(LogoutView):
    next_page = 'login'

class RegisterView(CreateView):
    form_class = UserRegistrationForm
    template_name = 'authentication/register.html'
    success_url = reverse_lazy('profile_setup')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Authenticate and login after registration
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password1')
        user = authenticate(username=username, password=password)
        login(self.request, user)
        return response

@login_required
def profile_setup(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            # Redirect based on user role
            if request.user.profile.role == 'military':
                return redirect('volunteer_list')
            else:
                return redirect('request_list')
    else:
        form = UserProfileForm(instance=request.user.profile)
    
    return render(request, 'authentication/profile_setup.html', {'form': form})

@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('profile_detail', pk=request.user.profile.pk)
    else:
        form = UserProfileForm(instance=request.user.profile)
    
    return render(request, 'authentication/profile_edit.html', {'form': form})