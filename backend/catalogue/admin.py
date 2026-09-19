from django.contrib import admin
from .models import Department

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'created_at', 'updated_at')
    search_fields = ('code', 'name')
    list_filter = ('is_active',)
    ordering = ('name',)

