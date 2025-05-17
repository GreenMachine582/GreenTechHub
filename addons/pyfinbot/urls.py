
from django.urls import path

from . import views


urlpatterns = [
    path('pyfinbot/stock/list/', views.StockListView.as_view(), name='pyfinbot-stock-list'),
    path('pyfinbot/stock/form/', views.StockFormView.as_view(), name='pyfinbot-stock-form'),
    path('pyfinbot/stock/form/<int:record_id>/', views.StockFormView.as_view(),
         name='pyfinbot-stock-form'),
    path('pyfinbot/stock/delete/<int:record_id>/', views.stock_delete,
         name='pyfinbot-stock-delete'),
]
