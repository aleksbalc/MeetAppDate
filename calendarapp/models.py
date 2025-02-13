#models.py
from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from django.contrib.auth.hashers import make_password

import hashlib
import datetime
import secrets
from datetime import timedelta

class Event(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateField(default=datetime.date.today)
    end_date = models.DateField(default=datetime.date.today)
    email = models.EmailField(default='')
    password = models.CharField(max_length=128, default='')  # 128 to handle Django's hashed password format
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
    
class GuestAvailability(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, default = '')

class AvailableDate(models.Model):
    guest = models.ForeignKey(GuestAvailability, on_delete=models.CASCADE, default=None)
    date = models.DateField(default=datetime.date.today)