import os
import django
from datetime import date, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ExpenseTracker.settings')
django.setup()

from django.contrib.auth.models import User
from expenses.models import Expense, Income

# Create test user
user, created = User.objects.get_or_create(username='amulya')
user.first_name = 'Amulya'
user.last_name = 'Patel'
user.email = 'amulya@example.com'
user.set_password('pass1234')
user.save()

# Clear existing entries
Expense.objects.filter(user=user).delete()
Income.objects.filter(user=user).delete()

# Add Income
sources = [('Salary', 45000), ('Freelance Coding', 12000), ('Investment Dividends', 3500)]
today = date.today()

for source, amount in sources:
    Income.objects.create(
        user=user,
        source=source,
        amount=amount,
        date=today - timedelta(days=random.randint(0, 10)),
        description=f"Payout for {source}"
    )

# Add Expenses across categories
expense_categories = [
    ('Food', 'Groceries and snacks', [250, 1200, 350, 800]),
    ('Transport', 'Petrol & Cab fares', [500, 1500, 200, 750]),
    ('Rent', 'Apartment Rent', [12000]),
    ('Shopping', 'Clothes & items', [3500, 1200, 800]),
    ('Entertainment', 'Movie tickets and Netflix subscription', [350, 600, 250]),
    ('Education', 'E-learning subscription', [1500]),
    ('Medical', 'Pharmacy prescriptions', [450, 900]),
    ('Recharge', 'Mobile recharge', [499, 749]),
    ('Bills', 'Electricity & High-speed Wifi', [2500, 1200]),
    ('Others', 'Miscellaneous items', [300, 150])
]

for cat, desc, amounts in expense_categories:
    for amt in amounts:
        Expense.objects.create(
            user=user,
            title=f"{cat} purchase",
            amount=amt,
            category=cat,
            date=today - timedelta(days=random.randint(0, 28)),
            description=desc
        )

print("Database seeded successfully with user 'amulya' (password: pass1234) and sample transactions.")
