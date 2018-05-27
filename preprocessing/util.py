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

from __future__ import division

import math
from functools import partial

import pyproj
from geopy.distance import vincenty
from shapely.ops import transform


# Class that represent a point
class Point:
    def __init__(self, latitude, longitude, time):
        self.latitude = latitude
        self.longitude = longitude
        self.time = time


# from http://people.cs.aau.dk/~simas/teaching/trajectories/KVVQ7QUQA7YBXUFA.pdf, pages 772-773
def spt(pts, max_dist_error, max_speed_error):
    if len(pts) <= 2:
        return pts
    else:
        is_error = False
        e = 1
        while e < len(pts) and not is_error:
            s = 1
            while s < e - 1 and not is_error:

                delta_e = pts[e].time_difference(pts[0])
                delta_i = pts[s].time_difference(pts[0])

                new_point_lat = pts[s].latitude + (pts[e].latitude - pts[0].latitude) * (delta_i / delta_e)
                new_point_lon = pts[s].longitude + (pts[e].longitude - pts[0].longitude) * (delta_i / delta_e)

                new_point = Point(new_point_lat, new_point_lon, None)

                vel_pre_s = distance_between_points(pts[s], pts[s-1]) / pts[s].time_difference(pts[s-1])
                vel_s = distance_between_points(pts[s+1], pts[s]) / pts[s+1].time_difference(pts[s])

                if distance_between_points(pts[s], new_point) > max_dist_error or \
                        abs(vel_s - vel_pre_s) > max_speed_error:
                    is_error = True
                else:
                    s += 1
            if is_error:
                return [pts[1]] + spt(pts[s:len(pts)], max_dist_error, max_speed_error)
            e += 1
        if not is_error:
            return [pts[1], pts[len(pts)-1]]


def compass_bearing(point_a, point_b):

    lat1 = math.radians(point_a.latitude)
    lat2 = math.radians(point_b.latitude)

    diff_long = math.radians(point_b.longitude - point_a.longitude)

    x = math.sin(diff_long) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(diff_long))

    initial_bearing = math.atan2(x, y)

    # Now we have the initial bearing but math.atan2 return values
    # from -180 to + 180 which is not what we want for a compass bearing
    # The solution is to normalize the initial bearing as shown below
    initial_bearing = math.degrees(initial_bearing)
    cmp_bearing = (initial_bearing + 360) % 360

    return cmp_bearing


def line_length_meters(line_string):
    # Projection
    project = partial(
        pyproj.transform,
        pyproj.Proj(init='EPSG:4326'),
        pyproj.Proj(init='EPSG:32633'))  # 3857

    projected_line = transform(project, line_string)

    # Get length
    return projected_line.length


# Get distance (in meters) between two points
def distance_between_points(point_a, point_b):
    a = (point_a.latitude, point_a.longitude)
    b = (point_b.latitude, point_b.longitude)
    return round(vincenty(a, b).kilometers * 1000)


# Discard point if next point has same timestamp
def remove_duplicates(points_set):
    return_set = []
    i = 0
    while i < len(points_set)-1:
        if points_set[i].time_difference(points_set[i+1]) > 0:
            return_set.append(points_set[i])
        i += 1
    return_set.append(points_set[i])  # append last point
    return return_set
