from django.contrib import admin
from .models import Event, AvailableDate, GuestAvailability, Name

admin.site.register(Name)
admin.site.register(Event)
admin.site.register(AvailableDate)
admin.site.register(GuestAvailability)
