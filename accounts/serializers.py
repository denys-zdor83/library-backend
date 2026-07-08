from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, LibrarianProfile, FavoriteGenre, Role


class FavoriteGenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteGenre
        fields = ['id', 'genre']


class UserProfileSerializer(serializers.ModelSerializer):
    favorite_genres = FavoriteGenreSerializer(many=True, read_only=True)
    full_name = serializers.CharField(read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'role', 'avatar', 'avatar_url', 'country', 'city', 'postal_code',
            'bio', 'registered_at', 'favorite_genres',
        ]
        read_only_fields = ['id', 'email', 'role', 'registered_at']

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar and request:
            return request.build_absolute_uri(obj.avatar.url)
        return None


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'username', 'first_name', 'last_name', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        return CustomUser.objects.create_user(
            role=Role.USER,
            **validated_data,
        )


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError({'new_password': 'Passwords do not match.'})
        return data

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value


class LibrarianSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'avatar', 'avatar_url', 'role', 'registered_at', 'permissions']

    def get_permissions(self, obj):
        try:
            return obj.librarian_profile.permissions
        except LibrarianProfile.DoesNotExist:
            return []

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar and request:
            return request.build_absolute_uri(obj.avatar.url)
        return None


class RegisterLibrarianSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'password']

    def create(self, validated_data):
        email = validated_data['email']
        username = email.split('@')[0]
        base = username
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f'{base}{counter}'
            counter += 1
        user = CustomUser.objects.create_user(role=Role.LIBRARIAN, username=username, **validated_data)
        LibrarianProfile.objects.create(user=user, permissions=[])
        return user
