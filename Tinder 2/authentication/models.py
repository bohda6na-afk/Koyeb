from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLES = (
        ('military', 'Військовий'),
        ('volunteer', 'Волонтер'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLES)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('profile_detail', kwargs={'pk': self.pk})