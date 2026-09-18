from django.urls import path
from .views import EmailLogListView

urlpatterns = [
    path('logs/', EmailLogListView.as_view(), name='email_logs'),
    path('logs/<str:pk>/', EmailLogListView.as_view(), name='email_log_detail'),
]
