"""
Copyright 2018 Vincenzo Cutrona

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import networkx as nx
import utm
from shapely.geometry import LineString
from shapely.geometry import Point
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from annotator import annotator as ann
from model import model


class MapGraph:

    def __init__(self):
        self.map_graph = nx.Graph()

    def map_to_graph(self, directory):

        vertices_file = open(directory + 'vertices.txt', 'r')
        vertices_raw = vertices_file.readlines()
        edges_file = open(directory + 'edges.txt', 'r')
        edges_raw = edges_file.readlines()

        for vertex_raw in vertices_raw:
            id_pt, easting, northing, _ = vertex_raw.strip('\n').split(',')
            lat, lng = utm.to_latlon(float(easting), float(northing), 32, 'N')
            self.map_graph.add_node(int(id_pt), latitude=lat, longitude=lng)

        for edge_raw in edges_raw:
            id_seg, start_pt_id, end_pt_id = edge_raw.strip('\n').split(',')
            self.map_graph.add_edge(int(start_pt_id), int(end_pt_id), points=[])

        # some nodes are within edge line, but there isn't an intersection. Just create it
        for node, data in self.map_graph.nodes_iter(data=True):
            point = Point(data['longitude'], data['latitude'])
            for edge in self.map_graph.edges_iter():
                if node != edge[0] and node != edge[1]:
                    start_point = self.map_graph.node[edge[0]]
                    end_point = self.map_graph.node[edge[1]]
                    line = LineString([Point(start_point['longitude'], start_point['latitude']),
                                      Point(end_point['longitude'], end_point['latitude'])])

                    if line.distance(point) < 1e-8:
                        self.map_graph.remove_edge(edge[0], edge[1])
                        self.map_graph.add_edge(edge[0], node, points=[])
                        self.map_graph.add_edge(node, edge[1], points=[])
        return self.map_graph

    def _get_segments_from_map(self):
        intersection_nodes = []
        for n, d in self.map_graph.nodes_iter(data=True):
            if self.map_graph.degree(n) != 2:
                intersection_nodes.append(n)

        paths = []
        checked_pairs = []
        removed_edges = []
        for first in intersection_nodes:
            for second in intersection_nodes:
                # check if this pair is already checked
                checked = False

                for pair in checked_pairs:
                    if pair[0] == second and pair[1] == first or pair[1] == second and pair[0] == first:
                        checked = True
                        break
                if not checked:
                    # Reset removed arcs for the previous pair
                    for removed_edge in removed_edges:
                        self.map_graph.add_edge(removed_edge[0], removed_edge[1], points=[])
                    removed_edges = []

                    checked_pairs.append((first, second))
                    try:
                        try_again = True
                        last_paths = []
                        while try_again:
                            paths_copy = list(nx.all_shortest_paths(self.map_graph, first, second))
                            if last_paths == paths_copy:
                                try_again = False
                            else:
                                last_paths = paths_copy
                                for p in paths_copy:
                                    if len(p) > 1:
                                        valid = True
                                        for n in p[1:len(p) - 1]:
                                            if self.map_graph.degree(n) != 2:
                                                valid = False
                                                break
                                        if valid:
                                            tmp_path = []
                                            for node in p:
                                                tmp_path.append(Point(self.map_graph.node[node]['longitude'],
                                                                      self.map_graph.node[node]['latitude']))
                                            paths.append(tmp_path)
                                        for i in range(0, len(p)-1):
                                            try:
                                                self.map_graph.remove_edge(p[i], p[i+1])
                                                removed_edges.append((p[i], p[i+1]))
                                            except nx.exception.NetworkXError:
                                                continue
                    except nx.exception.NetworkXNoPath:
                        continue
        return paths

    def paths_to_geom(self):
        engine = create_engine('postgresql://postgres:root@localhost/hiking', echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Create table (drop if already exists)
        if model.Label.__table__.exists(engine):
            model.Label.__table__.drop(engine)
        if model.Segment.__table__.exists(engine):
            model.Segment.__table__.drop(engine)
        model.Segment.__table__.create(engine)
        model.Label.__table__.create(engine)
        annotator = ann.SyntheticAnnotator(.5, .3)
        for idx, path in enumerate(self._get_segments_from_map()):
            ls = LineString(path)

            # Store segment in GIS
            gis_segment = model.Segment(name='seg' + str(idx), geom=ls.wkb_hex)
            labels = annotator.annotation()
            for l in labels:
                gis_segment.labels.append(model.Label(label=l[0], label_rate=l[1]))
            session.add(gis_segment)
        session.commit()
