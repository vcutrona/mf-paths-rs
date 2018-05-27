# coding=utf-8
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

import pickle
import random
from itertools import combinations

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import recommendation.recommender as rs
from MetricsEngine import MetricEngine
from model import model
from recommendation.recommender import Recommender


class Evaluator:

    def __init__(self, filename='survey_results.csv'):
        self.df = Evaluator._read_csv_report(filename)
        engine = create_engine('postgresql://postgres:root@localhost/hiking', echo=False)
        Session = sessionmaker(bind=engine)
        self.session = Session()

        self.models = [Recommender.g_local_sim, Recommender.local_sim, Recommender.global_sim, 'random']
        self.ndcg_ks = [5, 10]
        self.baselines = [False, True]

    @staticmethod
    def _read_csv_report(filename):
        df = pd.read_csv(filename)
        df['user'] = df['user'].astype(int)
        df['interest'] = df['interest'].astype(float)
        df.ix[:, 6:36] = df.ix[:, 6:36].astype(float)
        return df

    def _get_survey_users(self):
        users = []
        for index, row in self.df.iterrows():
            gis_user = model.User()
            gis_user.id = row['user']
            user_profile = self.df[self.df['user'] == row['user']].ix[:, 6:10].values[0]
            s = sum(user_profile)
            user_profile = [float(i)/s for i in user_profile]
            gis_user.rock = user_profile[3]
            gis_user.dirt = user_profile[1]
            gis_user.woodland = user_profile[2]
            gis_user.asphalt = user_profile[0]
            gis_user.ranking_list = row.tolist()[10:36]
            gis_user.survey_time = row['time']
            self.session.query(model.User).filter(model.User.id == row['user']).delete()
            self.session.add(gis_user)
            users.append(gis_user)
        self.session.commit()
        return users

    @staticmethod
    def _avg_ndcg(k, users):
        users_ndcg = 0.
        for user in users:
            users_ndcg += MetricEngine.ndcg_at_k(user.ranking_list, k)
        return users_ndcg / float(len(users))

    @staticmethod
    def _avg_ndcg_random(k, users, iterations=1000):
        users_ndcg = 0.
        for i in range(0, iterations):
            for user in users:
                random.shuffle(user.ranking_list)
                users_ndcg += MetricEngine.ndcg_at_k(user.ranking_list, k)
        return users_ndcg / float(len(users)*iterations)

    def _get_users_with_ranking_list(self, method, baseline=False):

        try:
            with open('users_pickle/users_{}_{}.pkl'.format(method, baseline), 'rb') as userfile:
                return pickle.load(userfile)
        except IOError:
            print 'File users not found.'
            pass

        users = self._get_survey_users()

        for user in users:
            my_position = dict(latitude=45.86432820440195, longitude=9.488129491092195)
            r = rs.Recommender(50, 3500, 4000, my_position, user.id)
            final_paths = r.recommend(method, baseline)
            user_row = self.df[self.df.user == user.id]

            my_ranking_list = []
            for path, length, similarity in final_paths:
                segments_string = ""
                for segment in path:
                    segments_string += segment.name + " "

                path_name = self.session.query(model.Path.name)\
                    .filter(model.Path.segments == segments_string)\
                    .all()[0][0].encode('ascii', 'ignore')
                my_ranking_list += user_row[path_name].tolist()
            user.ranking_list = my_ranking_list

        with open('users_pickle/users_{}_{}.pkl'.format(method, baseline), 'wb') as userfile:
            pickle.dump(users, userfile)
        return users

    def _filter_users(self, users, mode=None):
        if mode == 'interested':
            interested_users_id = self.df[self.df.interest > 2]['user'].tolist()
            interested_users = []
            for user in users:
                if user.id in interested_users_id:
                    interested_users.append(user)
            return interested_users
        elif mode == 'expert':
            expert_users_id = self.df[self.df.interest > 2]
            expert_users_id = expert_users_id[
                expert_users_id.frequency.isin(['4 times', 'More than 4 times'])]['user'].tolist()
            expert_users = []
            for user in users:
                if user.id in expert_users_id:
                    expert_users.append(user)
            return expert_users
        else:
            return users

    def evaluate(self):
        df = pd.DataFrame()

        for m in self.models:
            for b in self.baselines:
                all_users = self._get_users_with_ranking_list(m, baseline=b)
                int_users = self._filter_users(all_users, 'interested')
                prac_users = self._filter_users(all_users, 'expert')
                scores = []
                idx = []
                for k in self.ndcg_ks:
                    idx.append('NDCG@{} ALL ({}):'.format(k, len(all_users)))
                    idx.append('NDCG@{} INT ({}):'.format(k, len(int_users)))
                    idx.append('NDCG@{} EXP ({}):'.format(k, len(prac_users)))
                    if m == 'random':
                        scores.append(self._avg_ndcg_random(k, all_users))
                        scores.append(self._avg_ndcg_random(k, int_users))
                        scores.append(self._avg_ndcg_random(k, prac_users))
                    else:
                        scores.append(self._avg_ndcg(k, all_users))
                        scores.append(self._avg_ndcg(k, int_users))
                        scores.append(self._avg_ndcg(k, prac_users))
                df['idx'] = idx
                col_m = m
                if b:
                    col_m += 'baseline'
                df[col_m] = scores

        df = df.set_index('idx')
        return df

    def paths_stats(self):
        user = self._get_survey_users()[0]  # Paths are the same for all users
        my_position = dict(latitude=45.86432820440195, longitude=9.488129491092195)
        r = rs.Recommender(50, 3500, 4000, my_position, user.id)
        final_paths = r.get_candidate_paths()

        length_km = []
        common_segments = []
        segments = {}
        for pair in combinations(final_paths, 2):
            segments1 = map(lambda s: s.name, pair[0][0])
            segments2 = map(lambda s: s.name, pair[1][0])
            common_segments.append(len(list(set(segments1[1:]).intersection(segments2[1:]))))
        common_segments_avg = np.mean(common_segments)
        segments_length = map(lambda p: len(p[0][1:]), final_paths)

        segments_length_avg = np.mean(segments_length)
        print 'Avg common segments', float(common_segments_avg) / float(segments_length_avg)

        num_segments = []
        for path, length in final_paths:
            for segment in path:
                if segment.name not in segments.keys():
                    segments[segment.name] = 0
                segments[segment.name] += 1
            length_km.append(length / 1000.0)
            num_segments.append(len(path))

        print '#Paths: ', len(final_paths)
        print '#Segments:', len(segments)
        print 'Average reuse:', np.mean(segments.values())
        print 'Max reuse:', np.max(segments.values())
        print 'Min reuse:', np.min(segments.values())
        print 'Average path length:', np.mean(length_km), 'km'
        print 'Max path length:', np.max(length_km), 'km'
        print 'Min path length:', np.min(length_km), 'km'
        print 'Avg segments per path:', np.mean(num_segments)
        print 'Min segments per path:', np.min(num_segments)
        print 'Max segments per path:', np.max(num_segments)
