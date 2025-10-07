import store_db, pprint
l, ts = store_db.load_list("merged")
print("merged count", len(l), "updated_ts", ts)
pprint.pprint(l[:5])
