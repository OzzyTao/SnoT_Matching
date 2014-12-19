import psycopg2

import sys
import pickle

# read experiment instances from database
sys.path.append('F:/London/Case 1 and 2 programs')
from sta import Test 

binarypath="F:/London/statistics2/"
binaryfiles = ['30seconds101test.p','60seconds101test.p','90seconds101test.p','120seconds101test.p','150seconds127test.p','180seconds109test.p']
groupname = ['30','60','90','120','150','180']

groups ={}
for typeid in range(6):
	with open(binarypath+binaryfiles[typeid],'rb') as binary:
		group=pickle.load(binary)
		groups[groupname[typeid]] = group[:100]
print 'data loaded'

conn = psycopg2.connect("dbname=gis user=postgres password=peach")
cur = conn.cursor()

addrow_query = "INSERT INTO testcases(time_slot, start_num, end_num, measurements) VALUES (%s, %s, %s, %s)"

for name in groupname:
	for test in groups[name]:
		time_slot = int(name)
		measurementsstr = "{%s}" % (','.join([str(x) for x in test.test_para['measurements']]),)
		cur.execute(addrow_query, (time_slot, test.test_para['measurements'][0], test.test_para['measurements'][-1], measurementsstr))
# name = groupname[-1]
# for test in groups[name]:
# 	time_slot = int(name)
# 	measurementsstr = "{%s}" % (','.join([str(x) for x in test.test_para['measurements']]),)
# 	cur.execute(addrow_query, (time_slot, test.test_para['measurements'][0], test.test_para['measurements'][-1], measurementsstr))
cur.execute("select * from testcases;")
print cur.fetchone()

conn.commit()
cur.close()
conn.close()
			 