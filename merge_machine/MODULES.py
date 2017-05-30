#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 24 17:18:28 2017

@author: leo
"""

from dedupe_linker import dedupe_linker
from performance import results_analysis
from infer_nan import infer_mvs, replace_mvs, sample_mvs_ilocs
from preprocess_fields_v3 import inferTypes, normalizeValues, sample_types_ilocs

NORMALIZE_MODULE_ORDER = ['INIT', 'replace_mvs', 'normalizeValues', 'concat_with_init']

MODULES = {
        'transform':{
                    'INIT': {
                                'desc': 'Initial upload (cannot be called)'                            
                            },
                    'replace_mvs': {
                                'func': replace_mvs,
                                'desc': replace_mvs.__doc__
                            },
                    'normalizeValues': {
                               'func':  normalizeValues,
                               'desc': normalizeValues.__doc__
                           },
                    'concat_with_init': {
                               'desc': 'Merge intial and transformed files (cannot be called)'
                           }
                    },
        'infer':{
                'infer_mvs': {
                                'func': infer_mvs,
                                'write_to': 'replace_mvs',
                                'desc': infer_mvs.__doc__
                            },
              'inferTypes': {
                               'func': inferTypes,
                               'write_to': 'normalize',
                               'desc': inferTypes.__doc__
                           },
              'results_analysis': {
                                'func': results_analysis,
                                'write_to': 'results_analysis',
                                'desc': results_analysis.__doc__
                            }
                },
        'link': {
                'dedupe_linker': {
                                'func': dedupe_linker,
                                'desc': dedupe_linker.__doc__
                            }
                },
        'sample': {
                'sample_mvs': {
                        'func': sample_mvs_ilocs,
                        'desc': sample_mvs_ilocs.__doc__
                        },
                'sample_types': {
                        'func': sample_types_ilocs,
                        'desc': sample_types_ilocs.__doc__
                        }
                }
        }
                
# Sanity check
for module_from_loop in NORMALIZE_MODULE_ORDER:
    assert (module_from_loop in MODULES['transform']) \
        or (module_from_loop in MODULES['link'])