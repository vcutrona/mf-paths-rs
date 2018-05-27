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
import os
import time

import utm


# Print each segment in its own file. Use "easting northing timestamp" format.
def gpx_segments_to_utm_txt(segments, directory):
    files = glob.glob(directory + '*')
    for f in files:
        os.remove(f)
    i = 0
    for segment in segments:
        new_file = open(directory + "trip_{}.txt".format(i), 'w')
        for point in segment.points:
            easting, northing, zone_number, zone_letter = utm.from_latlon(point.latitude, point.longitude)
            new_file.write('{} {} {}\n'.format(easting, northing, time.mktime(point.time.timetuple())))
        new_file.close()
        i += 1
