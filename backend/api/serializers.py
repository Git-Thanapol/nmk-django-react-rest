from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Note

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password']
        extra_kwargs = {'password': {'write_only': True}} # Password should not be readable

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data) # Use create_user to hash the password
        return user
    
class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ['id', 'user', 'title', 'content', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at'] # user will be set from request, timestamps are read-only
        extra_kwargs = {"user": {"read_only": True}}
    