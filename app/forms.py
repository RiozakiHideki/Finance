from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User, UserProfile

class RegisterForm(UserCreationForm):

    first_name = forms.CharField(required=True,
                                 widget=forms.TextInput(attrs={'placeholder': 'Your name'}),
                                 min_length=2,
                                 max_length=50
                                 )

    email = forms.EmailField(required=True,
                             widget=forms.EmailInput(attrs={'placeholder': 'Email'}))

    username = forms.CharField(required=True,
                               min_length=4,
                               widget=forms.TextInput(attrs={'placeholder': 'Username'}))

    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))

    class Meta:
        model = User
        fields = ['first_name', 'username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():  # Проверка на уникальность
            raise ValidationError("Пользователь с таким email уже зарегистрирован.")
        return email

    # Добавляем сохранение неактивного пользователя
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False
        if commit:
            user.save()
            user.userprofile.generate_confirmation_token()
        return user


class FilterForm(forms.Form):
    date_from = forms.DateField(
        required=False,
        label='От:',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        label='До:',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    filter_type = forms.ChoiceField(
        choices=[
            ('all', 'Всё'),
            ('income', 'Доходы'),
            ('expense', 'Расходы'),
        ],
        initial='all',
        label='Фильтр'
    )
    budget = forms.ChoiceField(
        choices=[],
        required=False,
        label='Бюджет'
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            user_profile = UserProfile.objects.get(user=user)
            self.fields['budget'].choices = user_profile.get_budgets_choices()


class AddDataForm(forms.Form):
    data_type = forms.ChoiceField(
        choices=[
            ('income', 'Доход'),
            ('expense', 'Расход'),
        ],
        label='Тип данных'
    )
    date = forms.DateField(
        label='Дата',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    category = forms.ChoiceField(
        choices=[
            ('Зарплата', 'Зарплата'),
            ('Подарок', 'Подарок'),
            ('Еда', 'Еда'),
            ('Транспорт', 'Транспорт'),
        ],
        label='Категория'
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='Сумма'
    )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        data_type = self.cleaned_data.get('data_type')

        if data_type == 'income' and amount < 0:
            raise ValidationError("Сумма дохода должна быть больше 0.")
        if data_type == 'expense' and amount > 0:
            raise ValidationError("Сумма расхода должна быть меньше 0.")

        return amount


class AddDataUserForm(forms.Form):
    data_type = forms.ChoiceField(
        choices=[
            ('income', 'Доход'),
            ('expense', 'Расход'),
        ],
        label='Тип данных'
    )
    date = forms.DateField(
        label='Дата',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    category = forms.ChoiceField(
        choices=[],
        label='Категория'
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='Сумма'
    )
    budget = forms.ChoiceField(
        choices=[],
        label='Бюджет'
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            user_profile = UserProfile.objects.get(user=user)
            self.fields['category'].choices = user_profile.get_categories_choices()
            self.fields['budget'].choices = user_profile.get_budgets_choices()

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        data_type = self.cleaned_data.get('data_type')
        if data_type == 'income' and amount < 0:
            raise ValidationError("Сумма дохода должна быть больше 0.")
        if data_type == 'expense' and amount > 0:
            raise ValidationError("Сумма расхода должна быть меньше 0.")
        return amount

class AddCategoryForm(forms.Form):
    category = forms.CharField(label='Новая категория')


class AddBudgetForm(forms.Form):
    name = forms.CharField(
        label='Название бюджета',
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Название бюджета'})
    )
    balance = forms.DecimalField(
        label='Баланс',
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'placeholder': 'Баланс'})
    )

class ChartForm(forms.Form):
    date_from = forms.DateField(
        required=True,
        label='От:',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_to = forms.DateField(
        required=True,
        label='До:',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    budget = forms.ChoiceField(
        choices=[],
        required=True,
        label='Бюджет'
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            user_profile = UserProfile.objects.get(user=user)
            self.fields['budget'].choices = user_profile.get_budgets_choices()

class DownloadDataForm(forms.Form):
    date_from = forms.DateField(
        required=True,
        label='От:',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_to = forms.DateField(
        required=True,
        label='До:',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    budget = forms.ChoiceField(
        choices=[],
        required=True,
        label='Бюджет'
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            user_profile = UserProfile.objects.get(user=user)
            self.fields['budget'].choices = user_profile.get_budgets_choices()