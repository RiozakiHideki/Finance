import uuid

import requests
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from .models import User, AbstractUser, FinanceData, UserProfile
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from .forms import RegisterForm, FilterForm, AddDataForm, AddDataUserForm, AddCategoryForm, AddBudgetForm, ChartForm, \
    DownloadDataForm
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')  # Используем бэкэнд Agg для генерации изображений без GUI
import matplotlib.pyplot as plt
import io
import base64
from rest_framework import generics, permissions, viewsets
from .serializers import UserProfileSerializer, FinanceDataSerializer


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

class FinanceDataViewSet(viewsets.ModelViewSet):
    queryset = FinanceData.objects.all()
    serializer_class = FinanceDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FinanceData.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            profile = user.userprofile
            profile.email_confirm_token = uuid.uuid4().hex
            profile.save()

            # Формируем ссылку подтверждения
            confirmation_url = request.build_absolute_uri(
                reverse('confirm_email', kwargs={'token': profile.email_confirm_token})
            )

            # Отправляем письмо
            send_mail(
                'Подтверждение регистрации',
                f'Для завершения регистрации перейдите по ссылке: {confirmation_url}',
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )

            return redirect('registration_pending')  # Новая страница ожидания

    else:
        form = RegisterForm()

    return render(request, 'app/registration.html', {'form': form})


def confirm_email(request, token):
    try:
        profile = get_object_or_404(UserProfile, email_confirm_token=token)

        # Проверка срока действия токена (24 часа)
        if (timezone.now() - profile.token_created) > timedelta(hours=24):
            messages.error(request, 'Срок действия ссылки истёк!')
            return redirect('invalid_token')

        if profile.user.is_active:
            messages.warning(request, 'Аккаунт уже был активирован ранее!')
            return redirect('login')

        # Активируем аккаунт
        profile.user.is_active = True
        profile.user.save()

        # Очищаем токен
        profile.email_confirm_token = ''
        profile.save()

        messages.success(request, 'Email успешно подтверждён! Можете войти.')
        return redirect('login')

    except Exception as e:
        messages.error(request, 'Неверная ссылка подтверждения!')
        return redirect('invalid_token')

def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('/')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    else:
        form = AuthenticationForm()

    return render(request, 'app/login.html', {'form': form})

def try_app(request):
    if 'transactions' not in request.session:
        request.session['transactions'] = []

    transactions = request.session['transactions']

    if request.method == 'POST':
        form = FilterForm(request.POST)

        if form.is_valid():
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            filter_type = form.cleaned_data['filter_type']

            filtered_transactions = []
            for transaction in transactions:
                transaction_date = datetime.strptime(transaction['date'], '%Y-%m-%d').date()
                if date_from and transaction_date < date_from:
                    continue
                if date_to and transaction_date > date_to:
                    continue
                if filter_type == 'income' and transaction['type'] != 'income':
                    continue
                if filter_type == 'expense' and transaction['type'] != 'expense':
                    continue
                filtered_transactions.append(transaction)

            transactions = filtered_transactions

    else:
        form = FilterForm()

    return render(request, 'app/try_app.html', {'form': form, 'transactions': transactions})

def add_data(request):
    if request.method == 'POST':
        form = AddDataForm(request.POST)

        if form.is_valid():
            data_type = form.cleaned_data['data_type']
            date = form.cleaned_data['date']
            category = form.cleaned_data['category']
            amount = form.cleaned_data['amount']

            new_transaction = {
                'type': data_type,
                'date': date.strftime('%Y-%m-%d'),
                'category': category,
                'amount': float(amount),
            }

            transactions = request.session.get('transactions', [])
            transactions.append(new_transaction)
            request.session['transactions'] = transactions

            return redirect('try_app')
    else:
        form = AddDataForm()

    return render(request, 'app/add_data.html', {'form': form})

def delete_transaction(request, index):
    transactions = request.session.get('transactions', [])
    if 0 <= index < len(transactions):
        del transactions[index]
        request.session['transactions'] = transactions
    return redirect('try_app')

