import datetime
from django.db import models
from django.contrib.auth.models import User
from django.core.cache import cache
from django.conf import settings
from django import forms
from captcha.fields import ReCaptchaField

class UserProfile(models.Model):
	user = models.ForeignKey(User, unique=True)
	mturkid = models.CharField(max_length=200)
	credit = models.IntegerField(default=0)
	score = models.IntegerField(default=0)

class Batch(models.Model):
	value = models.IntegerField(default=1)
	repetition = models.IntegerField(default=3)
	numtask = models.IntegerField()
	runtask = models.IntegerField(default=0)
	done = models.BooleanField(default=False)
	pulication = models.DateTimeField(auto_now_add=True)
	deadline = models.DateTimeField(auto_now=True)
	finishtime = models.DateTimeField(blank=True,null=True)
	name = models.CharField(max_length=50)
	bclass = models.CharField(max_length=10, choices=(('classify','classify'),('extract','extract'),('curate','curate'),('data','data')))
	def __unicode__(self):
		return self.name

class Task(models.Model):
	batch = models.ForeignKey(Batch)
	question = models.CharField(max_length=500,blank=False)
	choice = models.CharField(max_length=500,blank=True)
	lock = models.IntegerField(default=3)
	done = models.IntegerField(default=0)
	def __unicode__(self):
		return self.question

class TaskLock(models.Model):
	user = models.ForeignKey(User)
	task = models.ForeignKey(Task)
	class Meta:
		unique_together = ['user', 'task']

class TaskAnswer(models.Model):
	user = models.ForeignKey(User)
	task = models.ForeignKey(Task)
	answer = models.CharField(max_length=500)
	class Meta:
		unique_together = ['user', 'task']

class TaskSkip(models.Model):
	user = models.ForeignKey(User)
	task = models.ForeignKey(Task)
	class Meta:
		unique_together = ['user', 'task']

class FormWithCaptcha(forms.Form):
	captcha = ReCaptchaField()