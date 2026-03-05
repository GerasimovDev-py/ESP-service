from django.contrib import admin
from .models import ServiceRequest, Employee, RegisterUser

@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'department', 'status', 'created_at']
    list_filter = ['status', 'department']
    search_fields = ['full_name', 'request_text']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['username', 'full_name', 'department', 'is_active']
    list_filter = ['department', 'is_active']

@admin.register(RegisterUser)
class RegisterUserAdmin(admin.ModelAdmin):
    list_display = ['login', 'full_name', 'phone', 'email', 'created_at']
    search_fields = ['login', 'full_name', 'phone', 'email']
    
    def get_queryset(self, request):
        return super().get_queryset(request).using('users_db')
    
    def save_model(self, request, obj, form, change):
        obj.save(using='users_db')