from django.urls import path, re_path
from django.contrib import admin
from . import views


urlpatterns = [

    # The home page
    path('', views.index, name='home'),
    path('admin/', admin.site.urls),
    #path('new-event/', views.new_event, name='new-event'),
    path('create-event/', views.create_event, name='create-event'),
    path('add/', views.add_name, name='add_name'),
    path('show/', views.show_name, name='show_name'),
    path('event/<str:access_code>/', views.show_event, name='show_event'),
]
