import time
from subprocess import call

f = open("scripts/trace.txt", "r")
cnt = 1
for line in f.readlines():
	# run the command
	call(["heroku run python manage.py loaddata short_fixtures/b"+str(cnt)+".json"],shell=True)
	cnt = cnt + 1
	s = int(line.strip())
	print "sleeping", s
	# sleep for the next one
	time.sleep(s)
	
f.close()
