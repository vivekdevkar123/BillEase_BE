from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.utils import timezone
from datetime import timedelta

# Create your models here.

# Plan Model
class Plan(models.Model):
    """
    Plan model to store different subscription plans
    """
    
    plan_key = models.CharField(max_length=50, unique=True, help_text='Unique plan identifier')
    name = models.CharField(max_length=100, help_text='Plan display name')
    description = models.TextField(blank=True, null=True, help_text='Plan description')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text='Plan price')
    
    # Plan limits and features
    billing_requests = models.IntegerField(default=0, help_text='Number of billing requests (0 = unlimited)')
    duration_days = models.IntegerField(help_text='Plan duration in days')
    
    # Feature flags
    has_unlimited_bills = models.BooleanField(default=False, help_text='Unlimited bill creation')
    has_cloud_storage = models.BooleanField(default=True, help_text='Cloud storage enabled')
    has_gst_compliance = models.BooleanField(default=True, help_text='GST compliance enabled')
    has_multi_device = models.BooleanField(default=True, help_text='Multi-device access')
    has_cloud_backup = models.BooleanField(default=False, help_text='Cloud backup enabled')
    has_24x7_support = models.BooleanField(default=False, help_text='24/7 customer support')
    has_inventory_management = models.BooleanField(default=False, help_text='Inventory management enabled')
    has_insights_dashboard = models.BooleanField(default=False, help_text='Insights dashboard enabled')
    has_sales_reports = models.BooleanField(default=False, help_text='Sales reports enabled')
    has_inventory_reports = models.BooleanField(default=False, help_text='Inventory reports enabled')
    has_excel_export = models.BooleanField(default=False, help_text='Excel export enabled')
    
    # Status
    is_active = models.BooleanField(default=True, help_text='Plan is active and available')
    is_custom = models.BooleanField(default=False, help_text='Custom plan - not shown in public plan list')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['price']
        verbose_name = 'Plan'
        verbose_name_plural = 'Plans'
    
    def __str__(self):
        return f"{self.name} - ₹{self.price}"
    
    @property
    def is_unlimited(self):
        """Check if plan has unlimited billing requests"""
        return self.billing_requests == 0 or self.has_unlimited_bills


# Custom User Manager
class UserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, mobile_number, password=None, **extra_fields):
        """
        Creates and saves a User with the given email, name, mobile number and password.
        """
        if not email:
            raise ValueError('User must have an email address')

        user = self.model(
            email=self.normalize_email(email),
            first_name=first_name,
            last_name=last_name,
            mobile_number=mobile_number,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password, **other_fields):
        other_fields.setdefault('is_admin', True)
        other_fields.setdefault('is_active', True)
        other_fields.setdefault('is_account_activated', True)  # Auto-activate superusers
        
        if not email:
            raise ValueError("Users must have an email address")
        
        email = self.normalize_email(email)
        user = self.model(email=email, **other_fields)
        user.set_password(password)
        user.save()
        return user


class User(AbstractBaseUser):
    email = models.EmailField(
        verbose_name='Email',
        max_length=255,
        unique=True,
    )
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    mobile_number = models.CharField(max_length=13)
    
    # Business details
    business_name = models.CharField(max_length=200, blank=True, null=True, help_text='Business/Company Name')
    business_address = models.TextField(blank=True, null=True, help_text='Business Address')
    upi_id = models.CharField(max_length=100, blank=True, null=True, help_text='UPI ID for digital payments')
    
    # Referral field
    referred_by = models.CharField(max_length=200, blank=True, null=True, help_text='Name of person who referred this user')
    
    # GST-related fields
    gstin_number = models.CharField(max_length=15, blank=True, null=True, help_text='GST Identification Number')
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='GST percentage to apply on bills')
    
    # Billing-related fields
    current_plan = models.ForeignKey('Plan', on_delete=models.SET_NULL, null=True, blank=True, related_name='users', help_text='Current active plan')
    plan_expiry_date = models.DateTimeField(null=True, blank=True, help_text='Expiry date of the billing plan')
    billing_requests_remaining = models.IntegerField(default=0, help_text='Number of billing requests remaining (used for plans with limits)')
    
    # User status fields
    is_active = models.BooleanField(default=True, help_text='User can log in')
    is_account_activated = models.BooleanField(default=False, help_text='Account activated by admin after payment verification')
    is_admin = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'mobile_number']

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        return self.is_admin

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        return self.is_admin
    
    def has_active_plan(self):
        """Check if user has an active billing plan"""
        if not self.plan_expiry_date:
            return False
        return self.plan_expiry_date > timezone.now()
    
    def can_create_bill(self):
        """Check if user can create a new bill"""
        # First check if account is activated
        if not self.is_account_activated:
            return False
            
        if not self.has_active_plan():
            return False
        
        # If plan has unlimited bills, always allow
        if self.current_plan and self.current_plan.is_unlimited:
            return True
        
        # Otherwise check billing_requests_remaining
        return self.billing_requests_remaining > 0
    
    def activate_plan(self, plan):
        """Assign a plan to user (does NOT activate account - requires admin activation)"""
        self.current_plan = plan
        # Set future expiry date but account won't be usable until admin activates
        self.plan_expiry_date = timezone.now() + timedelta(days=plan.duration_days)
        self.billing_requests_remaining = plan.billing_requests
        # Note: is_account_activated remains False until admin approves
        self.save()
        return True
    
    def activate_account(self):
        """Activate user account (called by admin after payment verification)"""
        self.is_account_activated = True
        # Reset expiry date from activation time
        if self.current_plan:
            self.plan_expiry_date = timezone.now() + timedelta(days=self.current_plan.duration_days)
        self.save()
        return True
    
    def deactivate_account(self):
        """Deactivate user account"""
        self.is_account_activated = False
        self.save()
        return True
    
    @property
    def plan_key(self):
        """Return plan_key for backward compatibility"""
        return self.current_plan.plan_key if self.current_plan else None
    
    def decrement_billing_request(self):
        """Decrement billing request count by 1"""
        if self.billing_requests_remaining > 0:
            self.billing_requests_remaining -= 1
            self.save(update_fields=['billing_requests_remaining'])
            return True
        return False
    
    @property
    def is_plan_active(self):
        "Check if the user's plan is still active"
        if not self.is_account_activated:
            return False
        if self.plan_expiry_date is None:
            return False
        return timezone.now() < self.plan_expiry_date
    
    @property
    def can_make_billing_request(self):
        "Check if user can make a billing request"
        if not self.is_account_activated:
            return False
        return self.is_plan_active and self.billing_requests_remaining > 0
