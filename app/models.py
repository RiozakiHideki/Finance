import uuid

from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.dispatch import receiver
from django.db.models.signals import post_save

def default_categories():
    return ["Зарплата", "Подарок", "Еда", "Транспорт"]

def default_budgets():
    return [{"name": "Мой бюджет", "balance": 0, "income": 0, "expense": 0}]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_categories = models.JSONField(default=default_categories)
    user_budgets = models.JSONField(default=default_budgets)
    email_confirm_token = models.CharField(max_length=100, blank=True)
    token_created = models.DateTimeField(auto_now_add=True)
    is_email_confirmed = models.BooleanField(default=False)

    def get_categories_choices(self):
        return [(category, category) for category in self.user_categories]

    def get_budgets_choices(self):
        return [(budget['name'], budget['name']) for budget in self.user_budgets]

    def generate_confirmation_token(self):
        self.email_confirm_token = uuid.uuid4().hex
        self.save()
        return self.email_confirm_token

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()

class FinanceData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField(null=False)
    category = models.CharField(max_length=100, null=False)
    sum = models.FloatField(null=False)
    budget = models.CharField(max_length=100, null=True, blank=True)