from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Business, Lead


class SignUpForm(UserCreationForm):
    """Username + password signup (MVP)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for fname in ("username", "password1", "password2"):
            if fname in self.fields:
                self.fields[fname].widget.attrs.setdefault("class", "input")


class BusinessSetupForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = ["name", "service", "city"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "Acme Haulers"}),
            "service": forms.TextInput(attrs={"class": "input", "placeholder": "Junk removal"}),
            "city": forms.TextInput(attrs={"class": "input", "placeholder": "Austin, TX"}),
        }


class ManualLeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["name", "phone", "email", "notes", "status"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "phone": forms.TextInput(attrs={"class": "input"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
            "notes": forms.Textarea(attrs={"class": "input", "rows": 2}),
            "status": forms.Select(attrs={"class": "select"}),
        }


class LeadStatusForm(forms.Form):
    status = forms.ChoiceField(choices=Lead.Status.choices, widget=forms.Select(attrs={"class": "select sm"}))


class PublicLeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["name", "phone", "email", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "required": True}),
            "phone": forms.TextInput(attrs={"class": "input"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
            "notes": forms.Textarea(attrs={"class": "input", "rows": 3, "placeholder": "What do you need?"}),
        }
