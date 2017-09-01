#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  1 21:10:15 2017

@author: m75380
"""

import logging
import os

# Change current path to path of api.py
curdir = os.path.dirname(os.path.realpath(__file__))
os.chdir(curdir)

from normalizer import UserNormalizer, ESReferential
from linker import UserLinker
    
    
def _infer_mvs(project_id, data_params, module_params):
    '''
    Runs the infer_mvs module
    
    wrapper around UserNormalizer.infer ?
    
    ARGUMENTS (GET):
        project_id: ID for "normalize" project

    ARGUMENTS (POST):
        - data_params: {
                "module_name": module to fetch from
                "file_name": file to fetch
                }
        - module_params: none
    
    '''
    proj = UserNormalizer(project_id=project_id)
    proj.load_data(data_params['module_name'], data_params['file_name'])    
    result = proj.infer('infer_mvs', module_params)
        
    # Write log
    proj.write_log_buffer(False)
    return result


def _replace_mvs(project_id, data_params, module_params):
    '''
    Runs the mvs replacement module
    
    ARGUMENTS (GET):
        project_id: ID for "normalize" project

    ARGUMENTS (POST):
        - data_params: {
                "module_name": module to fetch from
                "file_name": file to fetch
                }
        - module_params: same as result of infer_mvs
    '''
    proj = UserNormalizer(project_id=project_id)

    proj.load_data(data_params['module_name'], data_params['file_name'])
    
    _, run_info = proj.transform('replace_mvs', module_params)
    
    # Write transformations and log
    proj.write_data()
    return run_info

def _infer_types(project_id, data_params, module_params):
    '''
    Runs the infer_types module
    
    wrapper around UserNormalizer.infer ?
    
    ARGUMENTS (GET):
        project_id: ID for "normalize" project

    ARGUMENTS (POST):
        - data_params: {
                "module_name": module to fetch from
                "file_name": file to fetch
                }
        - module_params: none
    
    '''
    proj = UserNormalizer(project_id=project_id)
    proj.load_data(data_params['module_name'], data_params['file_name'])    
    result = proj.infer('infer_types', module_params)
        
    # Write log
    proj.write_log_buffer(False)
    return result


def _recode_types(project_id, data_params, module_params):
    '''
    Runs the recoding module
    
    ARGUMENTS (GET):
        project_id: ID for "normalize" project

    ARGUMENTS (POST):
        - data_params: {
                "module_name": module to fetch from
                "file_name": file to fetch
                }
        - module_params: same as result of infer_mvs
    '''
    proj = UserNormalizer(project_id=project_id)

    proj.load_data(data_params['module_name'], data_params['file_name'])
    
    _, run_info = proj.transform('recode_types', module_params)
    
    # Write transformations and logs
    proj.write_data()

    return run_info

def _es_linker(project_id, data_params, module_params):
    '''
    Runs the recoding module
    
    ARGUMENTS (GET):
        project_id: ID for "normalize" project

    ARGUMENTS (POST):
        - data_params: 
            none
                {
                "module_name": module to fetch from (source)
                "file_name": file to fetch (source)
                }
        - module_params: {
                "index_name": name of the Elasticsearch index to fetch from
                "query_template": 
                "threshold": minimum value of score for this query_template for a match
                "must": terms to filter by field (AND: will include ONLY IF ALL are in text)
                "must_not": terms to exclude by field from search (OR: will exclude if ANY is found)
                }
    '''
    # Problem: what project are we talking about? what ID? 
    
    assert False
    # proj = UserLinker(project_id=project_id)
    # proj.load_data(data_params['module_name'], data_params['file_name'])
    
    #_, run_info = proj.link('es_linker', data_params, module_params)
    
    # Write transformations and logs
    proj.write_data()

    return run_info


def _concat_with_init(project_id, data_params, *argv):
    '''
    Concatenate transformed columns with original file 

    ARGUMENTS (GET):
        project_id: ID for "normalize" project

    ARGUMENTS (POST):
        - data_params: file to concatenate to original
                {
                    "module_name": module to fetch from
                    "file_name": file to fetch
                }
                
        - module_params: none
    '''
    proj = UserNormalizer(project_id=project_id)

    # TODO: not clean
    if data_params is None:
        (module_name, file_name) = proj.get_last_written()
    else:
        module_name = data_params['module_name']
        file_name = data_params['file_name']

    proj.load_data(module_name, file_name)
    
    # TODO: there was a pdb here. is everything alright ?
    
    _, run_info = proj.transform('concat_with_init', None)

    # Write transformations and logs
    proj.write_data()
    return run_info

def _run_all_transforms(project_id, data_params, *argv):
    '''
    Run all transformations that were already (based on presence of 
    run_info.json files) with parameters in run_info.json files.

    ARGUMENTS (GET):
        project_id: ID for "normalize" project

    ARGUMENTS (POST):
        - data_params: file to concatenate to original
                {
                    "file_name": file to use for transform (module_name is 'INIT')
                }
    '''
    proj = UserNormalizer(project_id=project_id)

    file_name = data_params['file_name']

    proj.load_data('INIT', file_name)
    all_run_infos = proj.run_all_transforms()

    # Write transformations and logs
    proj.write_data()
    return all_run_infos

def _create_dedupe_labeller(project_id, *argv):
    '''
    Create a "dedupe" labeller and pickle to project
    
    ARGUMENTS (GET):
        - project_id
    
    ARGUMENTS (POST):
        - data_params: none
        - module_params: none
    '''
    
    # TODO: data input in gen_dedupe_labeller ?
    proj = UserLinker(project_id=project_id)
    labeller = proj._gen_dedupe_labeller()
    proj.write_labeller('dedupe_linker', labeller)
    return

def _create_es_index(project_id, data_params, module_params):
    '''
    Create sample version of selected file (call just after upload).
    
    GET:
        - project_id
    POST:
        - data_params: 
                        {
                        module_name:
                        file_name: 
                        }
        - module_params: {
                            columns_to_index: 
                            force: force recreation of index even if existant
                        }
    '''
    
    columns_to_index = module_params.get('columns_to_index')
    force = module_params.get('force', False)
    
    proj = ESReferential(project_id=project_id)
    
    # Default columns_to_index
    if columns_to_index is None:
        default_analyzers = {'french', 'whitespace', 'integers', 'end_n_grams', 'n_grams'}
        column_tracker = proj.ref.metadata['column_tracker']
        columns_to_index = {col: default_analyzers if col in column_tracker['selected'] \
                            else {} for col in column_tracker['original']}    
    
    file_path = proj.ref.path_to(data_params['module_name'], data_params['file_name'])
    proj.create_index(file_path, columns_to_index, force)
    return


def _create_es_labeller(project_id, *argv):
    '''
    Create an "es" labeller and pickle to project
    
    ARGUMENTS (GET):
        - project_id
    
    ARGUMENTS (POST):
        - data_params: none
        - module_params: none
    '''
    proj = UserLinker(project_id=project_id)
    labeller = proj._gen_es_labeller()
    proj.write_labeller('es_linker', labeller)
    return

def _infer_restriction(project_id, _, module_params):
    '''
    Runs the training data and infers possible restrictions that can be made
    on the referential.
    
    ARGUMENTS (GET):
        project_id: ID for "link" project

    ARGUMENTS (POST):
        - data_params: none
        - module_params: {#TODO: fill with params from restrict}
    '''
    if module_params is None:
        module_params = dict()
    
    proj = UserLinker(project_id=project_id)
    training = proj.read_config_data('dedupe_linker', 'training.json')
    if not training:
        raise Exception('No training file was found in this project')
    module_params['training'] = training
    
    result = proj.infer('infer_restriction', module_params)
        
    # Write log
    proj.write_log_buffer(False)
    return result

def _perform_restriction(project_id, _, module_params):
    '''
    Creates a restricted version of the file set as reference in the link
    project and writes it in the link project.
    
    ARGUMENTS (GET):
        project_id: ID for "link" project

    ARGUMENTS (POST):
        - data_params: none
        - module_params: same as result of infer_mvs
    '''
    proj = UserLinker(project_id=project_id)
    
    run_info = proj.perform_restriction(module_params)
    
    return run_info


# In test_linker
def _dedupe_linker(project_id, *argv):
    '''
    Runs deduper module. Contrary to other modules, linker modules, take
    paths as input (in addition to module parameters)
    
    ARGUMENTS (GET):
        project_id: ID for "link" project

    ARGUMENTS (POST):
        - data_params: none
        - module_params: none
        
    # Todo: deprecate
    '''  
    
    proj = UserLinker(project_id=project_id) # Ref and source are loaded by default
    
    paths = proj._gen_paths_dedupe()
    
    col_matches = proj.read_col_matches()
    my_variable_definition = proj._gen_dedupe_variable_definition(col_matches)
    
    module_params = {
                    'variable_definition': my_variable_definition,
                    'selected_columns_from_source': None,
                    'selected_columns_from_ref': None
                    }  
    
    # TODO: This should probably be moved
    logging.info('Performing linking')           
    
    # Perform linking
    proj.linker('dedupe_linker', paths, module_params)

    logging.info('Writing data')
    # Write transformations and log
    proj.write_data()
    
    file_path = proj.path_to(proj.mem_data_info['module_name'], 
                             proj.mem_data_info['file_name'])
    logging.info('Wrote data to: {0}'.format(file_path))

    return {}

def _link_results_analyzer(project_id, data_params, *argv):
    '''
    Runs the link results analyzer module
    
    wrapper around UserNormalizer.infer ?
    
    ARGUMENTS (GET):
        project_id: ID for "normalize" project

    ARGUMENTS (POST):
        - data_params: {
                "module_name": module to fetch from
                "file_name": file to fetch
                }    
    '''
    proj = UserLinker(project_id=project_id)
    proj.load_data(data_params['module_name'], data_params['file_name'])    
    result = proj.infer('link_results_analyzer', {})
    
    # Write log
    proj.write_log_buffer(False)
    return result


def _test_long(*argv):
    print('-->>>>  STARTED JOB')
    import time
    time.sleep(10)
    print('-->>>>  ENDED JOB')
    return