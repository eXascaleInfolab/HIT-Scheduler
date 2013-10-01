# -*- coding: utf-8 -*-:
from django.shortcuts import redirect

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout

from django.core.context_processors import csrf

from accounts.tokens import generate_token
from fast.utils import render_template

from .models import UserProfile

from .forms import LoginForm


def login_view(request):
    print "login"
    csrf_tk = {}
    csrf_tk.update(csrf(request))

    if request.user.is_authenticated():
        return redirect('/')
    print request.user.username

    if 'wid' in request.GET:
        wid = request.GET.get('wid')
    else:
        wid = ''

    login_error = ''
    if request.method == 'POST':
        login_form = LoginForm(request.POST, initial={
            'username': wid
        })
        if login_form.is_valid():
            username = request.POST['username']
            user = authenticate(username=username, password="cool")
            if user is not None:
                print "user is back !"
                login(request, user)
            else:
                print "user is new: create him"
                user = User.objects.create_user(username, 'username@hitbit.co', "cool")
                user = authenticate(username=username, password="cool")
                login(request, user)
                user_profile = UserProfile.objects.create(user=request.user)
                user_profile.save()

            if user is not None:
                request.session['get_token'] = generate_token()
                if 'next' in request.POST:
                    return redirect(request.POST['next'] or '/')
                else:
                    return redirect('/')
            else:
                login_error = 'Sorry, something bad happened.'
        else:
            login_error = 'Form invalid'

    if request.method != 'POST':
        login_form = LoginForm(initial={
            'username': wid
        })

    csrf_tk['login_error'] = login_error
    csrf_tk['login_form'] = login_form
    if 'next' in request.GET:
        csrf_tk['next'] = request.GET.get('next')
    return render_template('login.html', csrf_tk)


@login_required
def logout_view(request):
    print "logout"
    logout(request)
    request.session.clear()
    return redirect('/')
