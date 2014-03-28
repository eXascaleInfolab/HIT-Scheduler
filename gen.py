#!/usr/bin/python
import random
from random import shuffle
a= []
to= range(1,26)
for x in range(1,26):
    random.shuffle(to)
    for y in to:
        a.append((x,y))
#random.shuffle(a)
print a
pk = 1 
for t in a:
    fr, to = t 
    print """
      {
        "pk": %s,
        "model": "accounts.task",
        "fields": {
          "batch": 1,
          "question": "data/celebrities/%s.jpg,data/celebrities/%s_1.jpg",
          "choice": "yes, no"
        }
      },""" % (pk, fr, to)
    pk = pk + 1 
