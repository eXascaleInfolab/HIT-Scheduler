from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader
from django.shortcuts import render_to_response, get_object_or_404, redirect, render
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from accounts.models import UserProfile, Batch, Task, TaskSubmit
from accounts.views import login_view
from django.contrib.sessions.models import Session
from datetime import datetime, timedelta
from tracking.models import Visitor
from django.db import transaction
from django.db.models import Sum, Avg, F
import random
import string
import os
import fcntl
from django.core.files import locks
from django.utils.timezone import utc
from django.conf import settings
from decimal import *
import ast

# Core method
def work(request,task_id):
    print "giving !!!!!!"
    # Some user management with mturk
    workerId = request.GET.get('workerId')
    assignmentId = request.GET.get('assignmentId')
    print workerId
    if request.user.is_authenticated() == False:
        if workerId != None:
            user = authenticate(username=workerId, password="cool")
            if user is not None:
                print "user is back !"
                login(request, user)
            else:
                print "user is new: create him"
                user = User.objects.create_user(workerId, 'username@hitbit.co', "cool")
                user = authenticate(username=workerId, password="cool")
                login(request, user)
                user_profile = UserProfile.objects.create(user=request.user)
                user_profile.save()
        else:
            return render_to_response('welcome.html', context_instance=RequestContext(request))

    if task_id == None:
        return render_to_response('error.html', {'user_profile':user_profile}, context_instance=RequestContext(request))

    # this is by default ..
    batch = Batch.objects.get(id=1)
    # get the user profile
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        print user_profile.credit, user_profile.user.username
    except UserProfile.DoesNotExist:
        return HttpResponseRedirect(reverse('login_view'))

    ## Create the vector of performance
    data = []
    last= 0 
    prev= 0
    avg_data = 0
    max_data = 0
    upside = True
    BASE_PAY = batch.value
    tasks = TaskSubmit.objects.filter(user=user_profile).order_by('starttime')
    for t in tasks:
        if t.elapsed > 0:
            last = round((3600*(t.bonus+BASE_PAY))/t.elapsed,2)
            if last > prev:
                upside = True
            else:
                upside = False
            prev = last
            data.append(last)
    if len(data) >0 :
        avg_data= round(sum(data)/len(data),2)
        max_data = round(max(data))
    data = data[-100:]
    # print data
    data = ','.join([str(item) for item in data])
    # print data

    if assignmentId == "ASSIGNMENT_ID_NOT_AVAILABLE":
        return render_to_response('accept.html', {'user_profile':user_profile, 'data': data, 
            'last': last, 'max': max_data, 'avg':avg_data, 'upside': upside}, context_instance=RequestContext(request))

    # get the task
    from django.db import IntegrityError
    task = get_object_or_404(Task, pk=task_id)
    try: 
        assigned, created= TaskSubmit.objects.get_or_create(user=request.user,task=task, elapsed=0)
    except IntegrityError as e:
        return render_to_response('done.html', {'user_profile':user_profile, 'data': data, 
            'last': last, 'max': max_data, 'avg':avg_data, 'upside': upside}, context_instance=RequestContext(request))

    ## Run some model and assign the bonus !!
    # 1) do it constant :
    print assigned, assigned.id
    bonus = 0.01
    assigned.bonus = bonus
    assigned.save()
    print "assigned price:", assigned.bonus

    # Generate the next task and send it to the work:
    if batch.bclass == "imgcompare":
        img1, img2 = task.question.split(',')
        return render_to_response('celebrities.html', {'user_profile':user_profile,'task':task, 'img1':img1, 'img2': img2, 'bonus': bonus,
                'data': data, 'last': last, 'max': max_data, 'avg':avg_data, 'upside': upside, 'batch':batch},
                    context_instance=RequestContext(request))
    elif batch.bclass == "imgcompare_multi":
        print task.id, "!!!!!!", task.question
        # items = ast.literal_eval(task.question)
        items = task.question.split(',');
        print "Items Set: ", items
        item = items[0]
        items = items[1:]
        return render_to_response('celebrities_multi.html', {'user_profile':user_profile, 'task':task, 'item':item, 'items':items, 'bonus': bonus,
            'data': data, 'last': last, 'max': max_data, 'avg':avg_data, 'upside': upside, 'batch':batch}, 
            context_instance=RequestContext(request))
    elif batch.bclass == "er_multi":
        print task.id, "!!!!!!", task.question
        items = ast.literal_eval(task.question)
        print "Items Set: ", items
        item = items[0]
        items = items[1:]
        return render_to_response('er.html', {'user_profile':user_profile, 'task':task, 'item':item, 'items':items, 'bonus': bonus,
            'data': data, 'last': last, 'max': max_data, 'avg':avg_data, 'upside': upside, 'batch':batch}, 
            context_instance=RequestContext(request))
    elif batch.bclass == "data":
        return render_to_response('task.html', {'user_profile':user_profile, 'task':task, 'bonus': bonus,  
            'data': data, 'last': last, 'max': max_data, 'avg':avg_data, 'upside': upside, 'batch':batch}, 
            context_instance=RequestContext(request))
    else:
        return render_to_response('error.html', {'user_profile':user_profile}, context_instance=RequestContext(request))


# some actions
from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
@login_required
def submit(request, task_id):
    print "submitting !!!!!!"
    task = get_object_or_404(Task, pk=task_id)

    from django.core.exceptions import MultipleObjectsReturned
    print "submit" , task, task.id
    try:
        tasksubmit = TaskSubmit.objects.get(user=request.user,task=task)
    except TaskSubmit.DoesNotExist:
        # In case the person stayed too long and got dismissed
        return render_to_response('error.html', {'user_profile':user_profile}, context_instance=RequestContext(request))
    except MultipleObjectsReturned:
        tasksubmit = TaskSubmit.objects.filter(user=request.user,task=task)[0]
    tasksubmit.submittime = datetime.utcnow().replace(tzinfo=utc)
    start = tasksubmit.starttime
    end = tasksubmit.submittime
    print start
    print end
    tasksubmit.elapsed = (end-start).seconds+((end-start).microseconds/1e6)
    tasksubmit.save()
    user_profile = UserProfile.objects.get(user=request.user)
    user_profile.credit = user_profile.credit + tasksubmit.bonus
    user_profile.save()
    return HttpResponse('', mimetype="application/javascript")

def welcome(request):
    return render_to_response('welcome.html', context_instance=RequestContext(request))
