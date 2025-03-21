from django.db import models
from authentication.models import UserProfile

class HelpRequest(models.Model):
    URGENCY_CHOICES = (
        ('low', 'ТЕРМІНОВІСТЬ: НИЗЬКА'),
        ('medium', 'ТЕРМІНОВІСТЬ: СЕРЕДНЯ'),
        ('high', 'ТЕРМІНОВІСТЬ: ВИСОКА'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Активний'),
        ('in_progress', 'В процесі'),
        ('completed', 'Виконано'),
        ('canceled', 'Скасовано'),
    )
    
    military_user = models.ForeignKey(
        UserProfile, 
        on_delete=models.CASCADE, 
        related_name='requests',
        limit_choices_to={'role': 'military'}
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    location = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.military_user.user.username}"
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('request_detail', kwargs={'pk': self.pk})