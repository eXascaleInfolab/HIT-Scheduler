from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader
from django.shortcuts import render_to_response, get_object_or_404, redirect, render
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from accounts.models import UserProfile, Batch, Task
from accounts.views import login_view
from django.contrib.sessions.models import Session
from datetime import datetime, timedelta
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

import warnings
warnings.showwarning = lambda *x: None

# Common utilities
def getTask(batch):
    return Task.objects.filter(batch=batch).order_by('?')[0]

def remainingBatchs():
    batches = Batch.objects.exclude(id=100)  # special case
    return batches.filter(numtask__gt=F('done')) 

def TaskCount():
    return Task.objects.all().count()

def BatchFilter(user, taskExclude):
    myRemainingBatchs = Task.objects.exclude(id__in=taskExclude).values_list('batch', flat=True)
    SelectableBatchs = SelectableBatchs.filter(id__in=myRemainingBatchs, done=False)
    print "SELECTING ONLY FROM BATCHS:", SelectableBatchs
    return SelectableBatchs

# FIFO
def getNextBatch_FIFO(user, taskExclude):
    SelectableBatchs = BatchFilter(user, taskExclude)
    if SelectableBatchs.count() == 0:
        return 0
    return SelectableBatchs.order_by('batch_id')[0]

# Earliest Deadline First
def getNextBatch_EDF(user, taskExclude):
    SelectableBatchs = BatchFilter(user, taskExclude)
    if SelectableBatchs.count() == 0:
        return 0
    return SelectableBatchs.order_by('deadline')[0]

# Round-Robin
def getNextBatch_RR(user, taskExclude):
    SelectableBatchs = BatchFilter(user, taskExclude)
    if SelectableBatchs.count() == 0:
        return 0
    it = (getNextBatch_RR.item) % SelectableBatchs.count()
    getNextBatch_RR.item = getNextBatch_RR.item + 1
    return SelectableBatchs[it]
getNextBatch_RR.item = 0

# Weighted Fair Scheduling
def getNextBatch_FAIR(user):
    SelectableBatchs = remainingBatchs()
    if SelectableBatchs.count() == 0:
        return Batch.objects.get(id=100)
    batch = SelectableBatchs.extra(select={'score': "runtask/value"}).order_by('score')[0]
    return batch
    

# Weighted Fair Scheduling
def getNextBatch_Delay_FAIR(user):
    SelectableBatchs = remainingBatchs()
    if SelectableBatchs.count() == 0:
        return Batch.objects.get(id=100)
    batches = SelectableBatchs.extra(select={'score': "runtask/value"}).order_by('score')
    print batches
    for batch in batches:
        print batch.id
        if user.lastbatch == None:
            print "Virgin User"
            batch.repetition = 3
            batch.save()
            return batch
        if batch == user.lastbatch:
            print "Matched User"
            return batch
        elif batch.repetition > 0:
            print "Batch Giving up its priority"
            batch.repetition = batch.repetition - 1
            batch.save()
            continue
        else:
            print "Batch reaches give-up limit"
            batch.repetition = 3
            batch.save()
            return  batch

# Gang
def gang():
    est = {}
    locks = TaskLock.objects.all()
    for lock in locks:
        task = Task.objects.get(id=lock.task_id)
        tb= Task.objects.filter(batch_id=task.batch_id)
        avg = TaskAnswer.objects.filter(user_id=lock.user_id,task__in=tb).aggregate(Avg('elapsed'))['elapsed__avg']
        if avg:
            estimate = lock.starttime + timedelta(seconds=avg)
            est[lock.user_id] =  estimate
    tup = sorted(est.items(), key=lambda x:x[1])
    print tup
    workers=[]
    if len(tup) >= 3:
        for x in range(0,len(tup)-2):
            print "###### TIME INTERVAL:  ", tup[x+2][1] - tup[x][1]
            if tup[x+2][1] - tup[x][1] < timedelta(seconds=10):
                for i in range(x,x+3):
                    workers.append(tup[i][0])
                break
    return workers

# Core method
def work(request, task_id):
    print "New HIT Request ................."
    # Some user management with mturk
    workerId = request.GET.get('workerId')
    assignmentId = request.GET.get('assignmentId')
    
    # Assignement Id not available
    if assignmentId == "ASSIGNMENT_ID_NOT_AVAILABLE":
        return render_to_response('accept.html', {'user_profile':user_profile, 'data': data, 'batch': batch,
            'last': last, 'max': max_data, 'avg':avg_data, 'upside': upside}, context_instance=RequestContext(request))

    # User management
    if request.user.is_authenticated() == False:
        if workerId != None:
            print "new with id ", workerId
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
            print "new without id"
            return render_to_response('welcome.html', context_instance=RequestContext(request))
    else: 
        print "super, user is back: ", request.user

    print "super, user is here: ", request.user
    # get the user profile
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        print user_profile.credit, user_profile.user.username
    except UserProfile.DoesNotExist:
        return HttpResponseRedirect(reverse('login_view'))
    
    # ok, this is not really needed
    if task_id == None:
        return render_to_response('error.html', context_instance=RequestContext(request))

    # Schedule the next batch and get the task
    batch = getNextBatch_Delay_FAIR(user_profile)
    print "Selected Batch:", batch.id
    task = getTask(batch)
    print "Selected Task:", task.id
    user_profile.lastbatch = batch
    user_profile.save()


    # Create the Task Interface
    if batch.bclass == "classify":
        batch.runtask = batch.runtask + 1
        batch.save()
        return render_to_response('flies.html', {'user_profile':user_profile, 'task':task, 'batch':batch}, 
            context_instance=RequestContext(request))
    if batch.bclass == "er_multi":
        batch.runtask = batch.runtask + 1
        batch.save()
        items = ast.literal_eval(task.question)
        item = items[0]
        items = items[1:]
        return render_to_response('er.html', {'task':task, 'batch':batch, 'item':item, 'items':items}, 
            context_instance=RequestContext(request))
    if batch.bclass == "data":
        batch.runtask = batch.runtask + 1
        batch.save()
        return render_to_response('spell.html', {'user_profile':user_profile, 'task':task, 'batch':batch}, 
            context_instance=RequestContext(request))
    if batch.bclass == "sentiment":
        batch.runtask = batch.runtask + 1
        batch.save()
        return render_to_response('sentiment.html', {'user_profile':user_profile, 'task':task, 'batch':batch}, 
            context_instance=RequestContext(request))
    if batch.bclass == "tag":
        batch.runtask = batch.runtask + 1
        batch.save()
        return render_to_response('tag.html', {'user_profile':user_profile, 'task':task, 'batch':batch}, 
            context_instance=RequestContext(request))
    else:
        return render_to_response('error.html', {'user_profile':user_profile}, context_instance=RequestContext(request))


# some actions
from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
@login_required
def submit(request, batch_id):
    batch = get_object_or_404(Batch, pk=batch_id)
    print "User: ", request.user, "Submitted: " , batch
    batch.done = batch.done + 1
    batch.runtask = batch.runtask - 1
    batch.save()
    return HttpResponse('', mimetype="application/javascript")

def welcome(request):
    print "welcome page! .. someone is lurking"
    return render_to_response('welcome.html', {}, context_instance=RequestContext(request))
