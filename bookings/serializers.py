from rest_framework import serializers
from .models import Booking
from books.serializers import BookListSerializer
from accounts.serializers import UserProfileSerializer


class BookingSerializer(serializers.ModelSerializer):
    book_detail = BookListSerializer(source='book', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'book', 'book_detail', 'user', 'user_email', 'user_name',
            'status', 'requested_at', 'approved_at', 'rejected_at', 'due_date', 'notes',
        ]
        read_only_fields = ['id', 'user', 'status', 'requested_at', 'approved_at', 'rejected_at']


class CreateBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['book']
