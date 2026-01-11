from django.contrib import admin
from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def welcome_view(request):
    """
    Welcome endpoint
    GET /
    Returns welcome message
    """
    return Response({
        'message': 'Welcome to Billing Software API',
        'version': '1.0.0'
    }, status=200)


urlpatterns = [
    path('', welcome_view, name='welcome'),
    path('admin/', admin.site.urls),
    path('api/user/', include('account.urls')),
    path('api/bills/', include('bill.urls')),
]