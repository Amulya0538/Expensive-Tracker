import csv
import io
import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Sum, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from .forms import ExpenseForm, IncomeForm, RegisterForm
from .models import Expense, Income, CATEGORY_CHOICES


# ─── Auth Views ─────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to Expense Tracker Pro, {user.first_name}! 🎉')
            return redirect('dashboard')
    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = AuthenticationForm()
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}! 👋')
            return redirect('dashboard')
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ─── Dashboard ──────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    user = request.user
    today = date.today()

    # Filter params
    month = request.GET.get('month', today.month)
    year = request.GET.get('year', today.year)
    search = request.GET.get('search', '').strip()

    try:
        month = int(month)
        year = int(year)
    except ValueError:
        month, year = today.month, today.year

    # All-time totals
    total_income = Income.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_expense = Expense.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    balance = total_income - total_expense

    # Monthly totals
    monthly_income = Income.objects.filter(user=user, date__month=month, date__year=year).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    monthly_expense = Expense.objects.filter(user=user, date__month=month, date__year=year).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    monthly_balance = monthly_income - monthly_expense

    # Recent transactions (last 10)
    recent_expenses = Expense.objects.filter(user=user).order_by('-date', '-created_at')[:10]
    recent_incomes = Income.objects.filter(user=user).order_by('-date', '-created_at')[:5]

    # Category breakdown for charts
    cat_data = (
        Expense.objects.filter(user=user)
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    chart_labels = [c['category'] for c in cat_data]
    chart_values = [float(c['total']) for c in cat_data]

    # Monthly trend (last 6 months)
    trend_labels = []
    trend_income = []
    trend_expense = []
    for i in range(5, -1, -1):
        d = today.replace(day=1) - timedelta(days=i * 28)
        m, y = d.month, d.year
        label = d.strftime('%b %Y')
        trend_labels.append(label)
        inc = Income.objects.filter(user=user, date__month=m, date__year=y).aggregate(t=Sum('amount'))['t'] or 0
        exp = Expense.objects.filter(user=user, date__month=m, date__year=y).aggregate(t=Sum('amount'))['t'] or 0
        trend_income.append(float(inc))
        trend_expense.append(float(exp))

    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
        'monthly_balance': monthly_balance,
        'recent_expenses': recent_expenses,
        'recent_incomes': recent_incomes,
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
        'trend_labels': json.dumps(trend_labels),
        'trend_income': json.dumps(trend_income),
        'trend_expense': json.dumps(trend_expense),
        'current_month': month,
        'current_year': year,
        'today': today,
        'categories': CATEGORY_CHOICES,
    }
    return render(request, 'dashboard.html', context)


# ─── Expense CRUD ───────────────────────────────────────────────────────────

@login_required
def expense_list(request):
    search = request.GET.get('search', '').strip()
    category = request.GET.get('category', '')
    expenses = Expense.objects.filter(user=request.user)
    if search:
        expenses = expenses.filter(Q(title__icontains=search) | Q(description__icontains=search))
    if category:
        expenses = expenses.filter(category=category)
    total = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    return render(request, 'expenses/expense_list.html', {
        'expenses': expenses,
        'total': total,
        'search': search,
        'selected_category': category,
        'categories': CATEGORY_CHOICES,
    })


@login_required
def expense_add(request):
    form = ExpenseForm(initial={'date': date.today()})
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            messages.success(request, f'Expense "{expense.title}" added successfully! 💸')
            return redirect('expense_list')
    return render(request, 'expenses/expense_form.html', {'form': form, 'action': 'Add', 'type': 'Expense'})


@login_required
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    form = ExpenseForm(instance=expense)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, f'Expense "{expense.title}" updated! ✅')
            return redirect('expense_list')
    return render(request, 'expenses/expense_form.html', {'form': form, 'action': 'Edit', 'type': 'Expense', 'obj': expense})


@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        title = expense.title
        expense.delete()
        messages.success(request, f'Expense "{title}" deleted.')
        return redirect('expense_list')
    return render(request, 'expenses/confirm_delete.html', {'obj': expense, 'type': 'Expense'})


# ─── Income CRUD ────────────────────────────────────────────────────────────

@login_required
def income_list(request):
    search = request.GET.get('search', '').strip()
    incomes = Income.objects.filter(user=request.user)
    if search:
        incomes = incomes.filter(Q(source__icontains=search) | Q(description__icontains=search))
    total = incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    return render(request, 'expenses/income_list.html', {
        'incomes': incomes,
        'total': total,
        'search': search,
    })


@login_required
def income_add(request):
    form = IncomeForm(initial={'date': date.today()})
    if request.method == 'POST':
        form = IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.user = request.user
            income.save()
            messages.success(request, f'Income "{income.source}" added! 💰')
            return redirect('income_list')
    return render(request, 'expenses/expense_form.html', {'form': form, 'action': 'Add', 'type': 'Income'})


@login_required
def income_edit(request, pk):
    income = get_object_or_404(Income, pk=pk, user=request.user)
    form = IncomeForm(instance=income)
    if request.method == 'POST':
        form = IncomeForm(request.POST, instance=income)
        if form.is_valid():
            form.save()
            messages.success(request, f'Income "{income.source}" updated! ✅')
            return redirect('income_list')
    return render(request, 'expenses/expense_form.html', {'form': form, 'action': 'Edit', 'type': 'Income', 'obj': income})


