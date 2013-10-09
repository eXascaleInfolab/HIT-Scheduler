from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader
from django.shortcuts import render_to_response, get_object_or_404, redirect, render
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from accounts.models import UserProfile, Batch, Task, TaskLock, TaskAnswer, TaskSkip, FormWithCaptcha, BatchSkip
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

import warnings
warnings.showwarning = lambda *x: None

# Common utilities
def TaskCount():
    return Task.objects.all().count()

def TaskFilter(user):
    myDoneTasks = TaskAnswer.objects.filter(user=user).values_list('task', flat=True)
    mySkipTasks = TaskSkip.objects.filter(user=user).values_list('task', flat=True)
    doneOrLockedTasks = Task.objects.filter(lock=0, done=3).values_list('id', flat=True)
    print "SKIPPING TASK:", set(myDoneTasks) | set(mySkipTasks) | set(doneOrLockedTasks)
    return set(myDoneTasks) | set(mySkipTasks) | set(doneOrLockedTasks)

def BatchFilter(user, taskExclude):
    myRemainingBatchs = Task.objects.exclude(id__in=taskExclude).values_list('batch', flat=True)
    mySkipBatchs = BatchSkip.objects.filter(user=user).values_list('batch', flat=True)
    SelectableBatchs = Batch.objects.exclude(id__in=mySkipBatchs)
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
def getNextBatch_FAIR(user, taskExclude):
    SelectableBatchs = BatchFilter(user, taskExclude)
    if SelectableBatchs.count() == 0:
        return 0
    batch = SelectableBatchs.extra(select={'score': "runtask/value"}).order_by('score')[0]
    if batch.bclass == "collab":
        print "##################"
        print "THE TIME HAS COME"
        work.todo = Task.objects.get(batch=batch)
        print work.todo
        print "##################"
    else:
        return batch
    if SelectableBatchs.count() == 1:
        return 0
    return SelectableBatchs.extra(select={'score': "runtask/value"}).order_by('score')[1]

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
            if tup[x+2][1] - tup[x][1] < timedelta(seconds=100):
                for i in range(x,x+3):
                    workers.append(tup[i][0])
                break
    return workers


# Core method
@login_required
@transaction.commit_on_success
def work(request):
    print 'work ------------------------------------------'
    lock = DjangoLock('/tmp/djangolock.tmp')
    lock.acquire()
    try:
        if Batch.objects.filter(done=True).count() == Batch.objects.all().count():
            code = id_generator()
            print "CODE !", code
            return render_to_response('done.html', {'code': code},
                context_instance=RequestContext(request))
        release_expiredLocks() # Too heavy, but that's ok for now (run using celery ?)
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            print user_profile.credit, user_profile.user.username
        except UserProfile.DoesNotExist:
            return HttpResponseRedirect(reverse('login_view'))
        # TODO: move this after schedule the next betch
        count = num_visitors(request)
        print datetime.now(), "NUMBER of visitors:",count

        batches = Batch.objects.all()
        work_start = batches[0].experiment_started
        print "WORK STARTED?:", work_start
        # 1 Check if work started :)
        if not work_start:
            if count < settings.CONCURENT_WORKERS:
                form = FormWithCaptcha()
                return render_to_response('captcha.html',
                    {'user_profile':user_profile, 'count':count, 'form': form},
                    context_instance=RequestContext(request))
            else:
                print datetime.now(), "SYSTEM START"
                for batch in Batch.objects.all():
                    batch.pulication = datetime.utcnow().replace(tzinfo=utc)
                    batch.experiment_started = True
                    batch.save()

        # Check if the user isn't locking some task
        task_lock_count = TaskLock.objects.filter(user=request.user).count()
        print "NUM LOCKS:", task_lock_count
        user_id = request.user.id
        if task_lock_count == 0:
            # No Lock ... Schedule the next batch
            taskExclude = TaskFilter(request.user)
            ganged = Batch.objects.get(id=10).done
            if user_id in work.workers and not ganged:
                print "workers !" , work.todo
                work.workers.remove(user_id)
                batch=Batch.objects.get(id=10)
                task = Task.objects.get(id=1000)
            else:
                batch = getNextBatch_FAIR(request.user, taskExclude)
                if batch == 0:
                    print "Experiment Finished!"
                    code = id_generator()
                    print "CODE !", code
                    return render_to_response('done.html',
                        {'user_profile':user_profile, 'code':code},
                        context_instance=RequestContext(request))
                print "Batch Selected: ", batch
                # Take some care of real locks !
                tasks = Task.objects.filter(batch=batch, lock__gt=0, done__lt=batch.repetition).exclude(id__in=taskExclude).order_by('?')
                if tasks.count() == 0:
                    # return HttpResponseRedirect(reverse('work'))
                    form = FormWithCaptcha()
                    return render_to_response('captcha.html',
                        {'user_profile':user_profile, 'count':count, 'form': form},
                        context_instance=RequestContext(request))
                else:
                    task = tasks[0]
            task.lock = task.lock - 1
            task.save()
            batch.runtask = batch.runtask + 1
            batch.save()
        else:
            task_lock = TaskLock.objects.get(user=request.user)
            task = task_lock.task
            batch = task.batch
        print "LOCK: ", request.user, task
        tlock, created = TaskLock.objects.get_or_create(user=request.user,task=task)
        tlock.save()
        if len(work.workers) == 0:
            work.workers = gang()
        print work.workers
        img = False
        if task.question[-4:].lower() in ['.jpg', '.png', '.gif', '.jpeg']:
            img = True
        choices = task.choice.split(',')
        doc = False
        if batch.bclass == "collab":
            doc = task.question
        completed = (len(TaskFilter(request.user)))/Decimal(TaskCount()) * 100;
        return render_to_response('task.html', {'user_profile':user_profile, 'completed': completed ,'task':task, 'batch': batch, 'img': img, 'choice': len(choices) > 1, 'choices': choices, 'doc':doc},
                context_instance=RequestContext(request))
    finally:
        lock.release()
