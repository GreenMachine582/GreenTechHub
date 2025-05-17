from django import forms


class StockForm(forms.Form):
    symbol: str = forms.CharField(max_length=20)
    market: str = forms.CharField(max_length=20)
    name: str = forms.CharField()
