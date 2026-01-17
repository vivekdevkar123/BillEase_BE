from django.db import models
from account.models import User

# Create your models here.

class Product(models.Model):
    """
    Product Catalog - Each user maintains their own product catalog
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    manage_inventory = models.BooleanField(default=False, help_text='Whether to track inventory for this product')
    stock_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Available stock quantity')
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', 'name']),
        ]
    
    def __str__(self):
        return f"#{self.id} - {self.name} - ₹{self.price}"


class Bill(models.Model):
    """
    Bill - Bills stored in backend
    Items are stored as JSON in the items field
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bills')
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    items = models.JSONField(default=list, help_text='List of items in the bill')
    
    # Amount fields
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Subtotal before GST')
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='CGST amount')
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='SGST amount')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Total amount including GST')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed', help_text='Bill status: pending or completed')
    is_paid = models.BooleanField(default=True, help_text='Payment status: True if paid, False if unpaid')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"Bill #{self.id} - {self.customer_name} - ₹{self.total} ({self.status})"