work.workers = []
work.todo = None

@login_required
def click(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    if request.POST:
        if 'skip' in request.POST:
            return doSkip(request, task)
        elif 'skipbatch' in request.POST:
            return doSkipBatch(request, task)
        elif 'submit' in request.POST:
            return doSubmit(request, task)

@login_required
def doSubmit(request, task):
    if not request.POST['answer'].strip():
        return doSkip(request, task)
    lock = DjangoLock('/tmp/djangolock.tmp')
    lock.acquire()
    try:
        try:
            tl = TaskLock.objects.get(user=request.user,task=task)
        except TaskLock.DoesNotExist:
            # In case the person stayed too long and got dismissed
            return HttpResponseRedirect(reverse('work'))
        user_profile = UserProfile.objects.get(user=request.user)
        print 'SUBMIT TASK ------------------------------------------'
        task.done = task.done + 1
        task.save()
        # Assuming he answered correctly .. give him money !
        user_profile.credit = user_profile.credit + task.batch.value
        user_profile.save()
        # first measure elapsed time ..
        start = tl.starttime
        end = datetime.utcnow().replace(tzinfo=utc)
        elapsed = (end - start).seconds
        answer = TaskAnswer.objects.create(user=request.user,task=task, answer=request.POST['answer'],assign=tl.starttime,elapsed=elapsed)
        tl.delete()
        batch = task.batch
        batch.runtask = batch.runtask - 1
        batch.save()
        fct = batch.numtask * batch.repetition
        d = Task.objects.filter(batch=batch).aggregate(Sum('done'))
        d = d['done__sum']
        print "#### fact: ", fct, d
        if  d >= fct:
            print "aww !",  d, fct
            batch.done = True
            batch.finishtime = datetime.utcnow().replace(tzinfo=utc)
            batch.save()
        return HttpResponseRedirect(reverse('work'))
        # return work(request)
    finally:
        lock.release()

@login_required
def doSkip(request, task):
    lock = DjangoLock('/tmp/djangolock.tmp')
    lock.acquire()
    try:
        print 'SKIP TASK ------------------------------------------'
        try:
            tl = TaskLock.objects.get(user=request.user,task=task)
        except TaskLock.DoesNotExist:
            # In case the person stayed too long and got dismissed
            return HttpResponseRedirect(reverse('work'))
        task.lock = task.lock + 1
        task.save()
        # first measure elapsed time ..
        start = tl.starttime
        end = datetime.utcnow().replace(tzinfo=utc)
        elapsed = (end - start).seconds
        skip = TaskSkip.objects.create(user=request.user,task=task,assign=tl.starttime,elapsed=elapsed)
        tl.delete()
        batch = task.batch
        batch.runtask = batch.runtask - 1
        batch.save()
        return HttpResponseRedirect(reverse('work'))
    finally:
        lock.release()

@login_required
def doSkipBatch(request, task):
    lock = DjangoLock('/tmp/djangolock.tmp')
    lock.acquire()
    try:
        print 'SKIP BATCH ------------------------------------------'
        task.lock = task.lock + 1
        task.save()
        skip = BatchSkip.objects.create(user=request.user,batch=task.batch)
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
    return Visitor.objects.active().exclude(user=None).count()

@transaction.commit_manually
def release_expiredLocks():
    print "Release expired locks"
    tlocks = TaskLock.objects.all()
    for tl in tlocks:
        visits = Visitor.objects.active().filter(user=tl.user).count()
        if visits == 0 :
            sid = transaction.savepoint()
            task = tl.task
            batch = task.batch
            task.lock = task.lock + 1
            task.save()
            batch.runtask = batch.runtask - 1
            batch.save()
            tl.delete()
            visits = Visitor.objects.active().filter(user=tl.user).count()
            if visits == 0 :
                print "CLEAN LOCKS FROM USER ::: " , tl.user
                transaction.savepoint_commit(sid)
            else:
                print "DON'T CLEAN LOCKS FROM USER ::: " , tl.user
                transaction.savepoint_rollback(sid)
    transaction.commit()

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
