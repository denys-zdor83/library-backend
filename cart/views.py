from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from books.models import Book
from bookings.models import Booking
from .models import Cart, CartItem
from .serializers import CartSerializer


def _get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = _get_or_create_cart(request.user)
        return Response(CartSerializer(cart, context={'request': request}).data)


class CartAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        book_id = request.data.get('book_id')
        if not book_id:
            return Response({'error': 'book_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            book = Book.objects.get(pk=book_id)
        except Book.DoesNotExist:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

        cart = _get_or_create_cart(request.user)
        _, created = CartItem.objects.get_or_create(cart=cart, book=book)
        if not created:
            return Response({'error': 'Book already in cart'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CartSerializer(cart, context={'request': request}).data, status=status.HTTP_201_CREATED)


class CartRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, book_id):
        cart = _get_or_create_cart(request.user)
        deleted, _ = CartItem.objects.filter(cart=cart, book_id=book_id).delete()
        if not deleted:
            return Response({'error': 'Item not found in cart'}, status=status.HTTP_404_NOT_FOUND)
        return Response(CartSerializer(cart, context={'request': request}).data)


class CartBookAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = _get_or_create_cart(request.user)
        items = cart.items.select_related('book').all()

        if not items.exists():
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        booked = []
        errors = []

        for item in items:
            book = item.book

            if book.available_copies < 1:
                errors.append({'book': book.title, 'error': 'Not available'})
                continue

            active = Booking.objects.filter(
                user=request.user, book=book,
                status__in=[Booking.Status.REQUESTED, Booking.Status.APPROVED],
            ).exists()
            if active:
                errors.append({'book': book.title, 'error': 'Already booked'})
                continue

            Booking.objects.create(user=request.user, book=book)
            booked.append(book.title)

        cart.items.filter(book__title__in=booked).delete()

        return Response({'booked': booked, 'errors': errors})
