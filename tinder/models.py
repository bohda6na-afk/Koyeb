
from django.db import models
from django.contrib.auth.models import AbstractUser

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
    help_type = models.CharField(max_length=100)
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
