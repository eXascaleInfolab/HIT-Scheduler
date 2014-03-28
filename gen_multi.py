#!/usr/bin/python
import random
from random import shuffle
a= []
to= range(1,26)
for x in range(1,26):
    random.shuffle(to)
    for y in range(0,5):
	sub_to = to[(y*5):(y*5+5)]
	print sub_to
        a.append((x,sub_to))
#random.shuffle(a)
print a
pk = 626 
for t in a:
    fr, to = t 
    q,w,e,r,t = to
    print """
      {
        "pk": %s,
        "model": "accounts.task",
        "fields": {
          "batch": 2,
          "question": "data/celebrities/%s.jpg,data/celebrities/%s_1.jpg,data/celebrities/%s_1.jpg,data/celebrities/%s_1.jpg,data/celebrities/%s_1.jpg,data/celebrities/%s_1.jpg",
          "choice": "yes, no"
        }
      },""" % (pk, fr, q,w,e,r,t)
    pk = pk + 1 
