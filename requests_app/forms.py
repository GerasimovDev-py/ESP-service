from django import forms
from .models import ServiceRequest

class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ['full_name', 'organization', 'department', 'payment_doc', 'request_text']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите ФИО'}),
            'organization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите организацию'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'payment_doc': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите № платежного листа'}),
            'request_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Опишите вашу проблему'}),
        }