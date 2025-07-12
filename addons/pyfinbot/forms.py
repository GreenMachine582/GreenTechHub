from django import forms


class StockForm(forms.Form):
    symbol: str = forms.CharField(max_length=20)
    market: str = forms.CharField(max_length=20)
    name: str = forms.CharField()


class TransactionForm(forms.Form):
    user_id = forms.IntegerField(label="User ID")
    stock_id = forms.IntegerField(label="Stock ID")
    transaction_date = forms.DateField(label="Transaction Date", widget=forms.DateInput(attrs={'type': 'date'}))
    type = forms.ChoiceField(label="Transaction Type", choices=[('buy', 'Buy'), ('sell', 'Sell')])
    units = forms.DecimalField(label="Transaction Units", max_digits=12, decimal_places=2)
    price = forms.DecimalField(label="Transaction Price", max_digits=12, decimal_places=3)
    total_value = forms.DecimalField(label="Transaction Total Value", max_digits=18, decimal_places=6, required=False, initial=0.0)
    fees = forms.DecimalField(label="Transaction Fees", max_digits=12, decimal_places=2, required=False, initial=0.0)
    cost = forms.DecimalField(label="Transaction Cost", max_digits=18, decimal_places=6, required=False, initial=0.0)
    notes = forms.CharField(label="Transaction Notes", required=False, widget=forms.Textarea)
    fy = forms.IntegerField(label="Fiscal Year", required=False, initial=0)
