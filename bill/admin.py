from django.contrib import admin
from bill.models import Bill, Product

# Register your models here.

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'stock_quantity', 'is_active', 'user', 'created_at']
    list_filter = ['is_active', 'user', 'created_at']
    search_fields = ['name', 'description', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Product Information', {
            'fields': ('id', 'user', 'name', 'description', 'price')
        }),
        ('Inventory', {
            'fields': ('stock_quantity',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'customer_phone', 'subtotal', 'cgst_amount', 'sgst_amount', 'total', 'status', 'user', 'created_at']
    list_filter = ['status', 'created_at', 'user']
    search_fields = ['customer_name', 'customer_phone', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'subtotal', 'cgst_amount', 'sgst_amount', 'total']
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'customer_name', 'customer_phone')
        }),
        ('Bill Details', {
            'fields': ('items', 'status')
        }),
        ('Amount Breakdown', {
            'fields': ('subtotal', 'cgst_amount', 'sgst_amount', 'total')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
