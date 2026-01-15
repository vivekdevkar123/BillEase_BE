from rest_framework import serializers
from account.models import User, Plan
from django.utils.encoding import smart_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import PasswordResetTokenGenerator


class PlanSerializer(serializers.ModelSerializer):
    """Serializer for Plan model"""
    class Meta:
        model = Plan
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    
class UserRegistrationSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)
    plan_key = serializers.CharField(required=False, write_only=True, help_text='Selected plan key (defaults to trial)')

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'mobile_number', 'password', 'password2', 'plan_key', 'referred_by']
        extra_kwargs = {
            'password': {'write_only': True},
            'referred_by': {'required': False}
        }

    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.get('password2')
        plan_key = attrs.get('plan_key', 'trial')  # Default to trial
        
        if password != password2:
            raise serializers.ValidationError("Password and Confirm Password don't match")
        
        # Validate plan exists and is active
        try:
            plan = Plan.objects.get(plan_key=plan_key, is_active=True)
        except Plan.DoesNotExist:
            raise serializers.ValidationError(f"Invalid plan selected: {plan_key}")
        
        attrs['plan'] = plan
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        plan = validated_data.pop('plan')
        if 'plan_key' in validated_data:
            validated_data.pop('plan_key')
        
        # Create user
        user = User.objects.create_user(**validated_data)
        
        # Activate the selected plan
        user.activate_plan(plan)
        
        return user

class SendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    class Meta:
        model = User
        fields = ['email']

    def validate(self, attrs):
        email = attrs.get('email')
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return attrs

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        return data
    
class UserLoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255)
    class Meta:
        model = User
        fields = ['email', 'password']

class UserProfileSerializer(serializers.ModelSerializer):
    is_plan_active = serializers.ReadOnlyField()
    can_make_billing_request = serializers.ReadOnlyField()
    plan_key = serializers.ReadOnlyField()
    current_plan = PlanSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'mobile_number',
            'business_name', 'business_address', 'referred_by',
            'gstin_number', 'gst_percentage',
            'current_plan', 'plan_key', 'plan_expiry_date', 'billing_requests_remaining',
            'is_account_activated', 'is_plan_active', 'can_make_billing_request',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'current_plan', 'plan_key', 'plan_expiry_date', 'billing_requests_remaining', 
                            'is_account_activated', 'is_plan_active', 'can_make_billing_request', 'created_at', 'updated_at']


class UserChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=255, style={'input_type':'password'}, write_only=True)
    password2 = serializers.CharField(max_length=255, style={'input_type':'password'}, write_only=True)
    class Meta:
        fields = ['password', 'password2']

    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.get('password2')
        user = self.context.get('user')

        if password != password2:
            raise serializers.ValidationError("Password and Confirm Password doesn't match")
        
        user.set_password(password)
        user.save()
        return attrs

class SendPasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    class Meta:
        fields = ['email']


class UserPasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=255, style={'input_type':'password'}, write_only=True)
    password2 = serializers.CharField(max_length=255, style={'input_type':'password'}, write_only=True)
    class Meta:
        fields = ['password', 'password2']

    def validate(self, attrs):
        try:
            password = attrs.get('password')
            password2 = attrs.get('password2')
            uid = self.context.get('uid')
            token = self.context.get('token')
            if password != password2:
                raise serializers.ValidationError("Password and Confirm Password doesn't match")
            id = smart_str(urlsafe_base64_decode(uid))
            user = User.objects.get(id=id)
            if not PasswordResetTokenGenerator().check_token(user, token):
                raise serializers.ValidationError('Token is not Valid or Expired')
            user.set_password(password)
            user.save()
            return attrs
        except DjangoUnicodeDecodeError as identifier:
            PasswordResetTokenGenerator().check_token(user, token)
            raise serializers.ValidationError('Token is not Valid or Expired')
