from django.core.management import execute_from_command_line
import os
import sys

# Налаштування Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

# Код для автоматичного створення проекту
def setup_django_project():
    # Створюємо папки і файли проекту
    if not os.path.exists("test_project"):
        os.makedirs("test_project")
    
    # Створюємо settings.py
    with open("test_project/settings.py", "w", encoding = "utf-8") as f:
        f.write("""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-test-key-for-military-tinder'

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'test_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'test_project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uk-ua'
TIME_ZONE = 'Europe/Kiev'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'core.User'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
""")
    
    # Створюємо urls.py
    with open("test_project/urls.py", "w", encoding="utf-8") as f:
        f.write("""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
""")
    
    # Створюємо __init__.py
    with open("test_project/__init__.py", "w", encoding="utf-8") as f:
        f.write("")
    
    # Створюємо папку для core app
    if not os.path.exists("core"):
        os.makedirs("core")
        os.makedirs("core/templates/core")
    
    # Створюємо __init__.py для core
    with open("core/__init__.py", "w", encoding="utf-8") as f:
        f.write("")
    
    # Створюємо models.py
    with open("core/models.py", "w", encoding="utf-8") as f:
        f.write("""
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
""")
    
    # Створюємо views.py з простою тестовою сторінкою
    with open("core/views.py", "w", encoding="utf-8") as f:
        f.write("""
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import HelpRequest

def index(request):
    # Проста тестова сторінка з прикладом Tinder-інтерфейсу
    sample_request = None
    if HelpRequest.objects.exists():
        sample_request = HelpRequest.objects.first()
    
    # Якщо немає запитів у базі даних, показуємо тестові дані
    if not sample_request:
        sample_request = {
            'location': 'Запоріжжя',
            'requester': {'first_name': 'Микола'},
            'help_type': 'Тактична медицина',
            'description': 'Потрібні турнікети, гемостатичні бинти, оклюзивні наклейки, декомпресійні голки. Запас ліків вичерпується. Термінова доставка на позиції за 10 км від Запоріжжя. Є можливість зустрітися в місті для передачі. Контактна особа – Микола, командир медичного підрозділу.',
            'get_urgency_display': 'ТЕРМІНОВІСТЬ: ВИСОКА'
        }
    
    return render(request, 'core/swipe_interface.html', {'help_request': sample_request})

def test_view(request):
    return HttpResponse('''
    <h1>MilitaryTinder працює!</h1>
    <p>Базова функціональність запущена. Ви можете перейти на <a href="/">головну сторінку</a> для перегляду інтерфейсу.</p>
    <p>Для повного тестування вам потрібно:</p>
    <ol>
        <li>Перейти до <a href="/admin/">панелі адміністратора</a></li>
        <li>Створити користувачів (військових та волонтерів)</li>
        <li>Створити запити на допомогу</li>
    </ol>
    ''')
""")
    
    # Створюємо urls.py для core
    with open("core/urls.py", "w", encoding="utf-8") as f:
        f.write("""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('test/', views.test_view, name='test'),
]
""")
    
    # Створюємо admin.py
    with open("core/admin.py", "w", encoding="utf-8") as f:
        f.write("""
from django.contrib import admin
from .models import User, HelpRequest, Response

admin.site.register(User)
admin.site.register(HelpRequest)
admin.site.register(Response)
""")
    
    # Створюємо базовий шаблон
    with open("core/templates/core/swipe_interface.html", "w", encoding="utf-8") as f:
        f.write("""
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MilitaryTinder</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: Arial, sans-serif;
        }
        
        body {
            background-color: #f5f5f5;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        
        .app-container {
            width: 100%;
            max-width: 380px;
            background-color: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            border-bottom: 1px solid #eee;
            background-color: white;
        }
        
        .menu-icon, .settings-icon {
            width: 32px;
            height: 32px;
            display: flex;
            justify-content: center;
            align-items: center;
            background-color: #f0f0f0;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
        }
        
        .logo {
            font-weight: bold;
            font-size: 16px;
        }
        
        .profile-container {
            padding: 15px;
            flex-grow: 1;
            position: relative;
            background-color: #f9f9f9;
        }
        
        .location-tag {
            background-color: #e0e0e0;
            color: #333;
            padding: 4px 12px;
            border-radius: 20px;
            display: inline-block;
            font-size: 14px;
            margin-bottom: 15px;
        }
        
        .profile-photo-container {
            position: relative;
            display: flex;
            justify-content: center;
        }
        
        .profile-photo {
            width: 120px;
            height: 120px;
            background-color: #e0e0e0;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #777;
            font-size: 14px;
            margin-bottom: 15px;
        }
        
        .check-icon {
            position: absolute;
            right: 130px;
            top: 0;
            width: 32px;
            height: 32px;
            background-color: #2196f3;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            color: white;
            font-weight: bold;
        }
        
        .profile-card {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }
        
        .name {
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .occupation {
            font-size: 16px;
            color: #555;
            margin-bottom: 15px;
        }
        
        .description {
            text-align: center;
            margin-bottom: 15px;
            line-height: 1.4;
            color: #333;
            font-size: 14px;
        }
        
        .urgency {
            background-color: #f0f0f0;
            color: #333;
            padding: 4px 12px;
            border-radius: 20px;
            display: inline-block;
            font-size: 12px;
            text-transform: uppercase;
            margin: 5px auto;
        }
        
        .action-buttons {
            display: flex;
            justify-content: space-between;
            padding: 15px;
            background-color: white;
        }
        
        .action-button {
            padding: 10px 15px;
            border-radius: 30px;
            border: none;
            font-weight: bold;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
        }
        
        .decline {
            background-color: #9e9e9e;
            color: white;
            width: 40px;
            height: 40px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .more-info {
            background-color: #3f51b5;
            color: white;
        }
        
        .accept {
            background-color: #4caf50;
            color: white;
        }
        
        .bottom-nav {
            display: flex;
            justify-content: space-between;
            border-top: 1px solid #eee;
            padding: 12px 15px;
            background-color: white;
        }
        
        .nav-item {
            width: 32px;
            height: 32px;
            background-color: #f0f0f0;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
        }
        
        .nav-center {
            background-color: #546e7a;
            color: white;
        }
    </style>
</head>
<body>
    <div class="app-container">
        <div class="header">
            <div class="menu-icon">≡</div>
            <div class="logo">MilitaryTinder</div>
            <div class="settings-icon">⚙</div>
        </div>
        
        <div class="profile-container">
            <div class="location-tag" id="location">{{ help_request.location }}</div>
            
            <div class="profile-photo-container">
                <div class="profile-photo">фото</div>
                <div class="check-icon">✓</div>
            </div>
            
            <div class="profile-card">
                <h1 class="name" id="userName">{{ help_request.requester.first_name }}</h1>
                <div class="occupation" id="userOccupation">{{ help_request.help_type }}</div>
                
                <div class="description" id="userDescription">
                    {{ help_request.description }}
                </div>
                
                <div class="urgency" id="urgencyLevel">{{ help_request.get_urgency_display }}</div>
            </div>
        </div>
        
        <div class="action-buttons">
            <button class="action-button decline">✕</button>
            <button class="action-button more-info">Більше інформації</button>
            <button class="action-button accept">Беруся</button>
        </div>
        
        <div class="bottom-nav">
            <div class="nav-item">👨</div>
            <div class="nav-item nav-center">🔍</div>
            <div class="nav-item">👤</div>
        </div>
    </div>

    <script>
        // Просте демо-функціонування кнопок
        document.querySelector('.decline').addEventListener('click', function() {
            alert('Відхилено');
        });
        
        document.querySelector('.more-info').addEventListener('click', function() {
            alert('Відкриваємо більше інформації');
        });
        
        document.querySelector('.accept').addEventListener('click', function() {
            alert('Прийнято! Відправляємо повідомлення...');
        });
    </script>
</body>
</html>
""")
    
    # Створюємо wsgi.py
    with open("test_project/wsgi.py", "w", encoding="utf-8") as f:
        f.write("""
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_project.settings')
application = get_wsgi_application()
""")
    
    # Створюємо asgi.py
    with open("test_project/asgi.py", "w", encoding="utf-8") as f:
        f.write("""
import os
from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_project.settings')
application = get_asgi_application()
""")

