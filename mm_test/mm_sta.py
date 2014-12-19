import sys
sys.path.append('F:/London/Case 1 and 2 programs')
from sta import Test
import pickle
import csv
path = 'f:/London/statistics_speed/'
# names = ['TRMSE','area','CLength']
# # normalized indices: top ranked value against the worest_value
# fields = ['30s','60s','90s','120s','150s','180s'] 
times = [30,60,90,120,150,180]
binaryfiles = ['30seconds82test.p','60seconds74test.p','90seconds76test.p','120seconds81test.p','150seconds74test.p','180seconds69test.p']
typetest = []
for file in binaryfiles:
	with open(path+file,'rb') as binary:
		typetest.append(pickle.load(binary))

# # correlation
names = ['TRMSE_corr','area_corr','CLength_corr','TRMSE_Rank_corr','area_Rank_corr','CLength_Rank_corr']
with open(path+'corr/corr_edges.csv','wb') as csvfile:
	mywriter = csv.DictWriter(csvfile,delimiter=',',fieldnames=['id','time','edges','routes','speed']+names)
	mywriter.writeheader()
	for i in range(len(times)):
		tests=typetest[i]
		period = times[i]
		for test in tests:
			temp_row = {'id':test.test_para["test_id"],'time':period,'edges':test.test_para["edge_num"],'routes':len(test.routes),'speed':test.test_para['speed']}
			for name in names:
				temp_row[name]=getattr(test,name)[0]
			mywriter.writerow(temp_row)


# # Top-ranked routes 
names = ['TRMSE','area','CLength']

with open(path+'top-ranked/top-ranked_edges.csv','wb') as csvfile:
	mywriter = csv.DictWriter(csvfile,delimiter=",",fieldnames=['id','time','edges','routes','speed']+names)
	mywriter.writeheader()
	for i in range(len(times)):
		tests = typetest[i]
		period = times[i]
		for test in tests:
			temp_row = {'id':test.test_para["test_id"],'time':period,'edges':test.test_para["edge_num"],'routes':len(test.routes),'speed':test.test_para['speed']}
			top_rank = test.best_ranking('possibility')
			for name in names:
				temp_row[name]=top_rank[name]
			mywriter.writerow(temp_row)


# Best-ranked route statistics
names = ['TRMSE','area','CLength']

for index in names:
	with open(path+'best-ranked/'+index+'_edges.csv','wb') as csvfile:
		mywriter = csv.DictWriter(csvfile,delimiter=",",fieldnames=['id','time','edges','routes','speed','possibility','possibility_Rank'])
		mywriter.writeheader()
		for i in range(len(times)):
			tests = typetest[i]
			period = times[i]
			for test in tests:
				temp_row = {'id':test.test_para["test_id"],'time':period,'edges':test.test_para["edge_num"],'routes':len(test.routes),'speed':test.test_para['speed']}
				best_rank = test.best_ranking(index)
				temp_row['possibility']=best_rank['possibility']
				temp_row['possibility_Rank']=best_rank['possibility_Rank']
				mywriter.writerow(temp_row)


# maxnum = 1
# minnum = 10000

# for group in typetest:
# 	for test in group:
# 		num = test.test_para["edge_num"]
# 		minnum = num if num<minnum else minnum
# 		maxnum = num if num>maxnum else maxnum
# print minnum , maxnum