def edit_transaction(request, index):
    transactions = request.session.get('transactions', [])
    if not (0 <= index < len(transactions)):
        return redirect('try_app')

    transaction = transactions[index]
    if request.method == 'POST':
        form = AddDataForm(request.POST)
        if form.is_valid():
            transactions[index] = {
                'type': form.cleaned_data['data_type'],
                'date': form.cleaned_data['date'].strftime('%Y-%m-%d'),
                'category': form.cleaned_data['category'],
                'amount': float(form.cleaned_data['amount']),
            }
            request.session['transactions'] = transactions
            return redirect('try_app')
    else:
        form = AddDataForm(initial=transaction)

    return render(request, 'app/edit_data.html', {'form': form, 'index': index})

def contacts(request):
    return render(request, 'app/contacts.html')

def home(request):
    return render(request, 'app/home.html')


@login_required(login_url='login')
def finances(request, user_id):
    user = request.user
    if user.id != user_id:
        return render(request, 'app/finances.html',
                      {'error': 'Вы не можете просматривать профили других пользователей!'})

    finance_data = FinanceData.objects.filter(user=user)
    user_profile = user.userprofile

    if request.method == 'POST':
        form = FilterForm(request.POST, user=user)
        if form.is_valid():
            date_from = form.cleaned_data.get('date_from')
            date_to = form.cleaned_data.get('date_to')
            filter_type = form.cleaned_data.get('filter_type')
            selected_budget = form.cleaned_data.get('budget')
            filtered_transactions = []
            for transaction in finance_data:
                transaction_date = transaction.date
                if date_from and transaction_date < date_from:
                    continue
                if date_to and transaction_date > date_to:
                    continue
                if filter_type == 'income' and transaction.sum < 0:
                    continue
                if filter_type == 'expense' and transaction.sum > 0:
                    continue
                if selected_budget and transaction.budget != selected_budget:
                    continue
                filtered_transactions.append(transaction)
            finance_data = filtered_transactions
    else:
        form = FilterForm(user=user)

    return render(request, 'app/finances.html', {
        'user': user,
        'finance_data': finance_data,
        'form': form,
        'user_budgets': user_profile.user_budgets  # Передаем данные о бюджетах
    })


@login_required(login_url='login')
def add_data_user(request, user_id):
    user = request.user
    if user.id != user_id:
        return render(request, 'app/finances.html',
                      {'error': 'Вы не можете просматривать профили других пользователей!'})
    if request.method == 'POST':
        form = AddDataUserForm(request.POST, user=user)
        if form.is_valid():
            data_type = form.cleaned_data['data_type']
            date = form.cleaned_data['date']
            category = form.cleaned_data['category']
            amount = form.cleaned_data['amount']  # This is a Decimal
            budget_name = form.cleaned_data['budget']

            # Convert Decimal to float before saving to JSONField
            amount_float = float(amount)

            # Обновляем баланс бюджета
            user_profile = user.userprofile
            for budget in user_profile.user_budgets:
                if budget['name'] == budget_name:
                    if data_type == 'income':
                        budget['balance'] += amount_float
                        budget['income'] += amount_float
                    elif data_type == 'expense':
                        budget['balance'] -= abs(amount_float)
                        budget['expense'] += abs(amount_float)
                    break
            user_profile.save()

            # Сохраняем транзакцию
            FinanceData.objects.create(
                user=user,
                date=date,
                category=category,
                sum=amount,
                budget=budget_name
            )
            return redirect(f'/finances/{user.id}/')
    else:
        form = AddDataUserForm(user=user)
    return render(request, 'app/add_data_user.html', {'form': form})


@login_required(login_url='login')
def edit_transaction_user(request, user_id, transaction_id):
    user = request.user
    if user.id != user_id:
        return render(request, 'app/finances.html',
                      {'error': 'Вы не можете просматривать профили других пользователей!'})

    transaction = get_object_or_404(FinanceData, id=transaction_id, user=user)

    if request.method == 'POST':
        form = AddDataUserForm(request.POST, user=user)
        if form.is_valid():
            transaction.date = form.cleaned_data['date']
            transaction.category = form.cleaned_data['category']
            transaction.sum = form.cleaned_data['amount']
            transaction.save()
            return redirect(f'/finances/{user.id}/')
    else:
        form = AddDataUserForm(user=user, initial={
            'date': transaction.date,
            'category': transaction.category,
            'amount': transaction.sum
        })

    return render(request, 'app/edit_data.html', {'form': form, 'transaction': transaction})


