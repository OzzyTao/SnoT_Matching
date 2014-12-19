import sys
sys.path.append('F:/London/Case 1 and 2 programs')
from sta import Test
import pickle
import csv
path = 'f:/London/statistics_manual/'
# names = ['TRMSE','area','CLength']
# # normalized indices: top ranked value against the worest_value
# fields = ['30s','60s','90s','120s','150s','180s'] 
times = [30,60,90,120,150,180]
binaryfiles = ['30seconds92test.p','60seconds84test.p','90seconds58test.p','120seconds57test.p','150seconds69test.p','180seconds64test.p']
typetest = []
for file in binaryfiles:
	with open(path+file,'rb') as binary:
		typetest.append(pickle.load(binary))

# # correlation
names = ['TRMSE_corr','area_corr','CLength_corr','TRMSE_Rank_corr','area_Rank_corr','CLength_Rank_corr']
with open(path+'corr/corr.csv','wb') as csvfile:
	mywriter = csv.DictWriter(csvfile,delimiter=',',fieldnames=['id','time']+names)
	mywriter.writeheader()
	for i in range(len(times)):
		tests=typetest[i]
		period = times[i]
		for test in tests:
			temp_row = {'id':test.test_para["test_id"],'time':period}
			for name in names:
				temp_row[name]=getattr(test,name)[0]
			mywriter.writerow(temp_row)


# # Top-ranked routes 
names = ['TRMSE','area','CLength']

with open(path+'top-ranked/top-ranked.csv','wb') as csvfile:
	mywriter = csv.DictWriter(csvfile,delimiter=",",fieldnames=['id','time']+names)
	mywriter.writeheader()
	for i in range(len(times)):
		tests = typetest[i]
		period = times[i]
		for test in tests:
			temp_row = {'id':test.test_para["test_id"],'time':period}
			top_rank = test.best_ranking('possibility')
			for name in names:
				temp_row[name]=top_rank[name]
			mywriter.writerow(temp_row)


# Best-ranked route statistics
names = ['TRMSE','area','CLength']

for index in names:
	with open(path+'best-ranked/'+index+'.csv','wb') as csvfile:
		mywriter = csv.DictWriter(csvfile,delimiter=",",fieldnames=['id','time','possibility','possibility_Rank'])
		mywriter.writeheader()
		for i in range(len(times)):
			tests = typetest[i]
			period = times[i]
			for test in tests:
				temp_row = {'id':test.test_para["test_id"],'time':period}
				best_rank = test.best_ranking(index)
				temp_row['possibility']=best_rank['possibility']
				temp_row['possibility_Rank']=best_rank['possibility_Rank']
				mywriter.writerow(temp_row)


