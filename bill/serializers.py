from rest_framework import serializers
from bill.models import Bill, Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 
            'stock_quantity', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value
    
    def validate_stock_quantity(self, value):
        # Default to 0 if None or not provided
        if value is None:
            return 0
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative")
        return value
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        # Ensure stock_quantity defaults to 0
        if 'stock_quantity' not in validated_data or validated_data['stock_quantity'] is None:
            validated_data['stock_quantity'] = 0
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Ensure stock_quantity defaults to 0 if not provided
        if 'stock_quantity' not in validated_data or validated_data['stock_quantity'] is None:
            validated_data['stock_quantity'] = 0
        return super().update(instance, validated_data)


class BillSerializer(serializers.ModelSerializer):
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Bill
        fields = [
            'id', 'customer_name', 'customer_phone', 'items', 'items_count',
            'subtotal', 'cgst_amount', 'sgst_amount', 'total', 'status', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'items_count', 'subtotal', 'cgst_amount', 'sgst_amount', 'total', 'created_at', 'updated_at']
    
    def get_items_count(self, obj):
        if isinstance(obj.items, list):
            return len(obj.items)
        return 0
    
    def validate_items(self, value):
        if not value or len(value) == 0:
            raise serializers.ValidationError("At least one item is required")
        
        # Validate each item structure
        for idx, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f"Item {idx + 1} must be an object")
            
            # Check required fields
            required_fields = ['name', 'price', 'quantity']
            for field in required_fields:
                if field not in item:
                    raise serializers.ValidationError(f"Item {idx + 1} is missing required field: {field}")
            
            # Validate data types
            try:
                price = float(item['price'])
                if price < 0:
                    raise serializers.ValidationError(f"Item {idx + 1} price must be non-negative")
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"Item {idx + 1} has invalid price")
            
            try:
                quantity = float(item['quantity'])
                if quantity <= 0:
                    raise serializers.ValidationError(f"Item {idx + 1} quantity must be greater than zero")
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"Item {idx + 1} has invalid quantity")
        
        return value
    
    def create(self, validated_data):
        user = self.context['request'].user
        items_data = validated_data.get('items', [])
        
        # Calculate subtotal from items
        subtotal = sum(float(item.get('price', 0)) * int(item.get('quantity', 0)) for item in items_data)
        validated_data['subtotal'] = subtotal
        
        # Calculate GST amounts (split equally between CGST and SGST)
        gst_percentage = float(user.gst_percentage) if user.gst_percentage else 0
        half_gst = gst_percentage / 2
        cgst_amount = (subtotal * half_gst) / 100
        sgst_amount = (subtotal * half_gst) / 100
        
        validated_data['cgst_amount'] = round(cgst_amount, 2)
        validated_data['sgst_amount'] = round(sgst_amount, 2)
        validated_data['total'] = round(subtotal + cgst_amount + sgst_amount, 2)
        validated_data['user'] = user
        
        # Set default status to 'completed' if not provided
        if 'status' not in validated_data:
            validated_data['status'] = 'completed'
        
        bill = Bill.objects.create(**validated_data)
        return bill
    
    def update(self, instance, validated_data):
        user = instance.user
        
        # Update bill fields
        instance.customer_name = validated_data.get('customer_name', instance.customer_name)
        instance.customer_phone = validated_data.get('customer_phone', instance.customer_phone)
        
        # Update status if provided
        if 'status' in validated_data:
            instance.status = validated_data['status']
        
        # If items are provided, recalculate all amounts
        if 'items' in validated_data:
            items_data = validated_data['items']
            instance.items = items_data
            
            # Recalculate subtotal
            subtotal = sum(float(item.get('price', 0)) * int(item.get('quantity', 0)) for item in items_data)
            instance.subtotal = subtotal
            
            # Recalculate GST amounts
            gst_percentage = float(user.gst_percentage) if user.gst_percentage else 0
            half_gst = gst_percentage / 2
            cgst_amount = (subtotal * half_gst) / 100
            sgst_amount = (subtotal * half_gst) / 100
            
            instance.cgst_amount = round(cgst_amount, 2)
            instance.sgst_amount = round(sgst_amount, 2)
            instance.total = round(subtotal + cgst_amount + sgst_amount, 2)
        
        instance.save()
        return instance


class BillListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Bill
        fields = [
            'id', 'customer_name', 'customer_phone', 
            'subtotal', 'cgst_amount', 'sgst_amount', 'total', 
            'items_count', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'subtotal', 'cgst_amount', 'sgst_amount', 'total', 'items_count', 'created_at', 'updated_at']
    
    def get_items_count(self, obj):
        if isinstance(obj.items, list):
            return len(obj.items)
        return 0
