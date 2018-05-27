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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import mapgenerator.generator as mapgen
import recommendation.recommender as rs
from model import model
from mapgenerator.graph import MapGraph


class Demo:

    def __init__(self):
        pass

    def recommend_user(self, user_id, method):
        my_position = dict(latitude=45.85821905286897, longitude=9.46938252645873)
        r = rs.Recommender(50, 1950, 2000, my_position, user_id)
        return r.recommend(method)

    def analyze_paths(self, paths):
        directory = '../evaluation/'
        new_file = open(directory + "paths_analysis.txt", 'w')
        for i, path in enumerate(paths):
            new_file.write('-----------------PATH {}-----------------\n'.format(i))
            new_file.write('Length: {}\n'.format(path[1]))
            segments = path[0]
            for segment in segments:
                new_file.write('SegName: {} ->'.format(segment.name))
                new_file.write('SegLen: {} ->'.format(segment.length))
                segment_labels = ''
                for label in segment.labels:
                    segment_labels += '{} '.format(label.label)
                new_file.write('SegmentLabels: {}\n'.format(segment_labels))
            new_file.write('------------------------------------------\n\n')
        new_file.close()

    def questionnaire_paths(self, user_id, gis_store=False):
        my_position = dict(latitude=45.86432820440195, longitude=9.488129491092195)
        r = rs.Recommender(50, 3500, 4000, my_position, user_id)
        final_paths = r.get_candidate_paths()

        # Store paths to GIS
        if gis_store:
            engine = create_engine('postgresql://postgres:root@localhost/hiking', echo=False)
            Session = sessionmaker(bind=engine)
            session = Session()
            model.Path.__table__.create(engine)
            i = 1
            for path, length in final_paths:
                gis_path = model.Path()
                segments_string = ""
                for segment in path:
                    segments_string += segment.name + " "
                gis_path.length = length
                gis_path.segments = segments_string
                gis_path.name = 'path{}'.format(i)
                session.add(gis_path)
                i += 1
            session.commit()

        self.analyze_paths(final_paths)

    def start(self):
        mg = mapgen.MapGenerator()
        mg.generate_segments_txts()
        mg.generate_map_files('../docs/hiking_resegone_txt/original/', '../docs/map_resegone/original/', eps=30.0)
        mg.generate_map_files('../docs/hiking_resegone_txt/filtered/', '../docs/map_resegone/filtered/', eps=30.0)
        mg.generate_map_files('../docs/hiking_resegone_txt/splitted/', '../docs/map_resegone/splitted/', eps=50.0)

        g = MapGraph()
        g.map_to_graph('../docs/map_resegone/splitted/')
        g.paths_to_geom()

        self.recommend_user(1, rs.Recommender.g_local_sim)
        self.recommend_user(2, rs.Recommender.g_local_sim)
        self.recommend_user(3, rs.Recommender.g_local_sim)

        self.questionnaire_paths(1)
