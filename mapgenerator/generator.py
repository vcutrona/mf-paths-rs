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

import preprocessing.main as pp
import writer.writer as w
import subprocess


class MapGenerator:

    def __init__(self):
        pass

    def _execute_java(self, input_path, output_path, eps=150.0, has_altitude=False, alt_eps=4.0):
        subprocess.call(args=['java',
                              '-cp',
                              '../bin/Ahmed/bin',
                              'mapconstruction2.MapConstruction',
                              input_path,
                              output_path,
                              str(eps),
                              str(has_altitude),
                              str(alt_eps)
                              ])

    def generate_segments_txts(self):
        segments_original = pp.execute_no_gis('../docs/hiking_resegone/')
        w.gpx_segments_to_utm_txt(segments_original, '../docs/hiking_resegone_txt/original/')

        segments_filtered = pp.execute_filter_no_gis('../docs/hiking_resegone/')
        w.gpx_segments_to_utm_txt(segments_filtered, '../docs/hiking_resegone_txt/filtered/')

        segments_splitted_blocks = pp.execute_filter_split_no_gis('../docs/hiking_resegone/')
        segments_splitted = [item for sublist in segments_splitted_blocks for item in sublist]
        w.gpx_segments_to_utm_txt(segments_splitted, '../docs/hiking_resegone_txt/splitted/')

    def generate_map_files(self, input_path, output_path, eps):
        self._execute_java(input_path, output_path, eps=eps)
