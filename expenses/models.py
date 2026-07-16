from django.db import models
from django.contrib.auth.models import User


CATEGORY_CHOICES = [
    ('Food', '🍔 Food'),
    ('Transport', '🚗 Transport'),
    ('Rent', '🏠 Rent'),
    ('Shopping', '🛒 Shopping'),
    ('Entertainment', '🎬 Entertainment'),
    ('Education', '📚 Education'),
    ('Medical', '🏥 Medical'),
    ('Recharge', '📱 Recharge'),
    ('Bills', '💡 Bills'),
    ('Others', '📦 Others'),
]


class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Others')
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.title} - ₹{self.amount}"


class Income(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes')
    source = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.source} - ₹{self.amount}"
