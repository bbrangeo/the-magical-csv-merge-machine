#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  5 20:11:03 2017

@author: leo


{0.1: [0.27793493635077793,
  0.25318246110325321,
  0.29632248939179634,
  0.33804809052333806,
  0.31117397454031115],
 0.2: [0.45544554455445546,
  0.40806223479490805,
  0.25035360678925034,
  0.39886845827439887,
  0.41867043847241869],
 0.3: [0.43635077793493637,
  0.4490806223479491,
  0.55021216407355023,
  0.49717114568599718,
  0.4794908062234795],
 0.4: [0.53606789250353604,
  0.54526166902404527,
  0.51838755304101836,
  0.37340876944837342,
  0.52192362093352196],
 0.5: [0.43988684582743987,
  0.48514851485148514,
  0.60042432814710045,
  0.53606789250353604,
  0.54455445544554459],
 0.6: [0.40240452616690242,
  0.49434229137199437,
  0.52192362093352196,
  0.41654879773691655,
  0.52687411598302691],
 0.7: [0.46817538896746819,
  0.66902404526166903,
  0.52758132956152759,
  0.49929278642149927,
  0.50565770862800563],
 0.8: [0.63295615275813299,
  0.51555869872701554,
  0.34087694483734088,
  0.50636492220650642,
  0.40240452616690242],
 0.9: [0.83026874115983029,
  0.43917963224893919,
  0.53041018387553041,
  0.557991513437058,
  0.4794908062234795]}

"""

import json
import math
import random

from user_project import UserProject


def gen_dedupe_variable_definition(col_matches):
    my_variable_definition = []
    for match in col_matches:
        if (len(match['source']) != 1) or (len(match['ref']) != 1):
            raise Exception('Not dealing with multiple columns (1 source, 1 ref only)')
        my_variable_definition.append({"crf": True, "missing_values": True, "field": 
            {"ref": match['ref'][0], "source": match['source'][0]}, "type": "String"})
    return my_variable_definition


project_id = '7a4ce22c0ccd5d2c348b1b6ee2c43fd7'

source_path = '/home/leo/Documents/eig/merge_machine/merge_machine/data/projects/7a4ce22c0ccd5d2c348b1b6ee2c43fd7/source/replace_mvs/source.csv'
ref_path = '/home/leo/Documents/eig/merge_machine/merge_machine/data/referentials/liste_de_lycees/ref/INIT/ref.csv'
train_path = '/home/leo/Documents/eig/merge_machine/merge_machine/data/projects/7a4ce22c0ccd5d2c348b1b6ee2c43fd7/link/dedupe_linker/training.json'
learned_settings_path = '/home/leo/Documents/eig/merge_machine/merge_machine/data/projects/7a4ce22c0ccd5d2c348b1b6ee2c43fd7/link/dedupe_linker/learned_settings'

paths = {
            'learned_settings': learned_settings_path,
             'ref': ref_path,
             'source': source_path,
             'train': train_path
         }

proj = UserProject(project_id)
col_matches = proj.read_col_matches()
my_variable_definition = gen_dedupe_variable_definition(col_matches)

params = {
        'variable_definition': my_variable_definition,
        'selected_columns_from_source': None,
        'selected_columns_from_ref': None
        }  


with open('local_test_data/rnsr/my_dedupe_rnsr_config.json') as f:
   my_config = json.load(f)    

# Restrict training
with open(paths['train']) as r:
    training = json.load(r)
    num_matches = len(training['match'])
    num_distinct = len(training['distinct'])

props = [x/10. for x in range(1,10)]
props = [0.9]
match_sizes = []
distinct_sizes = []
recalls = {}

# Restrict training
with open(paths['train']) as r:
    training = json.load(r)
    
matches = training['match']
random.shuffle(matches)
distinct = training['distinct']
random.shuffle(distinct)


num_tries = 10
for prop in props:
    recalls[prop] = []
    
    for _ in range(num_tries):
        print('At prop: ', prop)
        new_training = dict()
        new_num_matches = math.ceil(prop*num_matches)
        new_training['match'] = matches[:new_num_matches]
        
        new_num_distinct = math.ceil(prop*num_distinct)
        new_training['distinct'] = distinct[:new_num_distinct]
            
        path_restricted_train = paths['train'] + '_temp'
        with open(path_restricted_train, 'w') as w:
            json.dump(new_training, w)  
        
        paths['train'] =  path_restricted_train   
        
        
        proj.linker('dedupe_linker', paths, params)
        source = proj.mem_data
        
        # Explore results
        match_rate = source.__CONFIDENCE.notnull().mean()
        print('Match rate', '-->', match_rate)

        recalls[prop].append(match_rate)
        match_sizes.append(new_num_matches)
        distinct_sizes.append(new_num_distinct)
       
        if match_rate >= 0.75:
            break
        


assert False

source.sort_values(by='__CONFIDENCE', inplace=True)
cols = ['commune', 'localite_acheminement_uai', 'lycees_sources', 
        'patronyme_uai', '__CONFIDENCE']