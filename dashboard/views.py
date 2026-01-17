import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncMonth, TruncDate
from datetime import datetime, timedelta
from decimal import Decimal

from bill.models import Bill, Product

# Get logger for this module
logger = logging.getLogger('dashboard')


def check_dashboard_permission(user):
    """Check if user has access to insights dashboard"""
    if not user.current_plan:
        return False
    return user.current_plan.has_insights_dashboard


def check_reports_permission(user):
    """Check if user has access to sales reports"""
    if not user.current_plan:
        return False
    return user.current_plan.has_sales_reports


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_overview(request):
    """
    Get dashboard overview with key metrics
    """
    user = request.user
    
    # Check permission
    if not check_dashboard_permission(user):
        logger.warning(f"User {user.email} attempted to access dashboard without permission")
        return Response({
            'error': 'Dashboard access not available in your current plan',
            'upgrade_required': True
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        logger.info(f"Dashboard overview accessed by user {user.email}")
        
        # Get date ranges
        today = datetime.now().date()
        thirty_days_ago = today - timedelta(days=30)
        seven_days_ago = today - timedelta(days=7)
        
        # Total revenue (all time)
        total_revenue = Bill.objects.filter(
            user=user,
            status='completed'
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        # Total bills count
        total_bills = Bill.objects.filter(user=user).count()
        
        # This month's revenue
        month_start = today.replace(day=1)
        month_revenue = Bill.objects.filter(
            user=user,
            status='completed',
            created_at__gte=month_start
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        # This month's bills count
        month_bills = Bill.objects.filter(
            user=user,
            created_at__gte=month_start
        ).count()
        
        # Last 7 days revenue
        week_revenue = Bill.objects.filter(
            user=user,
            status='completed',
            created_at__gte=seven_days_ago
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        # Average bill value
        avg_bill_value = Bill.objects.filter(
            user=user,
            status='completed'
        ).aggregate(avg=Avg('total'))['avg'] or Decimal('0')
        
        # Total products
        total_products = Product.objects.filter(user=user, is_active=True).count()
        
        # Low stock products (stock < 10) - only for products with inventory management enabled
        low_stock_count = Product.objects.filter(
            user=user,
            is_active=True,
            manage_inventory=True,
            stock_quantity__lt=10,
            stock_quantity__gt=0
        ).count()
        
        # Out of stock products - only for products with inventory management enabled
        out_of_stock_count = Product.objects.filter(
            user=user,
            is_active=True,
            manage_inventory=True,
            stock_quantity__lte=0
        ).count()
        
        # Top selling product (by quantity in last 30 days)
        recent_bills = Bill.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago
        ).values_list('items', flat=True)
        
        product_sales = {}
        for bill_items in recent_bills:
            if not bill_items:
                continue
            for item in bill_items:
                if item.get('isCustom', False):
                    continue
                product_name = item.get('name', '')
                quantity = float(item.get('quantity', 0))
                if product_name:
                    product_sales[product_name] = product_sales.get(product_name, 0) + quantity
        
        top_product = None
        if product_sales:
            top_product = max(product_sales.items(), key=lambda x: x[1])
            top_product = {
                'name': top_product[0],
                'quantity_sold': top_product[1]
            }
    
        return Response({
            'total_revenue': float(total_revenue),
            'total_bills': total_bills,
            'month_revenue': float(month_revenue),
            'month_bills': month_bills,
            'week_revenue': float(week_revenue),
            'avg_bill_value': float(avg_bill_value),
            'total_products': total_products,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'top_product': top_product,
        })
    except Exception as e:
        logger.error(f"Error fetching dashboard overview for user {user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch dashboard data'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_sales(request):
    """
    Get monthly sales data for the last 12 months
    """
    user = request.user
    
    # Check permission
    if not check_dashboard_permission(user):
        logger.warning(f"User {user.email} attempted to access monthly sales without permission")
        return Response({
            'error': 'Dashboard access not available in your current plan',
            'upgrade_required': True
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        logger.info(f"Monthly sales accessed by user {user.email}")
        
        # Get last 12 months
        today = datetime.now()
        twelve_months_ago = today - timedelta(days=365)
        
        # Group bills by month
        monthly_data = Bill.objects.filter(
            user=user,
            status='completed',
            created_at__gte=twelve_months_ago
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total_sales=Sum('total'),
            bills_count=Count('id')
        ).order_by('month')
        
        # Format response
        sales_data = []
        for data in monthly_data:
            sales_data.append({
                'month': data['month'].strftime('%b %Y'),
                'sales': float(data['total_sales']),
                'bills': data['bills_count']
            })
        
        return Response({
            'monthly_sales': sales_data
        })
    except Exception as e:
        logger.error(f"Error fetching monthly sales for user {user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch monthly sales'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_sales(request):
    """
    Get daily sales data for the last 30 days
    """
    user = request.user
    
    # Check permission
    if not check_dashboard_permission(user):
        logger.warning(f"User {user.email} attempted to access daily sales without permission")
        return Response({
            'error': 'Dashboard access not available in your current plan',
            'upgrade_required': True
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        logger.info(f"Daily sales accessed by user {user.email}")
        
        # Get last 30 days
        today = datetime.now().date()
        thirty_days_ago = today - timedelta(days=30)
        
        # Group bills by date
        daily_data = Bill.objects.filter(
            user=user,
            status='completed',
            created_at__date__gte=thirty_days_ago
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total_sales=Sum('total'),
            bills_count=Count('id')
        ).order_by('date')
        
        # Format response
        sales_data = []
        for data in daily_data:
            sales_data.append({
                'date': data['date'].strftime('%d %b'),
                'sales': float(data['total_sales']),
                'bills': data['bills_count']
            })
        
        return Response({
            'daily_sales': sales_data
        })
    except Exception as e:
        logger.error(f"Error fetching daily sales for user {user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch daily sales'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_insights(request):
    """
    Get product insights including low stock, out of stock, and top sellers
    """
    user = request.user
    
    # Check permission
    if not check_dashboard_permission(user):
        logger.warning(f"User {user.email} attempted to access product insights without permission")
        return Response({
            'error': 'Dashboard access not available in your current plan',
            'upgrade_required': True
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        logger.info(f"Product insights accessed by user {user.email}")
        
        # Low stock products (stock < 10) - only for products with inventory management enabled
        low_stock_products = Product.objects.filter(
            user=user,
            is_active=True,
            manage_inventory=True,
            stock_quantity__lt=10,
            stock_quantity__gt=0
        ).values('id', 'name', 'stock_quantity', 'price').order_by('stock_quantity')[:10]
        
        # Out of stock products - only for products with inventory management enabled
        out_of_stock_products = Product.objects.filter(
            user=user,
            is_active=True,
            manage_inventory=True,
            stock_quantity__lte=0
        ).values('id', 'name', 'price')[:10]
        
        # Get top selling products (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_bills = Bill.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago
        ).values_list('items', flat=True)
        
        product_sales = {}
        product_revenue = {}
        
        for bill_items in recent_bills:
            if not bill_items:
                continue
            for item in bill_items:
                if item.get('isCustom', False):
                    continue
                product_name = item.get('name', '')
                quantity = float(item.get('quantity', 0))
                price = float(item.get('price', 0))
                
                if product_name:
                    product_sales[product_name] = product_sales.get(product_name, 0) + quantity
                    product_revenue[product_name] = product_revenue.get(product_name, 0) + (quantity * price)
        
        # Sort by quantity sold
        top_sellers = sorted(
            [{'name': name, 'quantity_sold': qty, 'revenue': product_revenue.get(name, 0)} 
             for name, qty in product_sales.items()],
            key=lambda x: x['quantity_sold'],
            reverse=True
        )[:10]
        
        return Response({
            'low_stock_products': list(low_stock_products),
            'out_of_stock_products': list(out_of_stock_products),
            'top_selling_products': top_sellers
        })
    except Exception as e:
        logger.error(f"Error fetching product insights for user {user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch product insights'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def revenue_breakdown(request):
    """
    Get revenue breakdown by time periods
    """
    user = request.user
    
    # Check permission
    if not check_dashboard_permission(user):
        logger.warning(f"User {user.email} attempted to access revenue breakdown without permission")
        return Response({
            'error': 'Dashboard access not available in your current plan',
            'upgrade_required': True
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        logger.info(f"Revenue breakdown accessed by user {user.email}")
        
        today = datetime.now().date()
        
        # Today's revenue
        today_revenue = Bill.objects.filter(
            user=user,
            status='completed',
            created_at__date=today
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        # Yesterday's revenue
        yesterday = today - timedelta(days=1)
        yesterday_revenue = Bill.objects.filter(
            user=user,
            status='completed',
            created_at__date=yesterday
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        # This week's revenue (last 7 days)
        week_start = today - timedelta(days=7)
        week_revenue = Bill.objects.filter(
            user=user,
            status='completed',
            created_at__date__gte=week_start
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        # This month's revenue
        month_start = today.replace(day=1)
        month_revenue = Bill.objects.filter(
            user=user,
            status='completed',
            created_at__date__gte=month_start
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        # Last month's revenue
        last_month_end = month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        last_month_revenue = Bill.objects.filter(
            user=user,
            status='completed',
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        # Calculate growth percentages
        month_growth = 0
        if last_month_revenue > 0:
            month_growth = ((month_revenue - last_month_revenue) / last_month_revenue) * 100
        
        return Response({
            'today': float(today_revenue),
            'yesterday': float(yesterday_revenue),
            'this_week': float(week_revenue),
            'this_month': float(month_revenue),
            'last_month': float(last_month_revenue),
            'month_growth_percentage': float(month_growth)
        })
    except Exception as e:
        logger.error(f"Error fetching revenue breakdown for user {user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch revenue breakdown'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_report(request):
    """
    Get detailed sales report with filtering
    Query params: start_date, end_date
    """
    user = request.user
    
    # Check permission
    if not check_reports_permission(user):
        logger.warning(f"User {user.email} attempted to access sales report without permission")
        return Response({
            'error': 'Sales reports not available in your current plan',
            'upgrade_required': True
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        logger.info(f"Sales report accessed by user {user.email}")
        
        # Get date range from query params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Default to last 30 days if not provided
        if not start_date or not end_date:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get bills in date range
        bills = Bill.objects.filter(
            user=user,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).order_by('-created_at')
        
        # Calculate totals
        total_bills = bills.count()
        completed_bills = bills.filter(status='completed').count()
        pending_bills = bills.filter(status='pending').count()
        
        total_revenue = bills.filter(status='completed').aggregate(
            total=Sum('total')
        )['total'] or Decimal('0')
        
        total_subtotal = bills.filter(status='completed').aggregate(
            total=Sum('subtotal')
        )['total'] or Decimal('0')
        
        total_cgst = bills.filter(status='completed').aggregate(
            total=Sum('cgst_amount')
        )['total'] or Decimal('0')
        
        total_sgst = bills.filter(status='completed').aggregate(
            total=Sum('sgst_amount')
        )['total'] or Decimal('0')
        
        # Average bill value
        avg_bill_value = bills.filter(status='completed').aggregate(
            avg=Avg('total')
        )['avg'] or Decimal('0')
        
        # Daily breakdown
        daily_data = bills.filter(status='completed').annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            sales=Sum('total'),
            bills_count=Count('id')
        ).order_by('date')
        
        daily_breakdown = [
            {
                'date': data['date'].strftime('%Y-%m-%d'),
                'sales': float(data['sales']),
                'bills': data['bills_count']
            }
            for data in daily_data
        ]
        
        # Top customers by revenue
        customer_revenue = {}
        for bill in bills.filter(status='completed'):
            customer_name = bill.customer_name
            if customer_name:
                customer_revenue[customer_name] = customer_revenue.get(customer_name, 0) + float(bill.total)
        
        top_customers = sorted(
            [{'name': name, 'revenue': revenue} for name, revenue in customer_revenue.items()],
            key=lambda x: x['revenue'],
            reverse=True
        )[:10]
        
        # Product sales analysis
        product_sales = {}
        product_revenue = {}
        
        for bill in bills:
            if not bill.items:
                continue
            for item in bill.items:
                product_name = item.get('name', '')
                quantity = float(item.get('quantity', 0))
                price = float(item.get('price', 0))
                
                if product_name:
                    product_sales[product_name] = product_sales.get(product_name, 0) + quantity
                    product_revenue[product_name] = product_revenue.get(product_name, 0) + (quantity * price)
    
        top_products = sorted(
            [{'name': name, 'quantity': qty, 'revenue': product_revenue.get(name, 0)} 
             for name, qty in product_sales.items()],
            key=lambda x: x['revenue'],
            reverse=True
        )[:10]
        
        return Response({
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            },
            'summary': {
                'total_bills': total_bills,
                'completed_bills': completed_bills,
                'pending_bills': pending_bills,
                'total_revenue': float(total_revenue),
                'total_subtotal': float(total_subtotal),
                'total_cgst': float(total_cgst),
                'total_sgst': float(total_sgst),
                'avg_bill_value': float(avg_bill_value),
            },
            'daily_breakdown': daily_breakdown,
            'top_customers': top_customers,
            'top_products': top_products,
        })
    except Exception as e:
        logger.error(f"Error fetching sales report for user {user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch sales report'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def inventory_report(request):
    """
    Get inventory report with stock analysis
    """
    user = request.user
    
    # Check permission
    if not check_reports_permission(user):
        logger.warning(f"User {user.email} attempted to access inventory report without permission")
        return Response({
            'error': 'Inventory reports not available in your current plan',
            'upgrade_required': True
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        logger.info(f"Inventory report accessed by user {user.email}")
        
        # Get all products with inventory management enabled
        products = Product.objects.filter(user=user, is_active=True, manage_inventory=True)
        
        total_products = products.count()
        out_of_stock = products.filter(stock_quantity__lte=0).count()
        low_stock = products.filter(stock_quantity__gt=0, stock_quantity__lt=10).count()
        in_stock = products.filter(stock_quantity__gte=10).count()
        
        # Total inventory value - only for products with inventory management
        total_value = sum([
            float(product.price) * float(product.stock_quantity or 0)
            for product in products
        ])
        
        # Products needing attention - only for products with inventory management
        critical_products = products.filter(stock_quantity__lte=0).values(
            'id', 'name', 'price', 'stock_quantity'
        )
        
        low_stock_products = products.filter(
            stock_quantity__gt=0, 
            stock_quantity__lt=10
        ).values('id', 'name', 'price', 'stock_quantity')
        
        # All products list - only products with inventory management
        all_products = products.values('id', 'name', 'price', 'stock_quantity').order_by('name')
        
        return Response({
            'summary': {
                'total_products': total_products,
                'in_stock': in_stock,
                'low_stock': low_stock,
                'out_of_stock': out_of_stock,
                'total_inventory_value': total_value,
            },
            'critical_products': list(critical_products),
            'low_stock_products': list(low_stock_products),
            'all_products': list(all_products),
        })
    except Exception as e:
        logger.error(f"Error fetching inventory report for user {user.email}: {str(e)}", exc_info=True)
        return Response({'error': 'Failed to fetch inventory report'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
