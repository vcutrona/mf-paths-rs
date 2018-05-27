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

import copy
import math

import numpy as np
from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from scipy.spatial import distance
from sqlalchemy import cast
from sqlalchemy import create_engine
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

from model import model


class Recommender:
    engine = create_engine('postgresql://postgres:root@localhost/hiking', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Allowed methods
    g_local_sim = 'glocal'
    global_sim = 'global'
    local_sim = 'local'

    # user_position is a dictionary -> {lat: lon:}
    def __init__(self, start_threshold, min_len, exact_len, user_position, user_id):
        self.min_len = min_len
        self.exact_len = exact_len
        self.start_threshold = start_threshold  # meters
        self.start_point_text_geom = 'POINT({} {})'.format(user_position['longitude'], user_position['latitude'])
        self.start_latitude = user_position['latitude']
        self.start_longitude = user_position['longitude']
        self.user = self.session.query(model.User).filter(model.User.id == user_id).first()

    def _find_nearest_lines(self):
        query = self.session.query(model.Segment,
                                   func.ST_Distance_Sphere(model.Segment.geom,
                                                           self.start_point_text_geom).label('distance'),
                                   func.ST_Length(cast(model.Segment.geom, Geography))
                                   ).order_by('distance')

        segments = []
        for row in query:  # row format [0]model.Segment, [1]distance (meters), [2]length (meters)
            if row[1] > self.start_threshold:
                break
            else:
                lines = self._split_start_line(self.start_point_text_geom, row[0])
                segments += lines
        return segments

    def _truncate_last_segment(self, segment, start_point, exact_len, current_length):
        # Function is called when last segment is too long.
        # Previous length is current_length - current_segment_length
        # We have to take only (exact_len - previous_len) first meters of current_segment_length

        # Detect "correct" orientation of segment
        query = self.session.query(func.st_equals(func.ST_StartPoint(segment.geom), start_point))

        previous_length = current_length - segment.length
        take_only = exact_len - previous_length
        truncate_point = float(take_only) / float(segment.length)

        # Correct SRID: 32632 (UTM WGS84 32 North)
        if not query.first()[0]:
            shorter_line = self.session.query(func.st_asewkb(func.st_Line_Substring(segment.geom, 0, truncate_point)),
                                              func.ST_Length(
                                                  cast(func.st_Line_Substring(segment.geom, 0, truncate_point),
                                                       Geography))).first()
        else:
            shorter_line = self.session.query(func.st_asewkb(func.st_Line_Substring(segment.geom,
                                                                                    1 - truncate_point, 1)),
                                              func.ST_Length(
                                                  cast(func.st_Line_Substring(segment.geom, 1 - truncate_point, 1),
                                                       Geography))).first()

        segment_labels = []
        for label in segment.labels:
            segment_labels.append(model.Label(label=label.label, label_rate=label.label_rate))

        shorter_segment = model.Segment(name=segment.name,
                                        geom=WKBElement(shorter_line[0]),
                                        length=shorter_line[1],
                                        labels=segment_labels)
        return shorter_segment

    def _split_start_line(self, point, segment):
        # Find segment's point nearest to point
        nearest_point = self.session.query(func.st_closestpoint(segment.geom, point)).first()

        # Locate nearest point on segment. Function returns the position on segment as rate
        located_point = self.session.query(func.st_line_locate_point(segment.geom, nearest_point)).first()

        # Split segment. First half starts from 0 and ends at located_point
        first_half = self.session.query(func.st_asewkb(func.st_Line_Substring(segment.geom, 0, located_point)),
                                        func.ST_Distance_Sphere(func.st_Line_Substring(segment.geom, 0, located_point),
                                                                nearest_point),
                                        func.ST_Length(cast(func.st_Line_Substring(segment.geom, 0, located_point),
                                                            Geography))).first()

        # Split segment. Second half starts from located_point and ends at 1
        second_half = self.session.query(func.st_asewkb(func.st_Line_Substring(segment.geom, located_point, 1)),
                                         func.ST_Distance_Sphere(func.st_Line_Substring(segment.geom, located_point, 1),
                                                                 nearest_point),
                                         func.ST_Length(cast(func.st_Line_Substring(segment.geom, located_point, 1),
                                                             Geography))).first()

        # Create temporary segments (do not add these segments to session), with their own labels
        first_segment_labels = []
        second_segment_labels = []

        for label in segment.labels:
            first_segment_labels.append(model.Label(label=label.label, label_rate=label.label_rate))
            second_segment_labels.append(model.Label(label=label.label, label_rate=label.label_rate))

        first_segment = model.Segment(name=segment.name,
                                      geom=WKBElement(first_half[0]),
                                      length=first_half[2],
                                      labels=first_segment_labels)
        second_segment = model.Segment(name=segment.name,
                                       geom=WKBElement(second_half[0]),
                                       length=second_half[2],
                                       labels=second_segment_labels)

        # If located point is the same as start point, return only second half
        if located_point[0] == 0.0:
            return [second_segment]
        # If located point is the same as end point, return only first half
        if located_point[0] == 1.0:
            return [first_segment]

        # Else, return two splitted segments
        return [first_segment, second_segment]

    @staticmethod
    def _segment_in_list(segment, segments):
        for seg in segments:
            if segment.name == seg.name:
                return True
        return False

    # Start point of a segment it's the bound nearest to the point passed as argument
    def _get_end_point_of_first_segment(self, segment, point):
        query1 = self.session.query(func.ST_StartPoint(segment.geom),
                                    func.ST_Distance_Sphere(func.ST_StartPoint(segment.geom), point))
        query2 = self.session.query(func.ST_EndPoint(segment.geom),
                                    func.ST_Distance_Sphere(func.ST_EndPoint(segment.geom), point))

        point1, distance1 = query1.first()
        point2, distance2 = query2.first()
        if distance1 < distance2:
            return point2
        else:
            return point1

    def _find_subpaths(self, last_point, current_segment, current_length, analyzed_segments):
        if current_length > self.exact_len:
            shorter_segment = self._truncate_last_segment(current_segment, last_point, self.exact_len, current_length)
            return [([shorter_segment], self.exact_len)]

        intersection_segments_rows = self.session.query(model.Segment,
                                                        func.ST_Length(cast(model.Segment.geom, Geography)))\
            .filter(model.Segment.geom.ST_Intersects(last_point)) \
            .all()

        # The path ends when point intersects with only one line
        if len(intersection_segments_rows) == 1:
            return [([current_segment], current_length)]

        all_subpaths = []
        for row in intersection_segments_rows:
            # Set length for each segment
            row[0].length = row[1]

            if row[0].name != current_segment.name and not self._segment_in_list(row[0], analyzed_segments):
                segment_last_point = self._get_opposite_bound(row[0], last_point)
                analyzed_segments.append(row[0])
                my_subpaths = self._find_subpaths(segment_last_point, row[0], current_length + row[1],
                                                  copy.copy(analyzed_segments))

                for subpath_tuple in my_subpaths:
                    subpath_tuple[0].insert(0, current_segment)
                    all_subpaths.append(subpath_tuple)
        return all_subpaths

    def _get_opposite_bound(self, segment, point_bound):
        query = self.session.query(func.ST_StartPoint(segment.geom))

        if query.first()[0] != point_bound:
            return query.first()[0]

        query = self.session.query(func.ST_EndPoint(segment.geom))

        return query.first()[0]

    def get_candidate_paths(self):
        segments = self._find_nearest_lines()
        all_paths = []
        for seg in segments:
            found = False
            # Skip segment if it is part of already found path
            for path_tuple in all_paths:
                # Skip first segment. It can be starting segment of another path
                for i in range(1, len(path_tuple[0])):
                    if path_tuple[0][i].name == seg.name:
                        found = True
            if not found:
                end_point = self._get_end_point_of_first_segment(seg, self.start_point_text_geom)
                analyzed_segments = [seg]
                paths_found = self._find_subpaths(end_point, seg, seg.length, analyzed_segments)
                all_paths += paths_found

        results = []
        for path_tuple in all_paths:
            if path_tuple[1] > self.min_len:
                results.append(path_tuple)

        return results

    def _compute_path_g_local_vector(self, path, baseline=False):
        path_segments = path[0]
        path_length = path[1]
        partial_length = 0

        path_vector = []
        for segment in path_segments:
            # v_i
            segment_vector = segment.get_properties_vector()

            if baseline:
                partial_length += segment.length
                # seg_i_len / P_len
                segment_length_on_path = 1.
                # decay factor
                decay = 1.
            else:
                partial_length += segment.length
                # seg_i_len / P_len
                segment_length_on_path = segment.length / float(path_length)
                # decay factor
                decay = math.exp(-(partial_length/path_length))

            segment_user_similarity = 1 - distance.cosine(segment_vector, self.user.get_profile())

            if str(segment_user_similarity) != 'nan':
                path_vector = np.sum([path_vector,
                                      list(np.multiply(segment_vector,
                                                       segment_length_on_path * segment_user_similarity * decay))],
                                     axis=0)
        return path_vector

    def _compute_path_score_local_similarity(self, path, baseline=False):
        path_segments = path[0]
        path_length = path[1]
        partial_length = 0

        segments_scores = []
        for segment in path_segments:
            # v_i
            segment_vector = segment.get_properties_vector()

            partial_length += segment.length

            if baseline:
                # seg_i_len / P_len
                segment_length_on_path = segment.length / float(path_length)
                # decay factor
                decay = math.exp(-(partial_length / path_length))
            else:
                segment_length_on_path = 1.
                decay = 1.

            segment_user_similarity = 1 - distance.cosine(segment_vector, self.user.get_profile())

            if str(segment_user_similarity) != 'nan':
                segments_scores.append(segment_length_on_path * segment_user_similarity * decay)

        path_score = np.sum(segments_scores) / len(path_segments)
        return path_score

    def _compute_path_vector_global_similarity(self, path, baseline=False):
        path_segments = path[0]
        path_length = path[1]
        partial_length = 0

        path_vector = []
        for segment in path_segments:
            # v_i
            segment_vector = segment.get_properties_vector()

            partial_length += segment.length

            if baseline:
                # seg_i_len / P_len
                segment_length_on_path = segment.length / float(path_length)
                # decay factor
                decay = math.exp(-(partial_length / path_length))
            else:
                segment_length_on_path = 1.
                decay = 1.

            path_vector = np.sum([path_vector,
                                  list(np.multiply(segment_vector, segment_length_on_path * decay))], axis=0)

        return path_vector

    def recommend(self, method, baseline=False):
        all_paths = self.get_candidate_paths()
        ordered_paths = []
        for path in all_paths:
            if method == Recommender.local_sim:
                # Similarity is computed locally within the function
                path_user_similarity = self._compute_path_score_local_similarity(path, baseline)
            elif method == Recommender.global_sim:
                path_vector = self._compute_path_vector_global_similarity(path, baseline)
                # Similarity is not computed withing the function
                path_user_similarity = 1 - distance.cosine(path_vector, self.user.get_profile())
            else:
                path_vector = self._compute_path_g_local_vector(path, baseline)
                path_user_similarity = 1 - distance.cosine(path_vector, self.user.get_profile())

            path_length = path[1]
            path_length_on_exact_length = path_length / float(self.exact_len)
            path_user_similarity = path_user_similarity * path_length_on_exact_length

            path += (path_user_similarity,)
            ordered_paths.append(path)

        ordered_paths = sorted(ordered_paths, key=lambda tup: tup[2], reverse=True)

        return ordered_paths
