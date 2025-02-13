from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from django.contrib.auth.hashers import make_password

import hashlib
import datetime
import secrets
from datetime import timedelta


class Event(models.Model):
    name = models.CharField(max_length=50)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    password_hash = models.CharField(max_length=64)  # SHA-256 hash of the password
    slug = models.SlugField(unique=True, blank=True)  # Randomized unique identifier for the URL
    creator_email = models.EmailField(default='')  # Creator's email for OTP
    otp = models.CharField(max_length=6, default='')  # One-time password
    otp_verified = models.BooleanField(default=False)

    def clean(self):
        """Validate date span is less than 3 months"""
        if self.end_date - self.start_date > timedelta(days=90):
            raise ValidationError("Event duration cannot exceed 3 months")
        if self.start_date < timezone.now():
            raise ValidationError("Start date cannot be in the past")

    def save(self, *args, **kwargs):
        """Generate a unique slug if not provided"""
        if not self.slug:
            self.slug = secrets.token_urlsafe(16)  # Random 16-character URL-safe string
        super().save(*args, **kwargs)

    def set_password(self, password):
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

    def __str__(self):
        return self.name


class AvailableDate(models.Model):
    """Individual dates in the event's range for availability"""
    event = models.ForeignKey('calendarapp.Event', on_delete=models.CASCADE)  # Use string reference
    date = models.DateField()

    def __str__(self):
        return str(self.date)


class GuestAvailability(models.Model):
    event = models.ForeignKey('calendarapp.Event', on_delete=models.CASCADE)  # Use string reference
    name = models.CharField(max_length=50)
    available_dates = models.ManyToManyField(AvailableDate, related_name='guest_availability')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.event.name})"



class Name(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateField(default=datetime.date.today)
    end_date = models.DateField(default=datetime.date.today)
    email = models.EmailField(default='')
    password = models.CharField(max_length=128)  # 128 to handle Django's hashed password format
    access_code = models.CharField(max_length=16, unique=True, blank=True)  # Random code

    def save(self, *args, **kwargs):
        if not self.access_code:
            self.access_code = secrets.token_urlsafe(12)[:16]  # Generate a 16-character code

        # Automatically hash the password if it's not already hashed
        if not self.password.startswith('pbkdf2_'):  # Check if it's already hashed
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
