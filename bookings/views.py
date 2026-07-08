from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import CustomUser, Role
from accounts.permissions import IsAdminOrLibrarian
from books.models import Book
from .models import Booking
from .serializers import BookingSerializer, CreateBookingSerializer


class UserBookingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = Booking.objects.filter(user=request.user).select_related('book', 'book__genre')
        return Response(BookingSerializer(bookings, many=True, context={'request': request}).data)

    def post(self, request):
        serializer = CreateBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = serializer.validated_data['book']

        if book.available_copies < 1:
            return Response({'error': 'Book is not available'}, status=status.HTTP_400_BAD_REQUEST)

        active = Booking.objects.filter(
            user=request.user, book=book,
            status__in=[Booking.Status.REQUESTED, Booking.Status.APPROVED],
        ).exists()
        if active:
            return Response({'error': 'You already have an active booking for this book'}, status=status.HTTP_400_BAD_REQUEST)

        booking = Booking.objects.create(user=request.user, book=book)
        return Response(BookingSerializer(booking, context={'request': request}).data, status=status.HTTP_201_CREATED)


class UserBookingCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, user=request.user)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        if booking.status != Booking.Status.REQUESTED:
            return Response({'error': 'Only requested bookings can be cancelled'}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = Booking.Status.CANCELLED
        booking.save()
        return Response(BookingSerializer(booking, context={'request': request}).data)


class AllBookingsView(APIView):
    permission_classes = [IsAdminOrLibrarian]

    def get(self, request):
        user_id = request.query_params.get('user_id')
        queryset = Booking.objects.select_related('book', 'book__genre', 'user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return Response(BookingSerializer(queryset, many=True, context={'request': request}).data)


class BookingUsersView(APIView):
    permission_classes = [IsAdminOrLibrarian]

    def get(self, request):
        user_ids = Booking.objects.filter(
            status__in=[Booking.Status.REQUESTED, Booking.Status.APPROVED]
        ).values_list('user_id', flat=True).distinct()
        users = CustomUser.objects.filter(id__in=user_ids)
        from accounts.serializers import UserProfileSerializer
        return Response(UserProfileSerializer(users, many=True, context={'request': request}).data)


class BookingApproveView(APIView):
    permission_classes = [IsAdminOrLibrarian]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        if booking.status != Booking.Status.REQUESTED:
            return Response({'error': 'Only requested bookings can be approved'}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = Booking.Status.APPROVED
        booking.approved_at = timezone.now()
        booking.save()

        book = booking.book
        book.available_copies = max(0, book.available_copies - 1)
        book.borrow_count += 1
        if book.available_copies == 0:
            book.status = Book.Status.BORROWED
        else:
            book.status = Book.Status.RESERVED
        book.save()

        return Response(BookingSerializer(booking, context={'request': request}).data)


class BookingRejectView(APIView):
    permission_classes = [IsAdminOrLibrarian]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        if booking.status not in (Booking.Status.REQUESTED, Booking.Status.APPROVED):
            return Response({'error': 'Cannot reject this booking'}, status=status.HTTP_400_BAD_REQUEST)

        if booking.status == Booking.Status.APPROVED:
            book = booking.book
            book.available_copies = min(book.total_copies, book.available_copies + 1)
            if book.available_copies > 0:
                book.status = Book.Status.AVAILABLE
            book.save()

        booking.status = Booking.Status.REJECTED
        booking.rejected_at = timezone.now()
        booking.save()
        return Response(BookingSerializer(booking, context={'request': request}).data)
