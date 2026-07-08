from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import CustomUser, LibrarianProfile, FavoriteGenre, Role
from .serializers import (
    RegisterSerializer, UserProfileSerializer, ChangePasswordSerializer,
    LibrarianSerializer, RegisterLibrarianSerializer,
)
from .permissions import IsAdmin


def set_auth_cookies(response, refresh):
    access = str(refresh.access_token)
    cookie_kwargs = {
        'httponly': settings.JWT_AUTH_COOKIE_HTTP_ONLY,
        'secure': settings.JWT_AUTH_COOKIE_SECURE,
        'samesite': settings.JWT_AUTH_COOKIE_SAMESITE,
    }
    response.set_cookie(
        settings.JWT_AUTH_COOKIE, access,
        max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        **cookie_kwargs,
    )
    response.set_cookie(
        settings.JWT_AUTH_REFRESH_COOKIE, str(refresh),
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        **cookie_kwargs,
    )
    return response


def clear_auth_cookies(response):
    response.delete_cookie(settings.JWT_AUTH_COOKIE)
    response.delete_cookie(settings.JWT_AUTH_REFRESH_COOKIE)
    return response


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        response = Response(
            UserProfileSerializer(user, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )
        return set_auth_cookies(response, refresh)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.check_password(password):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({'error': 'Account is disabled'}, status=status.HTTP_403_FORBIDDEN)
        refresh = RefreshToken.for_user(user)
        response = Response(
            UserProfileSerializer(user, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )
        return set_auth_cookies(response, refresh)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass
        response = Response({'message': 'Logged out successfully'})
        return clear_auth_cookies(response)


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        if not refresh_token:
            return Response({'error': 'No refresh token'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            refresh = RefreshToken(refresh_token)
            response = Response({'message': 'Token refreshed'})
            return set_auth_cookies(response, refresh)
        except TokenError:
            response = Response({'error': 'Session expired'}, status=status.HTTP_401_UNAUTHORIZED)
            return clear_auth_cookies(response)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserProfileSerializer(request.user, context={'request': request}).data)

    def patch(self, request):
        serializer = UserProfileSerializer(
            request.user, data=request.data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        genres = request.data.get('favorite_genres')
        if genres is not None:
            FavoriteGenre.objects.filter(user=request.user).delete()
            for genre in genres:
                FavoriteGenre.objects.create(user=request.user, genre=genre)
        return Response(UserProfileSerializer(request.user, context={'request': request}).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        refresh = RefreshToken.for_user(request.user)
        response = Response({'message': 'Password changed successfully'})
        return set_auth_cookies(response, refresh)


class LibrarianListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        librarians = CustomUser.objects.filter(role=Role.LIBRARIAN)
        return Response(LibrarianSerializer(librarians, many=True, context={'request': request}).data)

    def post(self, request):
        serializer = RegisterLibrarianSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            LibrarianSerializer(user, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class LibrarianDetailView(APIView):
    permission_classes = [IsAdmin]

    def _get_librarian(self, pk):
        try:
            return CustomUser.objects.get(pk=pk, role=Role.LIBRARIAN)
        except CustomUser.DoesNotExist:
            return None

    def delete(self, request, pk):
        user = self._get_librarian(pk)
        if not user:
            return Response({'error': 'Librarian not found'}, status=status.HTTP_404_NOT_FOUND)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, pk):
        user = self._get_librarian(pk)
        if not user:
            return Response({'error': 'Librarian not found'}, status=status.HTTP_404_NOT_FOUND)
        permissions = request.data.get('permissions')
        if permissions is not None:
            profile, _ = LibrarianProfile.objects.get_or_create(user=user)
            profile.permissions = permissions
            profile.save()
        return Response(LibrarianSerializer(user, context={'request': request}).data)
