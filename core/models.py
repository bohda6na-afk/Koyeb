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

    # Вказуємо явно поле, яке використовується для входу
    USERNAME_FIELD = "username"  
    REQUIRED_FIELDS = ["email"]  # Додаткові обов’язкові поля при створенні суперкористувача

    def __str__(self):
        return self.username