@login_required
def income_delete(request, pk):
    income = get_object_or_404(Income, pk=pk, user=request.user)
    if request.method == 'POST':
        source = income.source
        income.delete()
        messages.success(request, f'Income "{source}" deleted.')
        return redirect('income_list')
    return render(request, 'expenses/confirm_delete.html', {'obj': income, 'type': 'Income'})


# ─── Reports & Export ───────────────────────────────────────────────────────

@login_required
def reports(request):
    user = request.user
    today = date.today()

    # Category breakdown
    cat_data = (
        Expense.objects.filter(user=user)
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    chart_labels = [c['category'] for c in cat_data]
    chart_values = [float(c['total']) for c in cat_data]

    # Monthly bar chart (last 12 months)
    monthly_labels = []
    monthly_income_data = []
    monthly_expense_data = []
    for i in range(11, -1, -1):
        d = today.replace(day=1) - timedelta(days=i * 28)
        m, y = d.month, d.year
        monthly_labels.append(d.strftime('%b %y'))
        inc = Income.objects.filter(user=user, date__month=m, date__year=y).aggregate(t=Sum('amount'))['t'] or 0
        exp = Expense.objects.filter(user=user, date__month=m, date__year=y).aggregate(t=Sum('amount'))['t'] or 0
        monthly_income_data.append(float(inc))
        monthly_expense_data.append(float(exp))

    total_income = Income.objects.filter(user=user).aggregate(t=Sum('amount'))['t'] or 0
    total_expense = Expense.objects.filter(user=user).aggregate(t=Sum('amount'))['t'] or 0

    context = {
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_income_data': json.dumps(monthly_income_data),
        'monthly_expense_data': json.dumps(monthly_expense_data),
        'total_income': total_income,
        'total_expense': total_expense,
        'cat_data': cat_data,
    }
    return render(request, 'reports.html', context)


@login_required
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="expense_tracker_report.csv"'
    writer = csv.writer(response)

    writer.writerow(['Type', 'Title/Source', 'Amount (₹)', 'Category', 'Date', 'Description'])

    for exp in Expense.objects.filter(user=request.user).order_by('-date'):
        writer.writerow(['Expense', exp.title, exp.amount, exp.category, exp.date, exp.description or ''])

    for inc in Income.objects.filter(user=request.user).order_by('-date'):
        writer.writerow(['Income', inc.source, inc.amount, 'Income', inc.date, inc.description or ''])

    return response


@login_required
def export_pdf(request):
    user = request.user
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('title', parent=styles['Title'], fontSize=20, spaceAfter=12, textColor=colors.HexColor('#6366f1'))
    header_style = ParagraphStyle('header', parent=styles['Heading2'], fontSize=14, spaceAfter=8, textColor=colors.HexColor('#1e293b'))

    elements.append(Paragraph('Expense Tracker Pro – Full Report', title_style))
    elements.append(Paragraph(f'Generated for: {user.get_full_name() or user.username}', styles['Normal']))
    elements.append(Paragraph(f'Date: {date.today().strftime("%d %B %Y")}', styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))

    # Summary
    total_income = Income.objects.filter(user=user).aggregate(t=Sum('amount'))['t'] or 0
    total_expense = Expense.objects.filter(user=user).aggregate(t=Sum('amount'))['t'] or 0
    balance = total_income - total_expense

    elements.append(Paragraph('Financial Summary', header_style))
    summary_data = [
        ['Metric', 'Amount'],
        ['Total Income', f'₹{total_income:,.2f}'],
        ['Total Expense', f'₹{total_expense:,.2f}'],
        ['Net Balance', f'₹{balance:,.2f}'],
    ]
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.HexColor('#e2e8f0')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))

    # Expenses table
    elements.append(Paragraph('Expenses', header_style))
    exp_rows = [['Title', 'Amount', 'Category', 'Date']]
    for exp in Expense.objects.filter(user=user).order_by('-date'):
        exp_rows.append([exp.title, f'₹{exp.amount}', exp.category, str(exp.date)])

    if len(exp_rows) > 1:
        exp_table = Table(exp_rows, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        exp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ef4444')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fef2f2')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#fca5a5')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(exp_table)
    else:
        elements.append(Paragraph('No expenses found.', styles['Normal']))

    elements.append(Spacer(1, 0.3*inch))

    # Income table
    elements.append(Paragraph('Income', header_style))
    inc_rows = [['Source', 'Amount', 'Date']]
    for inc in Income.objects.filter(user=user).order_by('-date'):
        inc_rows.append([inc.source, f'₹{inc.amount}', str(inc.date)])

    if len(inc_rows) > 1:
        inc_table = Table(inc_rows, colWidths=[3*inch, 2*inch, 2*inch])
        inc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#22c55e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#86efac')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(inc_table)
    else:
        elements.append(Paragraph('No income found.', styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf',
                        headers={'Content-Disposition': 'attachment; filename="expense_tracker_report.pdf"'})