# Основний код виконання
if __name__ == "__main__":
    # Перевіряємо, чи встановлено Django
    try:
        import django
    except ImportError:
        print("Django не встановлено. Встановлюємо...")
        os.system("pip install django pillow")
        import django
    
    # Налаштовуємо проект
    setup_django_project()
    
    if len(sys.argv) == 1:
        # Якщо немає аргументів, запускаємо міграції та сервер
        sys.argv.extend(["makemigrations", "core"])
        execute_from_command_line(sys.argv)
        
        sys.argv = sys.argv[:1]
        sys.argv.extend(["migrate"])
        execute_from_command_line(sys.argv)
        
        print("\nСтворюємо суперкористувача (адміністратора)...")
        print("Введіть дані для входу в адмін-панель:")
        
        from django.contrib.auth.management.commands.createsuperuser import Command as SuperUserCommand
        cmd = SuperUserCommand()
        cmd.handle(interactive=True)
        
        print("\nЗапускаємо сервер...")
        print("Відкрийте браузер і перейдіть на http://127.0.0.1:8000/")
        print("Для адмін-панелі перейдіть на http://127.0.0.1:8000/admin/")
        
        sys.argv = sys.argv[:1]
        sys.argv.extend(["runserver"])
        execute_from_command_line(sys.argv)
    else:
        # Якщо є аргументи, просто передаємо їх Django
        execute_from_command_line(sys.argv)