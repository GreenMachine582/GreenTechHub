
from django.urls import path

from . import views


urlpatterns = [
    path('pyfinbot/stock/list/', views.StockListView.as_view(), name='pyfinbot-stock-list'),
    path('pyfinbot/stock/form/', views.StockFormView.as_view(), name='pyfinbot-stock-form'),
    path('pyfinbot/stock/form/<int:record_id>/', views.StockFormView.as_view(),
         name='pyfinbot-stock-form'),
    path('pyfinbot/stock/delete/<int:record_id>/', views.StockDeleteView.as_view(),
         name='pyfinbot-stock-delete'),
    path("stock/picker/", views.StockPickerModalView.as_view(), name="pyfinbot-stock-picker"),

    path('pyfinbot/transaction/list/', views.TransactionListView.as_view(), name='pyfinbot-transaction-list'),
    path('pyfinbot/transaction/form/', views.TransactionFormView.as_view(), name='pyfinbot-transaction-form'),
    path('pyfinbot/transaction/form/<int:record_id>/', views.TransactionFormView.as_view(),
         name='pyfinbot-transaction-form'),
    path('pyfinbot/transaction/delete/<int:record_id>/', views.TransactionDeleteView.as_view(),
         name='pyfinbot-transaction-delete'),
]
