#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 21 19:39:45 2017

@author: leo
"""
import copy
import itertools
import os
import time

import pandas as pd
import unidecode
from werkzeug.utils import secure_filename

from abstract_data_project import AbstractDataProject, MINI_PREFIX
from CONFIG import NORMALIZE_DATA_PATH
from MODULES import NORMALIZE_MODULES, NORMALIZE_MODULE_ORDER, NORMALIZE_MODULE_ORDER_log # TODO: think about these...

class Normalizer(AbstractDataProject):
    """
    Abstract class to deal with data, data transformation, and metadata.
    
    SUMMARY:
        This class allows to load user data and perform inference or 
        transformations. Before and after transformation, data is stored in 
        memory as Pandas DataFrame. Transformations are only written to disk if
        write_data is called. A log that describes the changes made to the 
        data in memory is stored in log_buffer. Agter writing data, you should
        also write the log_buffer (write_log_buffer) and run_info_buffer 
        (write_log_info_buffer) to log the changes that were performed.
    
    In short: Objects stored in memory are:
        - TODO: write this
    """
    MODULES = NORMALIZE_MODULES
    CHARS_TO_REPLACE = [' ', ',', '.', '(', ')', '\'', '\"', '/']
    
#==============================================================================
# Actual class
#==============================================================================   

    def __init__(self, project_id=None, create_new=False, description=None, display_name=None):
        super().__init__(project_id, create_new, description, display_name=display_name)

    def create_metadata(self, description=None, display_name=None):
        metadata = super().create_metadata(description=description, 
                                            display_name=display_name)
        # For dicts below, keys are file_names
        metadata['column_tracker'] = None
        metadata['files'] = dict() # Contains single file metadata
        metadata['has_mini'] = False
        metadata['log'] = {}
        return metadata   
    
    def __repr__(self):
        string = '{0}({1})'.format(self.__class__.__name__, self.project_id)
        return string
    
    def __str__(self):
        string = self.__repr__()
        for file_name, logs in self.metadata['log'].items():
            completed = []
            not_completed = []
            for module_name, log in logs.items():
                if log['completed']:
                    completed.append(module_name)
                else:
                    not_completed.append(module_name)
            string += '\n\nFile {0}:\n  Completed:\n  {1}\n  Not completed:\n  {2}'.format(file_name, completed, not_completed)                    
        return string


    def default_log(self):
        '''Default log for a new file'''
        return {module_name: copy.deepcopy(self.default_module_log) for module_name in NORMALIZE_MODULE_ORDER_log}
        
    def load_data(self, module_name, file_name, nrows=None, columns=None, restrict_to_selected=True):
        assert (columns is None) or (not restrict_to_selected)
        if restrict_to_selected:
            columns = self.metadata['column_tracker']['selected']
        super().load_data(module_name=module_name, 
                         file_name=file_name, 
                         nrows=nrows, 
                         columns=columns)
    
    def time_since_created(self):
        return time.time() - float(self.metadata['timestamp'])
    
    # TODO: add shared to metadata
    # TODO: change this in generic using get_last...
    def time_since_last_action(self):
        last_time = float(self.metadata['timestamp'])
        if self.metadata['log']:
            last_time = max(last_time, float(self.metadata['log'][-1]['end_timestamp']))
        return time.time() - last_time


    def _list_files(self, extensions=['.csv']):
        '''
        Lists csv files (from data) in data directory and presents a list of modules in 
        which they are present. You can combine this with get_last_written
        '''
        def is_dir(root_path, x):
            return os.path.isdir(os.path.join(root_path, x))
        
        all_files = dict()
        root_path = self.path_to()
        for _dir in filter(lambda x: is_dir(root_path, x), os.listdir(root_path)):
            for file_name in os.listdir(os.path.join(root_path, _dir)):
                if any(file_name[-len(ext):] == ext for ext in extensions):
                    if file_name not in all_files:
                        all_files[file_name] = [_dir]
                    else:
                        all_files[file_name].append(_dir)
        return all_files

    def log_by_file_name(self):
        # Sort by name and date        
        sorted_log = sorted(self.metadata['log'], key=lambda x: (x['file_name'], 
                                x['start_timestamp']))
        
        resp = dict()
        for key, group in itertools.groupby(sorted_log, lambda x: x['file_name']):
            resp[key] = list(group)
        return resp

    def get_last_written(self, module_name=None, file_name=None, 
                         before_module=None):
        '''
        Return info on data that was last successfully written (from log)
        
        INPUT:
            - module_name: filter on given module
            - file_name: filter on file_name
            - before_module: (string with module name) Looks for file that was 
                              written in a module previous to before_module 
                              (in the order defined by NORMALIZE_MODULE_ORDER)
            
        OUTPUT:
            - (module_name, file_name)
        '''        
        if (module_name is not None) and (before_module is not None):
            raise Exception('Variables module_name and before_module cannot be \
                            set simultaneously')

        if module_name is not None:
            modules_to_search = [module_name]
        else:        
            previous_modules = {NORMALIZE_MODULE_ORDER[i]: NORMALIZE_MODULE_ORDER[:i] for i in range(len(NORMALIZE_MODULE_ORDER))}
            previous_modules[None] = NORMALIZE_MODULE_ORDER
            modules_to_search = previous_modules[before_module][::-1]
        
        if file_name is None:
            file_name = self.metadata['last_written']['file_name']
        
        for module_name in modules_to_search:
            log = self.metadata['log'][file_name][module_name]
            if (not log.get('error', False)) and (log.get('written', False)):
                break
        else:
            raise Exception('No written data could be found in logs')
            
        module_name = log['module_name']
        file_name = log['file_name']        
        return (module_name, file_name)


    def path_to_last_written(self, module_name=None, file_name=None, before_module=None):
        (module_name, file_name) = self.get_last_written(module_name,
                                                        file_name, before_module)
        path = self.path_to(module_name, file_name)
        return path
        
    def safe_filename(self, file_name, ext='.csv'):
        assert file_name[-len(ext):] == ext
        return secure_filename(file_name)


    def read_csv(self, file, chars_to_replace):
        ENCODINGS = ['utf-8', 'windows-1252']
        SEPARATORS = [',', ';', '\t']
        
        could_read = False
        for encoding in ENCODINGS:
            for sep in SEPARATORS:
                try:
                    # Just read column name and first few lines for encoding
                    tab_part = pd.read_csv(file, 
                                           sep=sep, 
                                           encoding=encoding, 
                                           dtype=str)
                    columns = tab_part.columns
                    
                    try:
                        file.seek(0)
                    except:
                        pass # TODO: really? try except? really??
                    
                    # Create actual generator
                    tab = pd.read_csv(file, 
                                         sep=sep, 
                                         encoding=encoding, 
                                         dtype=str, 
                                         chunksize=self.CHUNKSIZE)
                    could_read = True
                    break
                except Exception as e:
                    print(e)
                    file.seek(0)
            if could_read:
                break
            
        if not could_read:
            raise Exception('Separator and/or Encoding not detected. Try uploading \
                            a csv with "," as separator with utf-8 encoding')            
            
        return tab, sep, encoding, columns
    
    def read_excel(self, file, chars_to_replace):
        # TODO: add iterator and return columns
        excel_tab = pd.read_excel(file, dtype=str)
        columns = excel_tab.columns
        
        def make_gen(excel_tab, chunksize):
            cursor = 0
            chunk = excel_tab.iloc[:chunksize]
            while chunk.shape[0]:
                yield chunk
                cursor += chunksize
                chunk = excel_tab.iloc[cursor:cursor+chunksize]
        tab = make_gen(excel_tab, self.CHUNKSIZE) 
    
        return tab, None, None, columns


    def upload_init_data(self, file, file_name, user_given_name=None):
        # TODO: deal with og_file_name, file_id, display_name, user_given_name
        """
        Upload and write source or reference to the project. Tables will
        be added to the "INIT" module.
        
        The file will be re-coded in utf-8 with a "," separator. Also, chars
        specified in CHARS_TO_REPLACE will be replaced by "_" in the header.
        """
        chars_to_replace = self.CHARS_TO_REPLACE
        
        # Check that 
        if self.metadata['files']:
            raise Exception('Cannot upload multiple files to the same project anymore :(')
        

        og_file_name = file_name

        base_name = secure_filename(file_name.rsplit('.')[0])
        extension = file_name.rsplit('.')[-1]
        file_name = base_name + '.csv'

        if extension not in ['csv', 'xls', 'xlsx']:
            raise Exception('file name (and user given name) should end with .csv , .xls , or .xlsx or .zip')
            
    
        self.mem_data_info = {
                                'file_name': file_name,
                                'og_file_name': og_file_name,
                                'module_name': 'INIT'
                             }
        
        # Check that file name is not already present 
        if file_name in self.metadata['files']:
            raise Exception('File: {0} already exists. Delete this file ' \
                             + 'or choose another name'.format(file_name))
        
        log = self.init_active_log('INIT', 'transform')

        if extension == 'csv':
            self.mem_data, sep, encoding, columns = self.read_csv(file, chars_to_replace)
            file_type = 'csv'

        else:
            self.mem_data, sep, encoding, columns = self.read_excel(file, chars_to_replace)
            file_type = 'excel'
            
        if len(set(columns)) != len(columns):
            raise Exception('Column names should all be different')

        # Add file to metadata
        self.metadata['files'][file_name] = {
                                                'og_file_name': og_file_name,
                                                'upload_time': time.time()
                                            }
        
        if self.metadata['column_tracker'] is None:
            self.metadata['column_tracker'] = {'original': list(columns),  # As in the original file
                                              'selected': list(columns), 
                                              'created': []}
        else:
            assert list(self.mem_data.columns) == self.metadata['column_tracker']['original']
                
        # Create new empty log in metadata
        self.mem_data_info['file_name'] = file_name
        self.metadata['log'][file_name] = self.default_log()
                
        # Complete log
        log = self.end_active_log(log, error=False)
                          
        # Update log buffer
        self.log_buffer.append(log)
        
        # Write configuration (sep, encoding) to INIT dir
        config_dict = {
                        'file_name': file_name,
                        'og_file_name': og_file_name,
                        'file_type': file_type, 
                        'sep': sep, 
                        'encoding': encoding, 
                        'ncols': len(columns)
                    }
        self.run_info_buffer[('INIT', file_name)] = config_dict
        # TODO: duplicate with run_info and infered_config.json        
        
        # write data and log
        config_dict['nrows'] = self.write_data()

        self.upload_config_data(config_dict, 'INIT', 'infered_config.json')

        self.clear_memory()    
                
        return None, config_dict

    def add_selected_columns(self, columns):
        '''
        Select the columns to normalize on. Will clear all changes if more columns 
        are selected than previously (clean_after)
        '''
        # Check that columns were selected
        if not columns:
            raise ValueError('Select at least one column')
        
        # Check that selected columns are in the original header
        for col in columns:
            if col not in self.metadata['column_tracker']['original']:
                raise ValueError('Selected column {0} is not in uploaded header (can be different from the original file)\n --> uploaded header: ({1})'.format(\
                                col, self.metadata['column_tracker']['original']))
        
        # If a selected column was not previously selected, delete all 
        # pre-existing files. Because we will have to re-run processing 
        if any(col not in self.metadata['column_tracker']['selected'] for col in columns):
            for file_name in self.metadata['files']:
                self.clean_after('INIT', file_name, include_current_module=False)

        # Add to log
        for file_name in self.metadata['log']:
            self.metadata['log'][file_name]['add_selected_columns']['completed'] = True
        
        # Add selected columns to metadata
        self.metadata['column_tracker']['selected'] = columns
        
        self.write_metadata()   

    def read_selected_columns(self):
        return self.metadata['column_tracker']['selected']
        
    def remove_all(self, file_name):
        '''
        Remove all occurences of files with a given file_name from the project
        and clears all mentions of this file_name in metadata
        '''
        # TODO: deal with .csv dependency
        all_files = self._list_files(extensions=['.csv'])
    
        for _file_name, module_name in  all_files.items():
            if file_name == _file_name:
                self.remove(module_name, file_name)
        
        self.metadata['log'][file_name] = self.default_log()
        self.write_metadata()

    def clean_after(self, module_name, file_name, include_current_module=True):
        '''
        Removes all occurences of file and transformations
        at and after the given module (NORMALIZE_MODULE_ORDER)
        '''
        # TODO: move to normalize
        
        if file_name not in self.metadata['log']:
            # TODO: put warning here instead
            pass
            # raise Exception('This file cannot be cleaned: it cannot be found in log')
        
        start_idx = NORMALIZE_MODULE_ORDER_log.index(module_name) + int(not include_current_module)
        for iter_module_name in NORMALIZE_MODULE_ORDER_log[start_idx:]:            
            # module_log = self.metadata['log'][file_name]
            # TODO: check skipped, written instead of try except            
            
            file_path = self.path_to(iter_module_name, file_name)
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass
            
            try:
                self.metadata['log'][file_name][iter_module_name] = copy.deepcopy(self.default_module_log)
            except:
                pass
            self.write_metadata()
    
    def concat_with_init(self):
        '''
        Concatenates original table to data in memory (changes column names as well)
        
        TODO: merge with transform
        '''
        chars_to_replace = self.CHARS_TO_REPLACE
        
        self.check_mem_data()
        
        # Initiate log
        log = self.init_active_log('concat_with_init', 'transform')
    
        og_file_name = self.mem_data_info['file_name']
        og_file_path = self.path_to('INIT', og_file_name)
        og_tab, _, _, _ = self.read_csv(og_file_path, chars_to_replace)
            
        def rename_column(col):
            if '__' in col:
                return col
            else:
                return col + '__NORMALIZED'
    
        def my_concat(og_data, data):
            data.columns = [rename_column(col) for col in data.columns]
            data = pd.concat([og_data, data], 1)
        
            # Re-order columns
            columns = []
            for col in og_data.columns:
                columns.append(col)
                modified_cols = filter(lambda x: col + '__' in x, og_data.columns)
                columns.extend(modified_cols)
            data = data[columns]
            return data
        
        self.mem_data = (my_concat(og_data, data) for og_data, data in zip(og_tab, self.mem_data))
        
        self.mem_data_info['module_name'] = 'concat_with_init'
        
        run_info = {} # TODO: check specifications for run_info

        # Complete log
        log = self.end_active_log(log, error=False)
                          
        # Add time to run_info (# TODO: is this the best way?)
        run_info['start_timestamp'] = log['start_timestamp']
        run_info['end_timestamp'] = log['end_timestamp']
        run_info['params'] = {}
        
        # Update buffers
        self.log_buffer.append(log)
        self.run_info_buffer[('concat_with_init', og_file_name)] = run_info        
        return log, run_info
    
    def transform(self, module_name, params):
        '''Overwrite transform from AbstractDataProject to be able to use concat_with_init'''       
        if module_name == 'concat_with_init':
            return self.concat_with_init()
        else:
            return super().transform(module_name, params)
            
    def run_all_transforms(self):
        '''Runs all modules on data in memory. And config from module names
        # TODO: move to abstract_data_project ?
        '''
        self.check_mem_data()
        
        all_run_infos = {}
        # Only run all if there is a MINI version of the file # TODO: check that this is valid
        if self.metadata['has_mini']:
            for module_name in NORMALIZE_MODULE_ORDER:
                if self.MODULES['transform'][module_name].get('use_in_full_run', False):
                    try:
                        run_info_name = MINI_PREFIX + self.mem_data_info['file_name'] + '__run_info.json'
                        
                        # TODO: deal with this
                        if module_name != 'concat_with_init':
                            params = self.read_config_data(module_name, run_info_name)['params']
                        else:
                            params = None
                        
                        # Load parameters from config files
                        _, run_info = self.transform(module_name, params)
                    except: 
                        run_info = {'skipped': True, }
                        print('WARNING: MODULE {0} WAS NOT RUN'.format(module_name))
                        # TODO: warning here
                    all_run_infos[module_name] = run_info
        return all_run_infos



class UserNormalizer(Normalizer):
    def path_to(self, module_name='', file_name=''):
        return self._path_to(NORMALIZE_DATA_PATH, module_name, file_name)
    
class InternalNormalizer(Normalizer):
    def path_to(self, module_name='', file_name=''):
        return self._path_to(NORMALIZE_DATA_PATH, module_name, file_name)
    




if __name__ == '__main__':
    import logging

    source_file_name = 'source.csv' # 'SIREN_FUI.col' # 'abes.csv'
    user_given_name = 'second_file.csv'

    logging.basicConfig(filename = 'log/preprocess_fields.log', level = logging.DEBUG)
    
    # Create/Load a project
    #project_id = "4e8286f034eef40e89dd99ebe6d87f21"
    proj = UserNormalizer(None, create_new=True)
    
    # Upload file to normalize
    file_path = os.path.join('local_test_data', source_file_name)
    with open(file_path) as f:
        proj.upload_init_data(f, source_file_name, user_given_name)

    # Select only interesting columns
    #    proj.add_selected_columns([
    #                                'numero_uai', 'patronyme_uai',
    #                               'localite_acheminement_uai', 'departement',
    #                               'code_postal_uai'])


    # Load source data to memory
    proj.load_data(module_name='INIT' , file_name=user_given_name)
    
    
    infered_mvs = proj.infer('infer_mvs', params=None)
    
    proj.transform('replace_mvs', params=infered_mvs)
    
    #    inferredTypes = proj.infer('infer_types', params = None)
    #    
    #    print('Inferred data types:', inferredTypes)
    #
    #    proj.transform('recode_types', inferredTypes)
    
    # Write transformed file
#    assert False
#    print('Rows written', proj.write_data())
#    proj.write_log_buffer(written=True)
#    proj.write_run_info_buffer()
#    
#    assert False
    
    # Concat with init
    proj.concat_with_init()
    proj.write_data()
    proj.write_log_buffer(written=True)
    proj.write_run_info_buffer()
    
    # Remove previously uploaded file
    # proj.remove_data('source', 'INIT', 'source.csv')    

