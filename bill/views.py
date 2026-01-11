from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from bill.models import Bill, Product
from bill.serializers import BillSerializer, BillListSerializer, ProductSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_products(request):
    """
    GET: List all products for the authenticated user
    """
    products = Product.objects.filter(user=request.user, is_active=True)
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_product(request):
    """
    POST: Create a new product
    """
    serializer = ProductSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_product_detail(request, product_id):
    """
    GET: Get product details
    """
    product = get_object_or_404(Product, id=product_id, user=request.user)
    serializer = ProductSerializer(product)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_product(request, product_id):
    """
    PUT: Update product (full update)
    """
    product = get_object_or_404(Product, id=product_id, user=request.user)
    serializer = ProductSerializer(product, data=request.data, partial=False, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Product updated successfully',
            'product': serializer.data
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def patch_product(request, product_id):
    """
    PATCH: Partial update product
    """
    product = get_object_or_404(Product, id=product_id, user=request.user)
    serializer = ProductSerializer(product, data=request.data, partial=True, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Product updated successfully',
            'product': serializer.data
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product(request, product_id):
    """
    DELETE: Soft delete product (mark as inactive)
    """
    product = get_object_or_404(Product, id=product_id, user=request.user)
    product.is_active = False
    product.save()
    return Response({'message': 'Product deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


# --- Bill Management Views ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bills(request):
    """
    GET: List all bills for the authenticated user
    Query parameters:
    - status: Filter by status ('pending' or 'completed')
    """
    bills = Bill.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.query_params.get('status', None)
    if status_filter:
        bills = bills.filter(status=status_filter)
    
    serializer = BillListSerializer(bills, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_bill(request):
    """
    POST: Create a new bill
    Accepts status field: 'pending' or 'completed' (defaults to 'completed')
    Reduces product stock quantities
    """
    user = request.user
    
    # Check if user has an active plan
    if not user.has_active_plan():
        return Response({
            'error': 'Your billing plan has expired. Please renew to create bills.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # For trial plan, check billing requests remaining
    if user.plan_key == 'trial':
        if user.billing_requests_remaining <= 0:
            return Response({
                'error': 'You have no billing requests remaining. Please upgrade your plan.'
            }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = BillSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        bill = serializer.save()
        
        # Reduce stock quantities for products in the bill
        items = request.data.get('items', [])
        for item in items:
            product_name = item.get('name')
            quantity = item.get('quantity', 0)
            is_custom = item.get('isCustom', False)
            
            # Only reduce stock for catalog products (not custom items)
            if product_name and quantity > 0 and not is_custom:
                try:
                    product = Product.objects.get(name=product_name, user=user, is_active=True)
                    # Always update stock (defaults to 0 if None)
                    current_stock = product.stock_quantity if product.stock_quantity is not None else 0
                    # Reduce stock, normalize to 0 if negative
                    product.stock_quantity = max(0, current_stock - quantity)
                    product.save()
                except Product.DoesNotExist:
                    pass  # Product not found, skip stock update
        
        # Decrement billing request count for trial plan
        if user.plan_key == 'trial':
            user.decrement_billing_request()
        
        response_data = {
            'message': 'Bill created successfully', 
            'bill': serializer.data
        }
        
        # Include remaining requests for trial plan
        if user.plan_key == 'trial':
            response_data['remaining_requests'] = user.billing_requests_remaining
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bill_detail(request, bill_id):
    """
    GET: Get bill details
    """
    bill = get_object_or_404(Bill, id=bill_id, user=request.user)
    serializer = BillSerializer(bill)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_bill(request, bill_id):
    """
    PUT: Update bill
    """
    user = request.user
    bill = get_object_or_404(Bill, id=bill_id, user=user)
    
    serializer = BillSerializer(bill, data=request.data, partial=False, context={'request': request})
    if serializer.is_valid():
        updated_bill = serializer.save()
        
        return Response({
            'message': 'Bill updated successfully', 
            'bill': serializer.data
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_bill(request, bill_id):
    """
    DELETE: Delete bill
    """
    bill = get_object_or_404(Bill, id=bill_id, user=request.user)
    bill.delete()
    return Response({
        'message': 'Bill deleted successfully'
    }, status=status.HTTP_200_OK)
