from rest_framework import serializers
from .models import Cart, CartItem
from books.serializers import BookListSerializer


class CartItemSerializer(serializers.ModelSerializer):
    book_detail = BookListSerializer(source='book', read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'book', 'book_detail', 'added_at']
        read_only_fields = ['id', 'added_at']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'item_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