@login_required(login_url='login')
def delete_transaction_user(request, user_id, transaction_id):
    user = request.user
    if user.id != user_id:
        return render(request, 'app/finances.html',
                      {'error': 'Вы не можете просматривать профили других пользователей!'})

    transaction = get_object_or_404(FinanceData, id=transaction_id, user=user)
    transaction.delete()
    return redirect(f'/finances/{user.id}/')


@login_required(login_url='login')
def add_category_user(request, user_id):
    user = request.user
    if user.id != user_id:
        return render(request, 'app/finances.html',
                      {'error': 'Вы не можете просматривать профили других пользователей!'})

    user_profile = user.userprofile

    if request.method == 'POST':
        form = AddCategoryForm(request.POST)
        if form.is_valid():
            new_category = form.cleaned_data['category']
            if new_category not in user_profile.user_categories:
                user_profile.user_categories.append(new_category)
                user_profile.save()
            return redirect(f'/finances/{user.id}/')
    else:
        form = AddCategoryForm()

    existing_categories = user_profile.user_categories

    return render(request, 'app/add_category_user.html', {
        'form': form,
        'existing_categories': existing_categories
    })


@login_required(login_url='login')
def add_budget_user(request, user_id):
    user = request.user
    if user.id != user_id:
        return render(request, 'app/finances.html',
                      {'error': 'Вы не можете просматривать профили других пользователей!'})
    if request.method == 'POST':
        form = AddBudgetForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            balance = form.cleaned_data['balance']

            user_profile = user.userprofile
            user_profile.user_budgets.append({
                'name': name,
                'balance': float(balance),
                'income': 0,
                'expense': 0
            })
            user_profile.save()
            return redirect(f'/finances/{user.id}/')
    else:
        form = AddBudgetForm()
    return render(request, 'app/add_budget_user.html', {'form': form})


@login_required(login_url='login')
def delete_budget_user(request, user_id, budget_name):
    user = request.user
    if user.id != user_id:
        return render(request, 'app/finances.html',
                      {'error': 'Вы не можете просматривать профили других пользователей!'})

    user_profile = user.userprofile
    user_profile.user_budgets = [budget for budget in user_profile.user_budgets if budget['name'] != budget_name]
    user_profile.save()

    return redirect(f'/finances/{user.id}/')


