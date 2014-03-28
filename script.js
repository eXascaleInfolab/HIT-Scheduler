var cur = db.getCollection("group").find({},{'requester_id': 1, 'requester_name': 1, '_id':0});
while (cur.hasNext()) { var doc = cur.next(); printjson(doc); }
