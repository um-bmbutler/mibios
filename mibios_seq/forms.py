from collections import OrderedDict

from django import forms
from django.core.exceptions import ValidationError

from mibios.forms import ExportFormatForm

from .models import AnalysisProject


class ExportSharedForm(ExportFormatForm):
    NORM_NONE = 'none'
    group_column_choices = []
    group_column_initial = None
    projects = ()

    project = forms.ChoiceField(
        required=True,
        help_text='Pick abundance data from this analysis project.',
    )
    normalize = forms.ChoiceField(
        widget=forms.RadioSelect(attrs={'class': None}),
        required=False,
        initial=0,
        help_text='Export data as absolute counts (none) or relative abundance'
                  ', that is, either as decimal fractions between 0.0 and 1.0 '
                  'or as normalized counts which has the absolute numbers '
                  'scaled to a normal sample size of 10,000.',
    )
    group_cols = forms.ChoiceField(
        widget=forms.RadioSelect(attrs={'class': None}),
        required=True,
        label='group column(s) / row id',
        help_text='What to use as row identifiers',
    )
    mothur = forms.BooleanField(
        required=False,
        initial=False,
        label='mothur compatible',
        help_text='Will make a shared file exactly as Mothur would make it. '
                  'The default is to make a tables without the "label" and '
                  '"numOtus" columns',
    )

    @classmethod
    def factory(cls, view):
        """
        Derive a form class with some view-specific attributes set

        We want to adjust the form's fields (setting choices and intials) but
        have to let the metaclass magic do its thing (setting up the fields)
        first.  So here in the factory only some regular class attributes are
        set.  At instantiation time, the constructor will use these attributes
        to modify the fields.
        """
        opts = OrderedDict()
        opts['norm_choices'] = view.norm_choices
        opts['group_column_choices'] = view.group_col_choices
        opts['group_column_initial'] = view.group_col_choices[0][0]
        opts['projects'] = [
            (i, i) for i in
            AnalysisProject.objects.all().values_list('name', flat=True)
        ]
        return super().factory(view, 'Auto' + cls.__name__, (cls, ), opts=opts)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['normalize'].choices = self.norm_choices
        self.fields['group_cols'].choices = self.group_column_choices
        self.fields['group_cols'].initial = self.group_column_initial
        self.fields['project'].choices = self.projects
        self.fields['project'].initial = self.projects[-1][0]  # most recent

    def clean_normalize(self):
        val = self.cleaned_data['normalize']
        if val == self.NORM_NONE:
            return None

        try:
            val = int(val)
            if val < 0:
                raise ValueError
        except (ValueError, TypeError):
            msg = f'must be a positive integer or "{self.NORM_NONE}"'
            raise ValidationError(msg)

        return val