@login_required(login_url='login')
def chart_user(request, user_id):
    user = request.user
    if user.id != user_id:
        return render(request, 'app/finances.html',
                      {'error': 'Вы не можете просматривать профили других пользователей!'})

    if request.method == 'POST':
        form = ChartForm(request.POST, user=user)
        if form.is_valid():
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            budget_name = form.cleaned_data['budget']

            # Фильтруем транзакции по выбранному бюджету и периоду
            transactions = FinanceData.objects.filter(
                user=user,
                budget=budget_name,
                date__range=(date_from, date_to)
            ).order_by('date')

            # Инициализируем переменные для графиков и диаграмм
            income_total = 0
            expense_total = 0
            income_categories = {}
            expense_categories = {}
            balance_series = []
            dates = []
            current_balance = 0

            for transaction in transactions:
                if transaction.sum > 0:
                    income_total += transaction.sum
                    category = transaction.category
                    if category in income_categories:
                        income_categories[category] += transaction.sum
                    else:
                        income_categories[category] = transaction.sum
                else:
                    expense_total += abs(transaction.sum)
                    category = transaction.category
                    if category in expense_categories:
                        expense_categories[category] += abs(transaction.sum)
                    else:
                        expense_categories[category] = abs(transaction.sum)

                # Обновляем текущий баланс
                current_balance += transaction.sum
                balance_series.append(current_balance)
                dates.append(transaction.date)

            # График баланса
            plt.figure(figsize=(10, 5))
            plt.plot(dates, balance_series, label='Баланс', color='blue')
            plt.xlabel('Дата')
            plt.ylabel('Баланс')
            plt.title('График баланса')
            plt.legend()
            plt.grid(True)
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            chart_balance = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()

            # Диаграмма процентного соотношения доходов и расходов
            labels = ['Доходы', 'Расходы']
            sizes = [income_total, expense_total]
            colors = ['green', 'red']
            plt.figure(figsize=(8, 8))
            plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
            plt.axis('equal')
            plt.title('Процентное соотношение доходов и расходов')
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            pie_income_expense = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()

            # Диаграмма процентного разделения по категориям доходов
            if income_categories:
                labels = list(income_categories.keys())
                sizes = list(income_categories.values())
                plt.figure(figsize=(8, 8))
                plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
                plt.axis('equal')
                plt.title('Процентное разделение по категориям доходов')
                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                pie_income_categories = base64.b64encode(buf.read()).decode('utf-8')
                plt.close()
            else:
                pie_income_categories = None

            # Диаграмма процентного разделения по категориям расходов
            if expense_categories:
                labels = list(expense_categories.keys())
                sizes = list(expense_categories.values())
                plt.figure(figsize=(8, 8))
                plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
                plt.axis('equal')
                plt.title('Процентное разделение по категориям расходов')
                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                pie_expense_categories = base64.b64encode(buf.read()).decode('utf-8')
                plt.close()
            else:
                pie_expense_categories = None

            return render(request, 'app/chart_user.html', {
                'form': form,
                'chart_balance': chart_balance,
                'pie_income_expense': pie_income_expense,
                'pie_income_categories': pie_income_categories,
                'pie_expense_categories': pie_expense_categories,
            })
    else:
        form = ChartForm(user=user)

    return render(request, 'app/chart_user.html', {'form': form})


@login_required(login_url='login')
def download_data_user(request, user_id):
    user = request.user
    if user.id != user_id:
        return render(request, 'app/finances.html',
                      {'error': 'Вы не можете просматривать профили других пользователей!'})

    if request.method == 'POST':
        form = DownloadDataForm(request.POST, user=user)
        if form.is_valid():
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            budget_name = form.cleaned_data['budget']

            # Фильтруем транзакции по выбранному бюджету и периоду
            transactions = FinanceData.objects.filter(
                user=user,
                budget=budget_name,
                date__range=(date_from, date_to)
            ).order_by('date')

            # Создаем текстовый файл с данными
            response = HttpResponse(content_type='text/plain; charset=utf-8')
            response[
                'Content-Disposition'] = f'attachment; filename="{budget_name}_transactions_{date_from}_{date_to}.txt"'

            # Записываем заголовки с выравниванием
            headers = "Дата\tКатегория\tСумма\tБюджет\n"
            response.write(headers)

            # Определяем максимальную длину каждого столбца для выравнивания
            max_date_len = len("Дата")
            max_category_len = len("Категория")
            max_sum_len = len("Сумма")
            max_budget_len = len("Бюджет")

            for transaction in transactions:
                max_date_len = max(max_date_len, len(str(transaction.date)))
                max_category_len = max(max_category_len, len(transaction.category))
                max_sum_len = max(max_sum_len, len(f"{transaction.sum}"))
                max_budget_len = max(max_budget_len, len(transaction.budget))

            # Записываем данные транзакций с выравниванием
            for transaction in transactions:
                date_str = str(transaction.date).ljust(max_date_len)
                category_str = transaction.category.ljust(max_category_len)
                sum_str = f"{transaction.sum}".ljust(max_sum_len)
                budget_str = transaction.budget.ljust(max_budget_len)
                response.write(f"{date_str}\t{category_str}\t{sum_str}\t{budget_str}\n")

            return response
    else:
        form = DownloadDataForm(user=user)

    return render(request, 'app/download_data_user.html', {'form': form})