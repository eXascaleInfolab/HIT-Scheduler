from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader
from django.shortcuts import render_to_response, get_object_or_404, redirect, render
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from accounts.models import UserProfile, Batch, Task, TaskLock, TaskAnswer, TaskSkip, FormWithCaptcha
from django.contrib.sessions.models import Session
from datetime import datetime
from tracking.models import Visitor
from django.db import transaction
from django.db.models import Sum, F
import random
import string
import os
import fcntl
from django.core.files import locks

# Common utilities
def TaskFilter(request):
    myDoneTasks = TaskAnswer.objects.filter(user=request.user).values_list('task', flat=True)
    mySkipTasks = TaskSkip.objects.filter(user=request.user).values_list('task', flat=True)
    return set(myDoneTasks) | set(mySkipTasks)

def BatchFilter(request):
    taskExclude = TaskFilter(request)
    myRemainingBatchs = Task.objects.exclude(id__in=taskExclude).values_list('batch', flat=True)
    SelectableBatchs = Batch.objects.filter(id__in=myRemainingBatchs, done=False, runtask__lt=F('numtask'))
    return SelectableBatchs

# FIFO
def getNextBatch_FIFO(request):
    SelectableBatchs = BatchFilter(request)
    if SelectableBatchs.count() == 0:
        return 0
    return SelectableBatchs.order_by('pulication')[0]

# Earliest Deadline First
def getNextBatch_EDF(request):
    SelectableBatchs = BatchFilter(request)
    if SelectableBatchs.count() == 0:
        return 0
    return SelectableBatchs.order_by('deadline')[0]

# Round-Robin
def getNextBatch_RR(request):
    SelectableBatchs = BatchFilter(request)
    if SelectableBatchs.count() == 0:
        return 0
    it = (getNextBatch_RR.item) % SelectableBatchs.count()
    getNextBatch_RR.item = getNextBatch_RR.item + 1
    return SelectableBatchs[it]
getNextBatch_RR.item = 0

# Weighted Fair Scheduling
def getNextBatch_FAIR(request):
    SelectableBatchs = BatchFilter(request)
    if SelectableBatchs.count() == 0:
        return 0
    return SelectableBatchs.extra(select={'score': "runtask/value"}).order_by('score')[0]

# Core method
@login_required
def work(request):
    lock = DjangoLock('/tmp/djangolock.tmp')
    lock.acquire()
    try:
        print "work"
        release_expiredLocks() # Too heavy, but that's ok for now (run using celery ?)
        user_profile = UserProfile.objects.get(user=request.user)
        print user_profile.credit, user_profile.user.username
        # TODO: move this after schedule the next betch
        count = num_visitors(request)
        print count, " NUMBER of visitors ...."
        if count < 3:
            form = FormWithCaptcha()
            return render_to_response('captcha.html',
                {'user_profile':user_profile,'form': form},
                context_instance=RequestContext(request))
        # Check if the user isn't locking some task
        try:
            task_lock = TaskLock.objects.get(user=request.user)
        except TaskLock.DoesNotExist:
            # Schedule the next batch
            batch = getNextBatch_FAIR(request)
            if batch == 0:
                return render_to_response('done.html',
                    {'user_profile':user_profile,},
                    context_instance=RequestContext(request))
            print "Batch Selected: ", batch
            # Take some care of real locks !
            taskExclude = TaskFilter(request)
            print taskExclude
            tasks = Task.objects.filter(batch=batch, lock__gt=0, done__lt=batch.repetition).exclude(id__in=taskExclude)
            task = tasks[0]
            task.lock = task.lock - 1
            task.save()
            batch.runtask = batch.runtask +1
            batch.save()
        else:
            task = task_lock.task
            batch = task.batch
        print "LOCK: ", request.user, task
        tlock, created = TaskLock.objects.get_or_create(user=request.user,task=task)
        tlock.save()
        img = False
        if task.question[-4:].lower() in ['.jpg', '.png', '.gif', '.jpeg']:
            img = True
        return render_to_response('task.html', {'user_profile':user_profile,'task':task, 'batch': batch, 'img': img},
                context_instance=RequestContext(request))
    finally:
        lock.release()

@login_required
def click(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    if request.POST:
        if 'submit' in request.POST:
            return doSubmit(request, task)
        elif 'skip' in request.POST:
            return doSkip(request, task)

@login_required
def doSubmit(request, task):
    lock = DjangoLock('/tmp/djangolock.tmp')
    lock.acquire()
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        print 'submit ---------------------'
        task.done = task.done +1
        task.save()
        answer = TaskAnswer.objects.create(user=request.user,task=task)
        # Assuming he answered correctly .. give him money !
        user_profile.credit = user_profile.credit + task.batch.value
        user_profile.save()
        tl = TaskLock.objects.filter(user=request.user,task=task)
        tl.delete()
        batch = task.batch
        batch.runtask = batch.runtask -1
        batch.save()
        fct = batch.numtask * batch.repetition
        d = Task.objects.filter(batch=batch).aggregate(Sum('done'))
        d = d['done__sum']
        print " #### fact: ", fct, d
        if  d >= fct:
            print "aww !",  d, fct
            batch.done = True
            batch.finishtime = datetime.now()
            batch.save()
        return HttpResponseRedirect(reverse('work'))
    finally:
        lock.release()

@login_required
def doSkip(request, task):
    lock = DjangoLock('/tmp/djangolock.tmp')
    lock.acquire()
    try:
        print 'skip ---------------------'
        task.lock = task.lock + 1
        task.save()
        skip = TaskSkip.objects.create(user=request.user,task=task)
        tl = TaskLock.objects.filter(user=request.user,task=task)
        tl.delete()
        batch = task.batch
        batch.runtask = batch.runtask - 1
        batch.save()
        return HttpResponseRedirect(reverse('work'))
    finally:
        lock.release()

@login_required
def doCaptcha(request):
    user_profile = UserProfile.objects.get(user=request.user)
    if request.method == 'POST':
        form=FormWithCaptcha(request.POST)
        print "I received the form", form.is_valid()
        if form.is_valid():
            print "is VALID CAPTCHA"
            user_profile.credit = user_profile.credit + 0.01
            user_profile.save()
    else:
        form = FormWithCaptcha()
    return HttpResponseRedirect(reverse('work'))

# Session management
def num_visitors(request):
    return Visitor.objects.active().count()

def release_expiredLocks():
    print "release expired locks"
    tlocks = TaskLock.objects.all()
    for tl in tlocks:
        try:
            Visitor.objects.get(user=tl.user)
        except Visitor.DoesNotExist:
            print tl.user, "REMOVE LOCKS"
            task = tl.task
            batch = task.batch
            task.lock = task.lock + 1
            task.save()
            batch.runtask = batch.runtask - 1
            batch.save()
            tl.delete()

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


class DjangoLock:
 
    def __init__(self, filename):
        self.filename = filename
        # This will create it if it does not exist already
        self.handle = open(filename, 'w')
 
    # flock() is a blocking call unless it is bitwise ORed with LOCK_NB to avoid blocking
    # on lock acquisition.  This blocking is what I use to provide atomicity across forked
    # Django processes since native python locks and semaphores only work at the thread level
    def acquire(self):
        fcntl.flock(self.handle, fcntl.LOCK_EX)
 
    def release(self):
        fcntl.flock(self.handle, fcntl.LOCK_UN)
 
    def __del__(self):
        self.handle.close()
