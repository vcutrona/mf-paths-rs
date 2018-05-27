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
import numpy as np


# Read all files locate in directory and return an array of all segments
def gpx_reader(directory):
    segments = []
    for filename in glob.glob(directory + "*.gpx"):
        gpx = gpxpy.parse(open(filename, 'r'))

        for gpx_track in gpx.tracks:
            for segment in gpx_track.segments:
                segments.append(segment)
    return segments


def gpx_length_stats(directory):
    length_km = []
    for filename in glob.glob(directory + "*.gpx"):
        gpx = gpxpy.parse(open(filename, 'r'))
        for gpx_track in gpx.tracks:
            length_km.append(gpx_track.length_2d() / 1000.0)

    print np.mean(length_km)
    print np.max(length_km)
    print np.min(length_km)
