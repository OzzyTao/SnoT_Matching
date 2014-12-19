from scipy import stats
import psycopg2

# snipping measurements to road network 
# return road edge id array
def cal_min_bbox(allmeasurements,cur):
	allcoordinates=[]
	pointsqlx ="ST_X(ST_transform(ST_setsrid(ST_makepoint(longitude,latitude),4326),32630))"
	pointsqly ="ST_Y(ST_transform(ST_setsrid(ST_makepoint(longitude,latitude),4326),32630))"
	for measurement in allmeasurements:
		cur.execute("select "+pointsqlx+","+pointsqly+" from ecourier_oneday where id="+str(measurement)+"; ")
		allcoordinates.append(cur.fetchone())
	minx = min([p[0] for p in allcoordinates])
	maxx = max([p[0] for p in allcoordinates])
	miny = min([p[1] for p in allcoordinates])
	maxy = max([p[1] for p in allcoordinates])
	return minx, maxx, miny, maxy

def create_temp_roadmap(allmeasurements,cur):
	# envelope="ST_Transform(ST_MakeEnvelope(%s,%s,%s,%s,32630),4326)" % boundingbox
	# cur.execute("create table tempgraph as (select * from hh_2po_4pgr where geom_way && "+envelope+");")
	raw_query = '''create table tempgraph as (select * from hh_2po_4pgr,(select st_buffer(st_envelope(st_collect(geom)),200/111320.0) as box from ecourier_oneday where id = any(array[%s])) as f 
	where geom_way && f.box);''' % ','.join([str(m) for m in allmeasurements])
	cur.execute(raw_query)

def get_edges(route,cur):
	edgenum=len(route)-1
	edge=[]
	for i in range(edgenum):
		start=route[i]
		end = route[i+1]
		cur.execute('select getedgeid(%s,%s);' % (start,end))
		temp=cur.fetchone()
		if temp!=None and temp[0]!=None:
			edge.append(str(temp[0]))
	return edge

def check_graph(candidate_graph,measurements):
	for measurement in measurements:
		print 'measurement +++++++++++++++++++ '+str(measurement)
		for candidate in candidate_graph[str(measurement)]:
			print '**', candidate
	print '____________________________________________________'

def record_projection(testid,measurementid,pointid,cur):
	# print pointid
	cur.execute('''select * from measurements_proj where test_id=%s and measurement_id=%s;''',(testid,measurementid))
	if not cur.fetchone():
		cur.execute('''INSERT INTO measurements_proj(test_id,measurement_id) VALUES (%s, %s); ''', (testid,measurementid))
		cur.execute('''Select * from tempgraph where source = %s;''',(pointid,))
		if cur.fetchone():
			cur.execute('''UPDATE measurements_proj SET  geom = ST_StartPoint(geom_way) from tempgraph 
				where tempgraph.source = %s and measurements_proj.test_id=%s and measurements_proj.measurement_id=%s;''',(pointid,testid,measurementid))
		else:
			cur.execute('''UPDATE measurements_proj SET  geom = ST_EndPoint(geom_way) from tempgraph 
				where tempgraph.target = %s and measurements_proj.test_id=%s and measurements_proj.measurement_id=%s;''',(pointid,testid,measurementid))


