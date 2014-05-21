import random
l = float(1/float(128))
print "Lambda", l
count= 0
for i in range(1,29):
	a= random.expovariate(l)
	count = count + a
	print a
print "Total", count
