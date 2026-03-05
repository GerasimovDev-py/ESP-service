from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register-page/', views.register_page, name='register_page'),
    path('login-page/', views.login_page, name='login_page'),
    path('cabinet/', views.cabinet, name='cabinet'),
    path('logout/', views.logout_view, name='logout'),
    path('submit-request/', views.submit_request, name='submit_request'),
    path('registration-success/', views.registration_success, name='registration_success'),
    # API для приложения
    path('api/employee-login/', views.employee_login, name='employee_login'),
    path('api/employee-requests/', views.get_employee_requests, name='employee_requests'),
    path('api/notify-client/', views.notify_client_from_app, name='notify_client_from_app'),
]