def cal_route(measurements,testid,cur):
	boundingboxratio = 1.0
	GPS_buffer = 100
	candidate_graph = {}
	pointid = 570000
	edgeid = 669000
	new_points = []
	GPS_distribution = stats.norm(loc=0,scale=20)

	create_temp_roadmap(measurements,cur)
	edge_query = '''select b.id as edge, b.source as source, b.target as target 
					from ecourier_oneday a, tempgraph b 
					where a.id = %s and st_dwithin(a.geom,b.geom_way,%s) order by st_distance(a.geom,b.geom_way) limit 4'''
	original_edge = {}
	for measurement in measurements:
		cur.execute(edge_query,(measurement,GPS_buffer/111320.0))
		candidates = [{'on_edge':x} for x in cur]
		# print candidates

		for candidate in candidates:
			cur.execute('''select st_distance(a.geom::geography,b.geom_way::geography)
					from ecourier_oneday a, tempgraph b
					where a.id = %s and b.id = %s''',(measurement,candidate['on_edge'][0]))
			candidate['observation_prob'] = GPS_distribution.pdf(cur.fetchone()[0])
			cur.execute('''select ST_LineLocatePoint(b.geom_way,a.geom), km
				from ecourier_oneday a, tempgraph b
				where a.id = %s and b.id = %s''',(measurement,candidate['on_edge'][0]))
			interpolate = cur.fetchone()
			if interpolate[0] == 0:
				candidate['pointid'] = candidate['on_edge'][1]
			elif interpolate[0] == 1:
				candidate['pointid'] = candidate['on_edge'][2]
			# min_proportion = interpolate[0] if interpolate[0] else 0.001
			else:
				add_edge_query = '''INSERT INTO tempgraph(id,source,target,km) VALUES (%s,%s,%s,%s)'''
				geom_query = '''update tempgraph as a set geom_way=ST_LineSubstring(b.geom_way,%s,%s) from tempgraph b where a.id = %s and b.id=%s;'''
				cur.execute(add_edge_query,(edgeid,candidate['on_edge'][1],pointid,interpolate[0]*interpolate[1]))
				cur.execute(geom_query,(0,interpolate[0],edgeid,candidate['on_edge'][0]))
				if candidate['on_edge'][0]>=669000:
					original_edge[str(edgeid)]=original_edge[str(candidate['on_edge'][0])]
				else:
					original_edge[str(edgeid)]=candidate['on_edge'][0]
				edgeid+=1
				cur.execute(add_edge_query,(edgeid,pointid,candidate['on_edge'][2],(1-interpolate[0])*interpolate[1]))
				cur.execute(geom_query,(interpolate[0],1,edgeid,candidate['on_edge'][0]))
				if candidate['on_edge'][0]>=669000:
					original_edge[str(edgeid)]=original_edge[str(candidate['on_edge'][0])]
				else:
					original_edge[str(edgeid)]=candidate['on_edge'][0]
				candidate['pointid'] = pointid
				new_points.append(pointid)
				edgeid+=1
				pointid+=1
				cur.execute('''DELETE FROM tempgraph WHERE id =%s''',(candidate['on_edge'][0],))
		candidate_graph[str(measurement)]=candidates

	# check_graph(candidate_graph,measurements)

	for candidate in candidate_graph[str(measurements[0])]:
		candidate['f'] = candidate['observation_prob']

	for i in range(1,len(measurements)):
		# calculate euclidean distance in meters
		cur.execute('''select st_distance(a.geom::geography,b.geom::geography)
			from ecourier_oneday a, ecourier_oneday b
			where a.id = %s and b.id=%s''',(measurements[i],measurements[i-1]))
		euclidean_distance = cur.fetchone()[0]
		for candidate in candidate_graph[str(measurements[i])]:
			max_value = -1000
			for pre_candidate in candidate_graph[str(measurements[i-1])]:
				# calculate shortest path between two candidates
				if pre_candidate['pointid']==candidate['pointid']:
					route=[]
					alt= pre_candidate['f'] + candidate['observation_prob']
				else:
					cur.execute('''select * from pgr_dijkstra('
						select id, source, target, km as cost from tempgraph
						',%s,%s,false,false);''',(pre_candidate['pointid'],candidate['pointid']))
					routes = cur.fetchall()
					alt = -1000
					if routes:
						total_cost = sum([x[-1] for x in routes])*1000
						route = [x[1] for x in routes]
						alt = pre_candidate['f'] + candidate['observation_prob']*(1-abs(euclidean_distance-total_cost)/(total_cost+euclidean_distance))
				if alt>max_value:
					max_value = alt
					candidate['pre'] = pre_candidate
					candidate['route']= route
				candidate['f'] = max_value
	
	max_value = -1000
	max_candidate = {}
	for candidate in candidate_graph[str(measurements[-1])]:
		if candidate['f'] > max_value:
			max_value=candidate['f']
			max_candidate = candidate
	
	edge_list = [max_candidate['on_edge'][0]]
	record_projection(testid,measurements[-1],max_candidate['pointid'],cur)
	realpath = []

	for i in range(1,len(measurements)):
		realpath=max_candidate['route']+realpath
		max_candidate = max_candidate['pre']
		edge_list.append(max_candidate['on_edge'][0])
		record_projection(testid,measurements[-1-i],max_candidate['pointid'],cur)
	print edge_list
	# edge_list=[x for x in edge_list if x < 669000]
	end_edge =edge_list[0] if edge_list[0]<669000 else original_edge[str(edge_list[0])] 
	start_edge =edge_list[-1] if edge_list[-1]<669000 else original_edge[str(edge_list[-1])]  

	print 'start edge:',start_edge
	print 'end edge:', end_edge
	# vertex_list.append(max_candidate['pointid'])
	# vertex_list.reverse()

	# realpath = []
	# for j in range(len(vertex_list)-1):
	# 	cur.execute('''select * from pgr_dijkstra('
	# 				select id, source, target, km as cost from tempgraph
	# 				',%s,%s,false,false);''',(vertex_list[j],vertex_list[j+1]))
	# 	realpath = realpath+ [x[1] for x in cur]


	simple_realpath = []
	for j in range(len(realpath)):
		if j==0 or j==len(realpath)-1:
			simple_realpath.append(realpath[j])
		elif realpath[j] not in new_points:
			if len(simple_realpath)>1 and realpath[j] == simple_realpath[-2]:
				simple_realpath.pop()
			elif realpath[j] != simple_realpath[-1]:
				simple_realpath.append(realpath[j])			

	
	# start_edge = [x['on_edge'][0] for x in candidate_graph[str(measurements[0])] if x['pointid']==simple_realpath[0]][0]
	# end_edge = [x['on_edge'][0] for x in candidate_graph[str(measurements[-1])] if x['pointid']==simple_realpath[-1]][0]
	temp_edges=get_edges(simple_realpath,cur)
	print temp_edges
	temp_edges = [str(start_edge)] + temp_edges if str(start_edge)!=temp_edges[0] and start_edge<669000 else temp_edges
	temp_edges = temp_edges + [str(end_edge)] if str(end_edge)!=temp_edges[-1] and end_edge<669000 else temp_edges
	return temp_edges




