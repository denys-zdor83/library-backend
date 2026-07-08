from django.urls import path
from .views import CartView, CartAddView, CartRemoveView, CartBookAllView

urlpatterns = [
    path('', CartView.as_view(), name='cart'),
    path('add/', CartAddView.as_view(), name='cart-add'),
    path('remove/<int:book_id>/', CartRemoveView.as_view(), name='cart-remove'),
    path('book-all/', CartBookAllView.as_view(), name='cart-book-all'),
]
