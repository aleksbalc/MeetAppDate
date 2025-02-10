from django.contrib import admin
from .models import Event, UserProfile, Availability

admin.site.register(Event)
admin.site.register(UserProfile)
admin.site.register(Availability)
