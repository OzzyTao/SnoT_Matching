import sys
sys.path.append('F:/London/Case 1 and 2 programs')
from sta import Test
import pickle
import csv
path = 'f:/London/statistics_map_matching/'
# names = ['TRMSE','area','CLength']
# # normalized indices: top ranked value against the worest_value
# fields = ['30s','60s','90s','120s','150s','180s'] 
times = [30,60,90,120,150,180]
with open(path+'possroutes.p','rb') as binary:
	typetest=pickle.load(binary)

# # correlation
names = ['TRMSE_corr','area_corr','CLength_corr','TRMSE_Rank_corr','area_Rank_corr','CLength_Rank_corr']
with open(path+'corr/poss_corr_edges.csv','wb') as csvfile:
	mywriter = csv.DictWriter(csvfile,delimiter=',',fieldnames=['id','time','edges','routes']+names)
	mywriter.writeheader()
	for test in typetest:
		temp_row = {'id':test.test_para["test_id"],'time':test.test_para["period"],'edges':test.test_para["edge_num"],"routes":test.test_para["route_num"]}
		for name in names:
			temp_row[name]=getattr(test,name)[0]
		mywriter.writerow(temp_row)


# # Top-ranked routes 
names = ['TRMSE','area','CLength']

with open(path+'top-ranked/poss_top-ranked_edges.csv','wb') as csvfile:
	mywriter = csv.DictWriter(csvfile,delimiter=",",fieldnames=['id','time','edges','routes']+names)
	mywriter.writeheader()
	for test in typetest:
		temp_row = {'id':test.test_para["test_id"],'time':test.test_para["period"],'edges':test.test_para["edge_num"],"routes":test.test_para["route_num"]}
		top_rank = test.best_ranking('possibility')
		for name in names:
			temp_row[name]=top_rank[name]
		mywriter.writerow(temp_row)


# Best-ranked route statistics
names = ['TRMSE','area','CLength']

for index in names:
	with open(path+'best-ranked/poss_'+index+'_edges.csv','wb') as csvfile:
		mywriter = csv.DictWriter(csvfile,delimiter=",",fieldnames=['id','time','edges','routes','possibility','possibility_Rank'])
		mywriter.writeheader()
		for test in typetest:
			temp_row = {'id':test.test_para["test_id"],'time':test.test_para['period'],'edges':test.test_para["edge_num"],'routes':test.test_para['route_num']}
			best_rank = test.best_ranking(index)
			temp_row['possibility']=best_rank['possibility']
			temp_row['possibility_Rank']=best_rank['possibility_Rank']
			mywriter.writerow(temp_row)