conn = psycopg2.connect("dbname=gis user=postgres password=peach")
cur = conn.cursor()
cur.execute("select measurements, test_id, gt_mm_edges from testcases order by test_id;")
alldata = cur.fetchall()
count=0
for test in alldata:
	try:
		# if not test[2]:
		if True:
			print test
			route = "{%s}" % (','.join(cal_route(test[0],test[1],cur)),)
			print test[0], route
			conn.commit()
			cur.execute('''Drop table if exists tempgraph;''')
			# conn.rollback()
			cur.execute('''update testcases set gt_mm_edges=%s where test_id = %s''',(route,test[1]))
			conn.commit()
			print 'successful************'+str(count)
			count+=1
		else:
			print "Already there"
	except:
		print "fail-------"
		conn.rollback()


# cur.execute("select measurements, test_id, gt_mm_edges from testcases where test_id=126;")
# alldata = cur.fetchall()
# count=0
# for test in alldata:
# 	# try:
# 	print test
# 	route = "{%s}" % (','.join(cal_route(test[0],test[1],cur)),)
# 	print test[0], route
# 	conn.commit()
# 	cur.execute('''Drop table tempgraph;''')
# 	# conn.rollback()
# 	cur.execute('''update testcases set gt_mm_edges=%s where test_id = %s''',(route,test[1]))
# 	conn.commit()
# 	print 'successful************'+str(count)
# 	count+=1

# 	# except:
# 	# 	print "fail-------"
# 	# 	conn.rollback()

cur.close()
conn.close()
