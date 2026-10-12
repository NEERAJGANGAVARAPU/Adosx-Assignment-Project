from django.urls import path
from reconciliation import views

urlpatterns = [
    path('api/disagreements/', views.disagreements_api, name='disagreements_api'),
]
