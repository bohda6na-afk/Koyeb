from django import forms
from .models import HelpRequest

class HelpRequestForm(forms.ModelForm):
    class Meta:
        model = HelpRequest
        fields = ('title', 'description', 'urgency', 'location')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }