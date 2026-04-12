from .import views
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('',views.index, name='index'),
    path('studentreg',views.studentregisters, name='studentreg'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('logout-preloader/', views.logout_with_preloader, name='logout_preloader'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
]
if settings.DEBUG: 
 urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
