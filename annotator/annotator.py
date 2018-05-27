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

import random as rnd

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from model import model


class SyntheticAnnotator:
    rock = 'rock'
    dirt = 'dirt'
    woodland = 'woodland'
    asphalt = 'asphalt'

    def __init__(self, rate_single, rate_double):
        self.rate_single = rate_single
        self.rate_double = rate_double

    def _choose_label(self):
        r = rnd.random()
        if r < .1:
            return self.rock
        elif r < .2:
            return self.asphalt
        elif r < .6:
            return self.woodland
        else:
            return self.dirt

    def annotation(self):
        labels = []
        if rnd.random() < self.rate_single:
            label = self._choose_label()
            labels.append((label, rnd.randint(1, 10) / 10.0))
            if label != self.asphalt:  # asphalt must be unique label
                if rnd.random() < self.rate_double:
                    if label == self.rock or label == self.dirt:  # only woodland with rock or dirt
                        labels.append((self.woodland, rnd.randint(1, 10) / 10.0))
                    else:  # woodland case
                        new_label = self._choose_label()
                        while new_label == self.asphalt or new_label == label:
                            new_label = self._choose_label()
                        labels.append((new_label, rnd.randint(1, 10) / 10.0))
        else:
            labels.append(('none', 1))
        return labels

    def set_labels_to_segments(self):
        engine = create_engine('postgresql://postgres:root@localhost/hiking', echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()

        segments = session.query(model.Segment)
        for segment in segments:
            labels = self.annotation()
            segment.labels = []
            for l in labels:
                segment.labels.append(model.Label(label=l[0], label_rate=l[1]))
            session.add(segment)
        session.commit()
