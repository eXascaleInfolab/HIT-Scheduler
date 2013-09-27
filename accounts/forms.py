# -*- coding: utf-8 -*-:
from django import forms
from django.contrib.auth.models import User

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit



class LoginForm(forms.Form):
    username = forms.CharField(max_length=30)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_method = 'post'


        self.helper.layout = Layout(
            Fieldset(
                '',
                'username'
            ),
            ButtonHolder(
                Submit('submit', 'Start', css_class='button')
            )
        )
        super(LoginForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = "Enter your Amazon Mturk Worker ID"
