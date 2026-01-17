import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from decimal import Decimal

from bill.models import Bill, Product
from bill.serializers import BillSerializer, BillListSerializer, ProductSerializer

# Get logger for this module
logger = logging.getLogger('bill')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_products(request):
    """
    GET: List all products for the authenticated user
    """
    try:
        products = Product.objects.filter(user=request.user, is_active=True)
        serializer = ProductSerializer(products, many=True)
        logger.info(f"User {request.user.email} fetched {len(products)} products")
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching products for {request.user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch products'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_product(request):
    """
    POST: Create a new product
    """
    try:
        serializer = ProductSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            product = serializer.save()
            logger.info(f"Product '{product.name}' created by user {request.user.email}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        logger.warning(f"Invalid product data from user {request.user.email}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error creating product for user {request.user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to create product'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_product_detail(request, product_id):
    """
    GET: Get product details
    """
    try:
        product = get_object_or_404(Product, id=product_id, user=request.user)
        serializer = ProductSerializer(product)
        logger.info(f"Product {product_id} details fetched by user {request.user.email}")
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching product {product_id} for user {request.user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch product details'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_product(request, product_id):
    """
    PUT: Update product (full update)
    """
    try:
        product = get_object_or_404(Product, id=product_id, user=request.user)
        serializer = ProductSerializer(product, data=request.data, partial=False, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Product {product_id} updated by user {request.user.email}")
            return Response({
                'message': 'Product updated successfully',
                'product': serializer.data
            })
        logger.warning(f"Invalid product update data from user {request.user.email}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error updating product {product_id} for user {request.user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to update product'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def patch_product(request, product_id):
    """
    PATCH: Partial update product
    """
    try:
        product = get_object_or_404(Product, id=product_id, user=request.user)
        serializer = ProductSerializer(product, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Product {product_id} patched by user {request.user.email}")
            return Response({
                'message': 'Product updated successfully',
                'product': serializer.data
            })
        logger.warning(f"Invalid product patch data from user {request.user.email}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error patching product {product_id} for user {request.user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to update product'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product(request, product_id):
    """
    DELETE: Soft delete product (mark as inactive)
    """
    try:
        product = get_object_or_404(Product, id=product_id, user=request.user)
        product.is_active = False
        product.save()
        logger.info(f"Product {product_id} deleted by user {request.user.email}")
        return Response({'message': 'Product deleted successfully'}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error deleting product {product_id} by user {request.user.email}: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- Bill Management Views ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bills(request):
    """
    GET: List all bills for the authenticated user
    Query parameters:
    - status: Filter by status ('pending' or 'completed')
    """
    try:
        bills = Bill.objects.filter(user=request.user).order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status', None)
        if status_filter:
            bills = bills.filter(status=status_filter)
        
        serializer = BillListSerializer(bills, many=True)
        logger.info(f"User {request.user.email} fetched {len(bills)} bills (filter: {status_filter or 'all'})")
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching bills for user {request.user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch bills'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        logger.warning(f"User {user.email} attempted to create bill with expired plan")
        return Response({
            'error': 'Your billing plan has expired. Please renew to create bills.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # For trial plan, check billing requests remaining
    if user.plan_key == 'trial':
        if user.billing_requests_remaining <= 0:
            logger.warning(f"User {user.email} has no billing requests remaining")
            return Response({
                'error': 'You have no billing requests remaining. Please upgrade your plan.'
            }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = BillSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        try:
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
                        current_stock = product.stock_quantity if product.stock_quantity is not None else Decimal('0')
                        # Reduce stock by exact quantity (supports decimals like 1.5, 2.75, etc.)
                        quantity_decimal = Decimal(str(quantity))
                        new_stock = current_stock - quantity_decimal
                        product.stock_quantity = max(Decimal('0'), new_stock)
                        product.save()
                    except Product.DoesNotExist:
                        logger.warning(f"Product '{product_name}' not found for user {user.email}")
                        pass  # Product not found, skip stock update
                    except Exception as e:
                        logger.error(f"Error updating stock for product '{product_name}': {str(e)}", exc_info=True)
            
            # Decrement billing request count for trial plan
            if user.plan_key == 'trial':
                user.decrement_billing_request()
            
            logger.info(f"Bill {bill.id} created successfully by user {user.email}")
            
            response_data = {
                'message': 'Bill created successfully', 
                'bill': serializer.data
            }
            
            # Include remaining requests for trial plan
            if user.plan_key == 'trial':
                response_data['remaining_requests'] = user.billing_requests_remaining
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating bill for user {user.email}: {str(e)}", exc_info=True)
            return Response({'error': 'Failed to create bill'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    logger.warning(f"Invalid bill data from user {user.email}: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bill_detail(request, bill_id):
    """
    GET: Get bill details
    """
    try:
        bill = get_object_or_404(Bill, id=bill_id, user=request.user)
        serializer = BillSerializer(bill)
        logger.info(f"Bill {bill_id} details fetched by user {request.user.email}")
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching bill {bill_id} for user {request.user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch bill details'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_bill(request, bill_id):
    """
    PUT: Update bill
    """
    try:
        user = request.user
        bill = get_object_or_404(Bill, id=bill_id, user=user)
        
        serializer = BillSerializer(bill, data=request.data, partial=False, context={'request': request})
        if serializer.is_valid():
            updated_bill = serializer.save()
            logger.info(f"Bill {bill_id} updated by user {user.email}")
            return Response({
                'message': 'Bill updated successfully', 
                'bill': serializer.data
            })
        logger.warning(f"Invalid bill update data from user {user.email}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error updating bill {bill_id} for user {request.user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to update bill'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_bill(request, bill_id):
    """
    DELETE: Delete bill
    """
    try:
        bill = get_object_or_404(Bill, id=bill_id, user=request.user)
        bill.delete()
        logger.info(f"Bill {bill_id} deleted by user {request.user.email}")
        return Response({
            'message': 'Bill deleted successfully'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error deleting bill {bill_id} for user {request.user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to delete bill'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
