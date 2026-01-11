from django.urls import path
from bill.views import (
    get_products,
    create_product,
    get_product_detail,
    update_product,
    patch_product,
    delete_product,
    get_bills,
    create_bill,
    get_bill_detail,
    update_bill,
    delete_bill,
)

urlpatterns = [
    # ============ Product Catalog Management ============
    path('products/list/', get_products, name='get-products'),  # GET
    path('products/create/', create_product, name='create-product'),  # POST
    path('products/<int:product_id>/', get_product_detail, name='get-product-detail'),  # GET
    path('products/<int:product_id>/update/', update_product, name='update-product'),  # PUT
    path('products/<int:product_id>/patch/', patch_product, name='patch-product'),  # PATCH
    path('products/<int:product_id>/delete/', delete_product, name='delete-product'),  # DELETE
    
    # ============ Bill Management ============
    path('list/', get_bills, name='get-bills'),  # GET
    path('create/', create_bill, name='create-bill'),  # POST
    path('<int:bill_id>/', get_bill_detail, name='get-bill-detail'),  # GET
    path('<int:bill_id>/update/', update_bill, name='update-bill'),  # PUT
    path('<int:bill_id>/delete/', delete_bill, name='delete-bill'),  # DELETE
]
