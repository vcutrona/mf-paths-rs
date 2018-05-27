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

from gpxpy.gpx import GPXTrackSegment

import util


def filter_segments_spt(segments, max_dist_error, max_speed_error):
    new_segments = []
    for segment in segments:
        points = util.remove_duplicates(segment.points)
        new_segments.append(GPXTrackSegment(util.spt(points, max_dist_error, max_speed_error)))
    return new_segments


def filter_segments_rdp(segments, max_dist_error):
    for segment in segments:
        segment.simplify(max_dist_error)
    return segments
