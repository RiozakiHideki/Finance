from rest_framework import serializers
from .models import UserProfile, FinanceData

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['user', 'user_categories', 'user_budgets']

class FinanceDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinanceData
        fields = ['id', 'user', 'date', 'category', 'sum', 'budget']