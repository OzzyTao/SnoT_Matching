import networkx as nx
import psycopg2
import numpy
import time
from matplotlib import pyplot as plt 


def london_roadmap(allmeasurements):
	start = time.time()

	conn = psycopg2.connect("dbname=gis user=postgres password=peach")
	cur = conn.cursor()
	cur.execute("drop table if exists subgraph;")

	raw_query = '''create table subgraph as (select * from hh_2po_4pgr,(select st_buffer(st_envelope(st_collect(geom)),200/111320.0) as box from ecourier_oneday where id = any(array[%s])) as f 
	where geom_way && f.box);''' % ','.join([str(m) for m in allmeasurements])
	cur.execute(raw_query)	# subgraph
	cur.execute("""create or replace function getedgeid(integer,integer) returns integer as 'select id from subgraph where ($1=source and $2=target) or ($1=target and $2=source) limit 1;' language sql immutable returns null on null input;""")


	sourcex = "ST_X(ST_transform(ST_setsrid(ST_makepoint(x1,y1),4326),32630))"
	sourcey = "ST_Y(ST_transform(ST_setsrid(ST_makepoint(x1,y1),4326),32630))"
	targetx = "ST_X(ST_transform(ST_setsrid(ST_makepoint(x2,y2),4326),32630))"
	targety = "ST_Y(ST_transform(ST_setsrid(ST_makepoint(x2,y2),4326),32630))"
	cur.execute("select source,target,"+sourcex+","+sourcey+","+targetx+","+targety+",km from subgraph;")

	roadmap = nx.Graph()
	for record in cur:
		source,target,x1,y1,x2,y2,cost=record
		# print source,target
		if not roadmap.has_node(source):
			roadmap.add_node(source,pos=numpy.array([x1,y1]))
		if not roadmap.has_node(target):
			roadmap.add_node(target,pos=numpy.array([x2,y2]))
		if source!=target:
			roadmap.add_edge(source,target,weight=cost*1000)
		# print roadmap.node[source]['pos'],roadmap.node[target]['pos'],cost*1000

	end =time.time()

	print "Graph generating ..."
	print end-start, 'secs'

	# position={}
	# for node in roadmap:
	# 	position[node]=roadmap.node[node]['pos']
	# nx.draw(roadmap,pos=position,node_size=50)
	# plt.show()

	print nx.number_of_nodes(roadmap), "nodes"
	print nx.number_of_edges(roadmap), "edges"
	return roadmap
