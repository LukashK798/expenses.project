import csv
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.generic.list import ListView
from django.db.models import Sum
from django.db.models.functions import TruncYear, TruncMonth
from .forms import ExpenseSearchForm
from .models import Expense, Category
from .reports import summary_per_category

class ExpenseListView(ListView):
    model = Expense
    paginate_by = 5

    def get_context_data(self, *, object_list=None, **kwargs):
        queryset = object_list if object_list is not None else self.object_list

        form = ExpenseSearchForm(self.request.GET)
        if form.is_valid():
            name = form.cleaned_data.get('name', '').strip()
            date_from = form.cleaned_data.get('date_from')
            date_to = form.cleaned_data.get('date_to')
            categories = form.cleaned_data.get('categories')

            if name:
                queryset = queryset.filter(name__icontains=name)
            if date_from:
                queryset = queryset.filter(date__gte=date_from)
            if date_to:
                queryset = queryset.filter(date__lte=date_to)
            if categories:
                queryset = queryset.filter(category__in=categories)

        sort_by = self.request.GET.get("sort", "date")
        order = self.request.GET.get("order", "asc")

        if sort_by == "category":
            queryset = queryset.order_by("category" if order == "asc" else "-category")
        else:
            queryset = queryset.order_by("date" if order == "asc" else "-date")

        monthly_summary = (
            queryset
            .annotate(year=TruncYear("date"), month=TruncMonth("date"))
            .values("year", "month")
            .annotate(total_spent=Sum("amount"))
            .order_by("year", "month")
        )

        return super().get_context_data(
            form=form,
            object_list=queryset,
            summary_per_category=summary_per_category(queryset),
            monthly_summary=monthly_summary,
            sort_by=sort_by,
            order=order,
            **kwargs
        )

class CategoryListView(ListView):
    model = Category
    paginate_by = 5

class ExpenseCSVExportView(View):
    def get(self, request, *args, **kwargs):
        queryset = Expense.objects.all()
        form = ExpenseSearchForm(self.request.GET)

        if form.is_valid():
            name = form.cleaned_data.get("name", "").strip()
            date_from = form.cleaned_data.get("date_from")
            date_to = form.cleaned_data.get("date_to")
            categories = form.cleaned_data.get("categories")

            if name:
                queryset = queryset.filter(name__icontains=name)
            if date_from:
                queryset = queryset.filter(date__gte=date_from)
            if date_to:
                queryset = queryset.filter(date__lte=date_to)
            if categories:
                queryset = queryset.filter(category__in=categories)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="expenses.csv"'

        writer = csv.writer(response)
        writer.writerow(["Category", "Name", "Amount", "Date"])

        for expense in queryset:
            writer.writerow([expense.category, expense.name, expense.amount, expense.date])

        return response

class ExpenseChartDataView(View):
    def get(self, request, *args, **kwargs):
        queryset = Expense.objects.all()
        form = ExpenseSearchForm(request.GET)

        if form.is_valid():
            name = form.cleaned_data.get("name", "").strip()
            date_from = form.cleaned_data.get("date_from")
            date_to = form.cleaned_data.get("date_to")
            categories = form.cleaned_data.get("categories")

            if name:
                queryset = queryset.filter(name__icontains=name)
            if date_from:
                queryset = queryset.filter(date__gte=date_from)
            if date_to:
                queryset = queryset.filter(date__lte=date_to)
            if categories:
                queryset = queryset.filter(category__in=categories)

        expenses = queryset.annotate(year=TruncYear("date"), month=TruncMonth("date")) \
            .values("year", "month") \
            .annotate(total=Sum("amount")) \
            .order_by("year", "month")

        data = {
            "labels": [f"{expense['year'].year}-{expense['month'].month:02d}" for expense in expenses],
            "data": [expense["total"] for expense in expenses]
        }

        return JsonResponse(data)
