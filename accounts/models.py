from django.db import models
from django.contrib.auth.models import User
from django import forms
from captcha.fields import ReCaptchaField

class UserProfile(models.Model):
	user = models.ForeignKey(User, unique=True)
	credit = models.FloatField(default=0.0)
	score = models.IntegerField(default=0)

class Batch(models.Model):
	experiment_started = models.BooleanField(default=False)
	value = models.FloatField(default=0.01)
	repetition = models.IntegerField(default=3)
	numtask = models.IntegerField()
	runtask = models.IntegerField(default=0)
	done = models.BooleanField(default=False)
	pulication = models.DateTimeField(auto_now_add=True)
	deadline = models.DateTimeField(auto_now=True)
	finishtime = models.DateTimeField(blank=True,null=True)
	name = models.CharField(max_length=50)
	description = models.CharField(max_length=255)
	bclass = models.CharField(max_length=10, choices=(('classify','classify'),('extract','extract'),('curate','curate'),('data','data'),('study','study'),('collab','collab')))
	def __unicode__(self):
		return self.name

class Task(models.Model):
	batch = models.ForeignKey(Batch)
	question = models.TextField(max_length=500,blank=False)
	choice = models.TextField(blank=True)
	lock = models.IntegerField(default=3)
	done = models.IntegerField(default=0)
	def __unicode__(self):
		return self.question

class TaskLock(models.Model):
	user = models.ForeignKey(User)
	task = models.ForeignKey(Task)
	starttime = models.DateTimeField(auto_now=True)
	class Meta:
		unique_together = ['user', 'task']

class TaskAnswer(models.Model):
	user = models.ForeignKey(User)
	task = models.ForeignKey(Task)
	answer = models.TextField(blank=True)
	elapsed = models.IntegerField(default=0)
	class Meta:
		unique_together = ['user', 'task']

class TaskSkip(models.Model):
	user = models.ForeignKey(User)
	task = models.ForeignKey(Task)
	elapsed = models.IntegerField(default=0)
	class Meta:
		unique_together = ['user', 'task']

class BatchSkip(models.Model):
	user = models.ForeignKey(User)
	batch = models.ForeignKey(Batch)
	class Meta:
		unique_together = ['user', 'batch']

class FormWithCaptcha(forms.Form):
	captcha = ReCaptchaField()
