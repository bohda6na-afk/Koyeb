
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
