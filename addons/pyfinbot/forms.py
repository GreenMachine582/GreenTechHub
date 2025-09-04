from django import forms

from ..base.widgets import SwitchInput


class StockForm(forms.Form):
    symbol: str = forms.CharField(max_length=20)
    market: str = forms.CharField(max_length=20)
    name: str = forms.CharField()
    is_active: bool = forms.BooleanField(required=False, initial=True, disabled=True, label="Active",
                                         widget=SwitchInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if record_id := kwargs.get("initial", {}).get("id"):
            for field in ["symbol", "market"]:
                self.fields[field].disabled = True

        self.record_id = record_id


class TransactionForm(forms.Form):
    user_id = forms.IntegerField(label="User ID", required=False, disabled=True)
    stock_id = forms.IntegerField(label="Stock ID", required=False)
    stock_symbol = forms.CharField(label="Stock Symbol", required=False)
    stock_market = forms.CharField(label="Stock Market", required=False)
    stock_name = forms.CharField(label="Stock Name", required=False)

    transaction_date = forms.DateField(label="Transaction Date", required=False, disabled=True,
                                       widget=forms.DateInput(attrs={'type': 'date'}))
    type = forms.ChoiceField(label="Transaction Type", choices=[('buy', 'Buy'), ('sell', 'Sell')])
    units = forms.DecimalField(label="Transaction Units", max_digits=12, decimal_places=2)
    price = forms.DecimalField(label="Transaction Price", max_digits=12, decimal_places=3)
    total_value = forms.DecimalField(label="Transaction Total Value", max_digits=18, decimal_places=6, required=False, initial=0.0,
                                     disabled=True)
    fees = forms.DecimalField(label="Transaction Fees", max_digits=12, decimal_places=2, required=False, initial=0.0)
    cost = forms.DecimalField(label="Transaction Cost", max_digits=18, decimal_places=6, required=False, initial=0.0,
                              disabled=True)
    notes = forms.CharField(label="Transaction Notes", required=False, disabled=True, widget=forms.Textarea)
    fy = forms.IntegerField(label="Fiscal Year", required=False, disabled=True)
