from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from .models import FinanceData, UserProfile
from .forms import RegisterForm

User = get_user_model()

class UserModelTests(TestCase):
    def test_user_profile_creation(self):
        """Тест автоматического создания и подтверждения профиля"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_active=True,
        )
        self.assertTrue(hasattr(user, 'userprofile'))
        self.assertEqual(UserProfile.objects.count(), 1)

class FinanceViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_active=True
        )
        self.client.login(username='testuser', password='testpass123')

    def test_finance_dashboard_access(self):
        """Тест доступа к финансовой панели"""
        response = self.client.get(reverse('finances', kwargs={'user_id': self.user.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Финансовые данные")

    def test_transaction_creation(self):
        """Тест создания транзакции"""
        response = self.client.post(reverse('add_data_user', args=[self.user.id]), {
            'data_type': 'income',
            'date': '2024-01-01',
            'category': 'Зарплата',
            'amount': '1000',
            'budget': 'Мой бюджет'
        })
        self.assertEqual(FinanceData.objects.count(), 1)
        self.assertRedirects(response, f'/finances/{self.user.id}/')

class FormTests(TestCase):
    def test_register_form_validation(self):
        """Тест валидации формы регистрации"""
        # Дублирующийся email
        User.objects.create_user(username='existing', email='test@example.com', password='pass')
        form = RegisterForm(data={
            'username': 'newuser',
            'email': 'test@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'first_name': 'Test'  # Добавлено поле first_name
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

class SecurityTests(TestCase):
    def test_unauthenticated_access(self):
        """Тест доступа к защищенным страницам без авторизации"""
        urls = [
            reverse('finances', kwargs={'user_id': 1}),
            reverse('add_data_user', args=[1]),
        ]

        for url in urls:
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('login')}?next={url}")

    def test_cross_user_access(self):
        """Тест попытки доступа к чужим данным"""
        user1 = User.objects.create_user(username='user1', password='pass1')
        user2 = User.objects.create_user(username='user2', password='pass2')
        self.client.login(username='user1', password='pass1')

        # Попытка доступа к данным user2
        response = self.client.get(reverse('finances', kwargs={'user_id': user2.id}))
        self.assertContains(response, "Вы не можете просматривать профили других пользователей!")

class EmailTests(TestCase):
    def test_confirmation_email_sent(self):
        """Тест отправки письма с подтверждением"""
        self.client.post(reverse('register'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'first_name': 'Test'  # Добавлено поле first_name
        })
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Подтверждение регистрации', mail.outbox[0].subject)

class FilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.transaction = FinanceData.objects.create(
            user=self.user,
            date='2024-01-15',
            category='Тест',
            sum=100,
            budget='Мой бюджет'
        )

    def test_date_filter(self):
        """Тест фильтрации по дате"""
        response = self.client.post(reverse('finances', kwargs={'user_id': self.user.id}), {
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'filter_type': 'all',
            'budget': ''
        })
        self.assertContains(response, 'Тест')

        response = self.client.post(reverse('finances', kwargs={'user_id': self.user.id}), {
            'date_from': '2024-02-01',
            'date_to': '2024-02-28',
            'filter_type': 'all',
            'budget': ''
        })
        self.assertNotContains(response, 'Тест')