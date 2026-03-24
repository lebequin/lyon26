from django import forms
from ..models import Visit


class VisitForm(forms.ModelForm):
    """Form for creating/editing visits"""
    class Meta:
        model = Visit
        fields = ['building', 'round', 'date', 'open_doors', 'knocked_doors', 'comment']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'comment': forms.Textarea(attrs={'rows': 3}),
        }
