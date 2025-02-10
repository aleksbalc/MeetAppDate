from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import hashlib

class Event(models.Model):
    name = models.CharField(max_length=50)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    password_hash = models.CharField(max_length=64)  # SHA-256 hash
    
    def set_password(self, password):
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    def check_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()
    
    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    events = models.ManyToManyField(Event, through='Availability')
    
    def __str__(self):
        return self.user.username

class Availability(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    available_date = models.DateField()
    
    class Meta:
        unique_together = ('user', 'event', 'available_date')
        indexes = [
            models.Index(fields=['event', 'available_date']),
        ]
    
    def __str__(self):
        return f"{self.user.user.username} - {self.event.name} - {self.available_date}"