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

from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


# ORM mapping with segment table
class Segment(Base):
    __tablename__ = 'segment_py'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    geom = Column(Geometry())
    labels = relationship('Label', back_populates="segment")
    length = 0

    def get_properties_vector(self):
        d = {'rock': 0, 'dirt': 0, 'woodland': 0, 'asphalt': 0}
        for label in self.labels:
            d[label.label] = label.label_rate
        return [d['rock'], d['dirt'], d['woodland'], d['asphalt']]


class Label(Base):
    __tablename__ = 'segment_label_py'
    id = Column(Integer, primary_key=True)
    label = Column(String)
    label_rate = Column(Float)
    segment_id = Column(Integer, ForeignKey('segment_py.id'))
    segment = relationship("Segment", back_populates="labels")


class User(Base):
    __tablename__ = 'user_py'
    id = Column(Integer, primary_key=True)
    rock = Column(Float)
    dirt = Column(Float)
    woodland = Column(Float)
    asphalt = Column(Float)
    ranking_list = []
    survey_time = 0.

    def get_profile(self):
        return [self.rock, self.dirt, self.woodland, self.asphalt]


class Path(Base):
    __tablename__ = 'survey_path_py'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    segments = Column(String)
    length = Column(Float)

    def __eq__(self, other):
        return self.segments == other.segments
