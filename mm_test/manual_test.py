import sys
sys.path.append('F:/London/Case 1 and 2 programs')
import case1 
import psycopg2
import math
import testdb
import time
import numpy
import networkx as nx
import matplotlib.pyplot as plt
from sta import Test
import pickle

import csv


def get_edges(route,cur):
	edgenum=len(route)-1
	edge=[]
	for i in range(edgenum):
		start=route[i]
		end = route[i+1]
		cur.execute('select getedgeid(%s,%s);' % (start,end))
		edge.append(str(cur.fetchone()[0]))
	return edge

def get_exact_record(measurements,cur):
	zl=[]
	t=[]
	for measurement in measurements:
		cur.execute('''select id, timestamp, 
			ST_X(ST_transform(ST_setsrid(ST_makepoint(longitude,latitude),4326),32630)),
			ST_Y(ST_transform(ST_setsrid(ST_makepoint(longitude,latitude),4326),32630))
			from ecourier_oneday where id=%s;''',(measurement,))
		record = cur.fetchone()
		t.append(record[1])
		zl.append(numpy.array([record[2],record[3]]))
	start=t[0]
	return zl,[(time-start).total_seconds() for time in t]

def get_allmeasurements(measurements,cur):
	allmeasurements=[]
	for measurement in measurements:
		cur.execute('''select id, timestamp from ecourier_oneday where id = %s;''',(measurement,))
		allmeasurements.append(cur.fetchone())
	return allmeasurements

def RSME(edge, allmeasurements, cur):
	distance=[]
	for measurement in allmeasurements:
		cur.execute('select st_distance(geom_way,geom,true) as dis from hh_2po_4pgr a, ecourier_oneday b where b.id='+str(measurement[0])+' and a.id in ('+','.join(edge)+') order by dis limit 1;')
		distance.append(cur.fetchone()[0])
	total = 0.0
	for d in distance:
		total+=d*d
	return math.sqrt(total/len(distance))
# assuming constant speed for estimated route and measurements projection for true path
def temporal_RSME(edge,allmeasurements,startvertex,cur,truepath):
	starttime = allmeasurements[0][1]
	total_time = (allmeasurements[-1][1]-starttime).total_seconds()
	distance=[]
	for measurement in allmeasurements:
		fraction = (measurement[1]-starttime).total_seconds()/total_time
		edgestr = "'{"+','.join(edge)+"}'"
		truepathstr = "'{"+','.join([str(x) for x in truepath])+"}'"
		tempstr = 'select st_distance(ST_LineInterpolatePoint(mergeroute('+edgestr+' , '+str(startvertex)+'),'+str(fraction)+'),measurement_projection('+truepathstr+','+str(measurement[0])+'),true) as dis;'
		# print tempstr
		cur.execute(tempstr)
		distance.append(cur.fetchone()[0])
	total = 0.0
	for d in distance:
		total+=d*d
	return math.sqrt(total/len(distance))

def nearest_vertex(G,measurement):
	minimum_distance = 1000000
	for node in nx.nodes_iter(G):
		pos = G.node[node]['pos']
		distance = math.sqrt((measurement[0]-pos[0])**2+(measurement[1]-pos[1])**2)
		if distance< minimum_distance:
			minimum_distance=distance
			result = node
	return result

def surrounding_area(modelpath,modelstartvertex,truepath,startvertex,cur):
	modelpathstr = "'{"+','.join(modelpath)+"}'"+' , '+str(modelstartvertex)
	truepathstr = "'{"+','.join([str(x) for x in truepath])+"}'"+' , '+str(startvertex)
	components = 'ARRAY[m,t,st_makeline(st_startpoint(m),st_startpoint(t)),st_makeline(st_endpoint(m),st_endpoint(t))]'
	query = "select st_area(st_makepolygon(st_linemerge(st_collect("+components+"))),true) from mergeroute("+modelpathstr+") m, mergeroute("+truepathstr+") t ;"
	# print query
	cur.execute(query)
	return cur.fetchone()[0]

def share_distance(modelpath,modelstartvertex,truepath,startvertex,cur):
	modelpathstr = "'{"+','.join(modelpath)+"}'"+' , '+str(modelstartvertex)
	truepathstr = "'{"+','.join([str(x) for x in truepath])+"}'"+' , '+str(startvertex)
	query = "select st_length(st_intersection(m,t))/st_length(t) from mergeroute("+modelpathstr+") m, mergeroute("+truepathstr+") t ;"
	cur.execute(query)
	return cur.fetchone()[0]

def case1_vehicle(interval):
	sig = 5
	# Algorithm parameters
	n = 100  # number of samples
	K = 100  # minimum number of candidate paths
	vmean = 10. # mean velocity
	vvar = 4. # velocity variance

	conn = psycopg2.connect("dbname=gis user=postgres password=peach")
	cur = conn.cursor()

	cur.execute('''select measurements, gt_manul_edges, test_id
		from testcases
		where time_slot=%s and gt_manul_edges != '{}'
		''', (interval,))

	tests = cur.fetchall()
	results = []
	for test in tests:
		allmeasurements_id = test[0]
		manul_route = test[1]
		locations,timestamp = get_exact_record(allmeasurements_id,cur)
		zl = [locations[0],locations[-1]]
		t = [timestamp[0],timestamp[-1]]
		allmeasurements = get_allmeasurements(allmeasurements_id,cur)

		G= testdb.london_roadmap(allmeasurements_id)
		if G.nodes():
			startvertex = nearest_vertex(G,zl[0])
			endvertex = nearest_vertex(G,zl[-1])

		print zl
		print t

		if len(G.edges())!=501 and nx.has_path(G,startvertex,endvertex) and startvertex!=endvertex:
			try:
				t0 = time.time()
				[pp,sep,wp] = case1.calcpostprobs(G,zl,t,n,K,vmean,vvar,sig*sig)
				et = time.time()-t0
				print et, "secs, done algorithm"
				possibleroutes = len(pp)
				
				if allmeasurements:
					# tpath = real_path(G,allmeasurements,startvertex,endvertex,cur)
					# print "TRUE PATH", tpath
					# tedge = get_edges(tpath,cur)
					tedge = manul_route
					result=[]
					for j in range(possibleroutes):
						# print "modeled path:",pp[j]
						edge = get_edges(pp[j],cur)
						try:
							area = surrounding_area(edge,pp[j][0],tedge,startvertex,cur)
						except:
							conn.rollback()
							area = surrounding_area(edge,pp[j][-1],tedge,startvertex,cur)
						result.append({'route':pp[j],
							'possibility':wp[j],
							'RMSE':RSME(edge,allmeasurements,cur),
							'temporal_RMSE':temporal_RSME(edge,allmeasurements,pp[j][0],cur,tedge),
							'area':area,
							'common_length':share_distance(edge,pp[j][0],tedge,startvertex,cur),
							'edgeIDList':edge
							})
					newtest = Test(result)
					newtest.test_para = {'period':t[-1],"test_id":test[2]}
					results.append(newtest)
					print "Success.************************", len(results)
				else:
					print "vertx edge table error",idl,allmeasurements
			except:
				conn.rollback()
				print "FAIL............................."
	return results

# intervals=[30,60,90,120,150,180]
# for interval in intervals:
interval = 180
results = case1_vehicle(interval)
f = open("f:/London/statistics_manual/"+str(interval)+'seconds'+str(len(results))+'test.p','wb')
pickle.dump(results,f)
