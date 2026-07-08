from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin, IsAdminOrLibrarian
from .models import Event
from .serializers import EventSerializer


class EventListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 9))
        queryset = Event.objects.all()
        total = queryset.count()
        start = (page - 1) * page_size
        events = queryset[start: start + page_size]
        return Response({
            'results': EventSerializer(events, many=True, context={'request': request}).data,
            'count': total,
            'page': page,
            'total_pages': (total + page_size - 1) // page_size,
        })

    def post(self, request):
        if not request.user.is_authenticated or request.user.role not in ('admin', 'librarian'):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        serializer = EventSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        return Response(EventSerializer(event, context={'request': request}).data, status=status.HTTP_201_CREATED)


class EventDetailView(APIView):
    permission_classes = [AllowAny]

    def _get_event(self, pk):
        try:
            return Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return None

    def get(self, request, pk):
        event = self._get_event(pk)
        if not event:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(EventSerializer(event, context={'request': request}).data)

    def patch(self, request, pk):
        if not request.user.is_authenticated or request.user.role not in ('admin', 'librarian'):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        event = self._get_event(pk)
        if not event:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = EventSerializer(event, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response(EventSerializer(serializer.save(), context={'request': request}).data)

    def delete(self, request, pk):
        if not request.user.is_authenticated or request.user.role not in ('admin', 'librarian'):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        event = self._get_event(pk)
        if not event:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UpcomingEventsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone
        events = Event.objects.filter(date__gte=timezone.now()).order_by('date')[:5]
        return Response(EventSerializer(events, many=True, context={'request': request}).data)
