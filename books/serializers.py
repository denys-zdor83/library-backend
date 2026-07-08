from rest_framework import serializers
from .models import Book, Genre, BookRating


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name']


class BookRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookRating
        fields = ['id', 'value', 'created_at']
        read_only_fields = ['id', 'created_at']


class BookListSerializer(serializers.ModelSerializer):
    genre_name = serializers.CharField(source='genre.name', read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'year', 'genre', 'genre_name',
            'cover', 'cover_url', 'status', 'average_rating', 'borrow_count',
        ]

    def get_cover_url(self, obj):
        request = self.context.get('request')
        if obj.cover and request:
            return request.build_absolute_uri(obj.cover.url)
        return None


class BookDetailSerializer(serializers.ModelSerializer):
    genre_name = serializers.CharField(source='genre.name', read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    cover_url = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'description', 'year', 'genre', 'genre_name',
            'cover', 'cover_url', 'status', 'total_copies', 'available_copies',
            'average_rating', 'user_rating', 'borrow_count', 'created_at',
        ]

    def get_cover_url(self, obj):
        request = self.context.get('request')
        if obj.cover and request:
            return request.build_absolute_uri(obj.cover.url)
        return None

    def get_user_rating(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            rating = obj.ratings.filter(user=request.user).first()
            return rating.value if rating else None
        return None


class BookWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = [
            'title', 'author', 'description', 'year', 'genre',
            'cover', 'total_copies', 'available_copies', 'status',
        ]
