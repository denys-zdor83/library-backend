from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Avg
from django.db.models.functions import Coalesce
from django.db.models import FloatField, Value

from accounts.permissions import IsAdmin, IsAdminOrLibrarian
from .models import Book, Genre, BookRating
from .serializers import BookListSerializer, BookDetailSerializer, BookWriteSerializer, GenreSerializer


class GenreListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        genres = Genre.objects.all()
        return Response(GenreSerializer(genres, many=True).data)


class BookListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = Book.objects.select_related('genre').prefetch_related('ratings')

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(author__icontains=search)
            )

        genre = request.query_params.get('genre')
        if genre:
            queryset = queryset.filter(genre_id=genre)

        author = request.query_params.get('author')
        if author:
            queryset = queryset.filter(author__icontains=author)

        year_from = request.query_params.get('year_from')
        if year_from:
            queryset = queryset.filter(year__gte=year_from)

        year_to = request.query_params.get('year_to')
        if year_to:
            queryset = queryset.filter(year__lte=year_to)

        book_status = request.query_params.get('status')
        if book_status:
            queryset = queryset.filter(status=book_status)

        sort = request.query_params.get('sort', '-created_at')

        if sort in ('popular', 'least_popular'):
            # Annotate with avg rating; books with no ratings get 0
            queryset = queryset.annotate(
                avg_rating=Coalesce(Avg('ratings__value'), Value(0.0, output_field=FloatField()))
            )
            order = '-avg_rating' if sort == 'popular' else 'avg_rating'
            queryset = queryset.order_by(order, '-created_at')
        else:
            sort_map = {
                'newest': '-created_at',
                'oldest': 'created_at',
            }
            queryset = queryset.order_by(sort_map.get(sort, '-created_at'))

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 12))
        total = queryset.count()
        start = (page - 1) * page_size
        books = queryset[start: start + page_size]

        return Response({
            'results': BookListSerializer(books, many=True, context={'request': request}).data,
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
        })

    def post(self, request):
        self.check_permissions(request)
        if request.user.role not in ('admin', 'librarian'):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        serializer = BookWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = serializer.save()
        return Response(BookDetailSerializer(book, context={'request': request}).data, status=status.HTTP_201_CREATED)


class BookDetailView(APIView):
    permission_classes = [AllowAny]

    def _get_book(self, pk):
        try:
            return Book.objects.select_related('genre').prefetch_related('ratings').get(pk=pk)
        except Book.DoesNotExist:
            return None

    def get(self, request, pk):
        book = self._get_book(pk)
        if not book:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(BookDetailSerializer(book, context={'request': request}).data)

    def patch(self, request, pk):
        if not request.user.is_authenticated or request.user.role not in ('admin', 'librarian'):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        book = self._get_book(pk)
        if not book:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = BookWriteSerializer(book, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        book = serializer.save()
        return Response(BookDetailSerializer(book, context={'request': request}).data)

    def delete(self, request, pk):
        if not request.user.is_authenticated or request.user.role not in ('admin', 'librarian'):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        book = self._get_book(pk)
        if not book:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
        book.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BookRatingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

        value = request.data.get('value')
        if not value or not (1 <= int(value) <= 5):
            return Response({'error': 'Rating must be between 1 and 5'}, status=status.HTTP_400_BAD_REQUEST)

        rating, created = BookRating.objects.update_or_create(
            book=book, user=request.user,
            defaults={'value': int(value)},
        )
        return Response({'rating': rating.value, 'average': book.average_rating})


class NewestBooksView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        books = Book.objects.order_by('-created_at')[:8]
        return Response(BookListSerializer(books, many=True, context={'request': request}).data)


class PopularBooksView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        books = Book.objects.order_by('-borrow_count')[:8]
        return Response(BookListSerializer(books, many=True, context={'request': request}).data)
