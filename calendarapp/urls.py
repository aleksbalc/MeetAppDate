from django.urls import path, re_path
from django.contrib import admin
from . import views


urlpatterns = [

    # The home page
    path('', views.index, name='home'),
    path('admin/', admin.site.urls),
    # path('create-event/', views.create_event, name='create-event'),
    path('add/', views.add_event, name='add_event'),
    path('send-otp/', views.send_otp, name='send_otp'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('event/<str:access_code>/', views.show_event, name='show_event'),
    path('event/<str:access_code>/add-availability/', views.add_availability, name='add_availability'),]
