# forms.py
from django import forms
from . import models
from .models import Event, GuestAvailability, AvailableDate, Name
from django.core.exceptions import ValidationError
from datetime import timedelta, datetime, date
from django.utils import timezone
import hashlib

class EventForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Event
        fields = ['name', 'start_date', 'end_date', 'creator_email', 'password']

    def clean_start_date(self):
        start_date = self.cleaned_data['start_date']
        if start_date <= timezone.now():
            raise forms.ValidationError("Start date must be greater than the current date.")
        return start_date

    def clean_end_date(self):
        end_date = self.cleaned_data['end_date']
        start_date = self.cleaned_data.get('start_date')
        if end_date <= start_date:
            raise forms.ValidationError("End date must be greater than the start date.")
        if (end_date - start_date).days > 90:
            raise forms.ValidationError("Event duration cannot exceed 90 days.")
        return end_date

    def save(self, commit=True):
        event = super().save(commit=False)
        event.set_password(self.cleaned_data['password'])
        if commit:
            event.save()
        return event

class GuestAvailabilityForm(forms.ModelForm):
    available_dates = forms.ModelMultipleChoiceField(
        queryset=AvailableDate.objects.none(),  # Dynamically populated in view
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = GuestAvailability
        fields = ['name', 'available_dates']

    def __init__(self, *args, **kwargs):
        event = kwargs.pop("event", None)
        super().__init__(*args, **kwargs)
        if event:
            self.fields['available_dates'].queryset = AvailableDate.objects.filter(event=event)

class NameForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Password",
        #help_text="Enter a secure password."
    )  # Use PasswordInput for hidden input
    email = forms.EmailField(label="Email Address")  # Automatically validates email format

    class Meta:
        model = Name
        fields = ['name', 'start_date', 'end_date', 'email', 'password']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_start_date(self):
        start_date = self.cleaned_data['start_date']
        if start_date < date.today():
            raise forms.ValidationError("The start date must be later than today.")
        return start_date

    def clean_end_date(self):
        end_date = self.cleaned_data['end_date']
        start_date = self.cleaned_data.get('start_date')

        if not start_date:
            raise forms.ValidationError("Please provide a valid start date first.")

        if end_date <= start_date:
            raise forms.ValidationError("The end date must be later than the start date.")

        if end_date > start_date + timedelta(days=90):
            raise forms.ValidationError("The end date must not be more than 90 days after the start date.")

        return end_date

    def clean_password(self):
        password = self.cleaned_data['password']
        # Hash the password using SHA256
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return hashed_password  # Return the hashed password to store it in the database

class PasswordForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Enter Event Password"
    )
