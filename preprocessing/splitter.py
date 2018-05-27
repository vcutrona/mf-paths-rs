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


# Split segment when detect turning point
def bearing_splitter(points_set, degree_threshold, min_length):
    segments = []
    segment = GPXTrackSegment()
    previous_bearing = None
    idx = 0

    while idx < len(points_set) - 1:
        current_bearing = util.compass_bearing(points_set[idx], points_set[idx + 1])
        if previous_bearing is not None:
            diff_bearing = abs(previous_bearing - current_bearing)
            if diff_bearing > 180:
                diff_bearing = abs(diff_bearing - 360)
            if diff_bearing > degree_threshold:
                segment.points.append(points_set[idx])
                if segment.length_2d() > min_length:
                    segments.append(segment)
                previous_bearing = None
                segment = GPXTrackSegment()
                # Not increase index. Next iteration must restart from this point
            else:
                segment.points.append(points_set[idx])
                previous_bearing = current_bearing
                idx += 1
        else:
            segment.points.append(points_set[idx])
            previous_bearing = current_bearing
            idx += 1

    segment.points.append(points_set[idx])  # append last point
    if segment.length_2d() > min_length:
        segments.append(segment)

    return segments
