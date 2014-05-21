from django.db import models
from django.contrib.auth.models import User


class Batch(models.Model):
	experiment_started = models.BooleanField(default=False)
	value = models.FloatField(default=0.01)
	repetition = models.IntegerField(default=3)
	numtask = models.IntegerField()
	runtask = models.IntegerField(default=0)
	done = models.IntegerField(default=0)
	pulication = models.DateTimeField(auto_now_add=True)
	deadline = models.DateTimeField(auto_now=True)
	finishtime = models.DateTimeField(blank=True,null=True)
	name = models.CharField(max_length=50)
	description = models.CharField(max_length=255)
	bclass = models.CharField(max_length=20, choices=(('sentiment','sentiment'),('classify','classify'),('tag','tag'),('curate','curate'),('data','data'),('study','study'),('collab','collab'), ('imgcompare','imgcompare'), ('imgcompare_multi','imgcompare_multi'),('er_multi','er_multi')))
	def __unicode__(self):
		return self.name

class UserProfile(models.Model):
	user = models.ForeignKey(User, unique=True)
	credit = models.FloatField(default=0.0)
	score = models.IntegerField(default=0)
	lastbatch = models.ForeignKey(Batch, null=True, blank=True, default = None) 

class Task(models.Model):
	batch = models.ForeignKey(Batch)
	question = models.TextField(max_length=500,blank=False)
	choice = models.TextField(blank=True)
	def __unicode__(self):
		return self.question

class TaskSubmit(models.Model):
	user = models.ForeignKey(User)
	task = models.ForeignKey(Task)
	starttime = models.DateTimeField(auto_now_add=True)
	submittime = models.DateTimeField(blank=True,null=True)
	elapsed = models.FloatField(blank=True,null=True)
	bonus = models.FloatField(default=0.01)
	class Meta:
		unique_together = ['user', 'task']