from django import forms
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Task
from .models import JournalEntry

class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['title', 'content', 'mood']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 8, 'placeholder': 'Write your journal entry here...'}),
        }

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'due_date', 'reminder']
        widgets = {
            'due_date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'min': timezone.now().strftime('%Y-%m-%dT%H:%M')
                }
            )
        }
    
    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now():
            raise forms.ValidationError("Due date cannot be in the past. Please select a current or future date.")
        return due_date


class SimpleRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text='Required. Must be unique.')
    user_type = forms.ChoiceField(
        choices=[
            ('doctor', 'Doctor'),
            ('teacher', 'Teacher'),
            ('business_professional', 'Business Professional'),
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='User Type'
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'user_type', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make password validation less strict
        self.fields['password1'].help_text = 'At least 3 characters'
        self.fields['password2'].help_text = 'Enter the same password again'
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if len(password1) < 3:
            raise forms.ValidationError('Password must be at least 3 characters long.')
        return password1

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Enforce case-insensitive uniqueness on email
            if User.objects.filter(email__iexact=email).exists():
                raise forms.ValidationError('An account with this email address already exists.')
        return email
