from django.contrib import admin
from account.models import User, Plan
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

# Register your models here.

class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_key', 'price', 'duration_days', 'billing_requests', 'is_unlimited', 'is_active')
    list_filter = ('is_active', 'has_unlimited_bills', 'has_inventory_management')
    search_fields = ('name', 'plan_key', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('plan_key', 'name', 'description', 'price', 'duration_days', 'billing_requests')
        }),
        ('Base Features', {
            'fields': ('has_unlimited_bills', 'has_cloud_storage', 'has_gst_compliance', 'has_multi_device')
        }),
        ('Premium Features', {
            'fields': ('has_cloud_backup', 'has_24x7_support', 'has_inventory_management')
        }),
        ('Advanced Features', {
            'fields': ('has_insights_dashboard', 'has_sales_reports', 'has_inventory_reports', 'has_excel_export')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


class UserModelAdmin(BaseUserAdmin):
    # The fields to be used in displaying the User model.
    list_display = ('email', 'first_name', 'last_name', 'mobile_number', 'current_plan', 'is_account_activated', 'plan_expiry_date', 'is_active')
    list_filter = ('is_admin', 'is_active', 'is_account_activated', 'current_plan')
    fieldsets = (
        ('User Credentials', {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'mobile_number')}),
        ('GST Information', {'fields': ('gstin_number', 'gst_percentage')}),
        ('Plan Information', {'fields': ('current_plan', 'plan_expiry_date', 'billing_requests_remaining')}),
        ('Permissions', {'fields': ('is_admin', 'is_active', 'is_account_activated')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserModelAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'mobile_number', 'password1', 'password2'),
        }),
    )
    search_fields = ('email', 'first_name', 'last_name', 'mobile_number')
    ordering = ('email', 'id')
    filter_horizontal = ()
    readonly_fields = ('created_at', 'updated_at')
    
    # Admin actions
    actions = ['activate_accounts', 'deactivate_accounts']
    
    def activate_accounts(self, request, queryset):
        """Activate selected user accounts"""
        count = 0
        for user in queryset:
            user.activate_account()
            count += 1
        self.message_user(request, f'{count} account(s) successfully activated.')
    activate_accounts.short_description = 'Activate selected accounts'
    
    def deactivate_accounts(self, request, queryset):
        """Deactivate selected user accounts"""
        count = 0
        for user in queryset:
            user.deactivate_account()
            count += 1
        self.message_user(request, f'{count} account(s) successfully deactivated.')
    deactivate_accounts.short_description = 'Deactivate selected accounts'


# Now register the models...
admin.site.register(Plan, PlanAdmin)
admin.site.register(User, UserModelAdmin)
