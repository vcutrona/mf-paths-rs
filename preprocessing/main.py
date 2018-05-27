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

import glob

import gpxpy.gpx
from shapely.geometry import LineString
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import filter
import receiver.reader as reader
import splitter
import util
from model import model

# Geo segmentation parameters
DEGREE_THRESHOLD = 70  # Start new segment when the bearing difference is greater than this threshold (in degree)
MIN_LENGTH = -1  # Remove segments which are shorter than this threshold (in meters)

# SPT algorithm parameters
MAX_DIST_ERROR = 20  # meters
MAX_SPEED_ERROR = 3  # m/s


def execute_with_gis(directory):
    # Start ORM engine and get Session
    engine = create_engine('postgresql://postgres:root@localhost/hiking', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create table (drop if already exists)
    if model.Segment.__table__.exists(engine):
        model.Segment.__table__.drop(engine)
    model.Segment.__table__.create(engine)

    # Parsing an existing gpx file
    for filename in glob.glob(directory):
        gpx = gpxpy.parse(open(filename, 'r'))

        for gpx_track in gpx.tracks:

            # Analyze each segment of track
            for segment_id, segment in enumerate(gpx_track.segments):

                # Remove points with same timestamp, if they are consecutive
                points = util.remove_duplicates(segment.points)

                # Simplify using SPT algorithm
                new_points_spt = util.spt(points, MAX_DIST_ERROR, MAX_SPEED_ERROR)

                # Apply segmentation using turning points
                new_lines = splitter.bearing_splitter(new_points_spt, DEGREE_THRESHOLD, MIN_LENGTH)

                # Create geometry and store in GIS
                for new_line in new_lines:
                    ls = LineString(new_line)

                    # Store segment in GIS
                    gis_segment = model.Segment(name=gpx_track.name, geom=ls.wkb_hex)
                    session.add(gis_segment)

    # Save changes
    session.commit()


def execute_no_gis(directory):
    segments = reader.gpx_reader(directory)
    return segments


def execute_filter_no_gis(directory):
    segments = reader.gpx_reader(directory)
    segments = filter.filter_segments_spt(segments, MAX_DIST_ERROR, MAX_SPEED_ERROR)
    return segments


def execute_filter_split_no_gis(directory):
    segments = execute_filter_no_gis(directory)
    splitted_segments = []  # set of segment, grouped by original track
    for seg in segments:
        splitted_segments.append(splitter.bearing_splitter(seg.points, DEGREE_THRESHOLD, MIN_LENGTH))
    return splitted_segments
