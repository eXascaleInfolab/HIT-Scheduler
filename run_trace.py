import time
from subprocess import call
import os,sys

f = open("scripts/trace.txt", "r")
cnt = 1
for line in f.readlines():
	# run the command
	print 'Executing', cnt
	call(["heroku run python manage.py loaddata short_fixtures/b"+str(cnt)+".json"],shell=True)
	print('\a')
	cnt = cnt + 1
	s = int(line.strip())
	print "sleeping", s
	# sleep for the next one
	#time.sleep(s)
	
f.close()
