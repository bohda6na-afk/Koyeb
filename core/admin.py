
from django.contrib import admin
from .models import User, HelpRequest, Response

admin.site.register(User)
admin.site.register(HelpRequest)
admin.site.register(Response)
