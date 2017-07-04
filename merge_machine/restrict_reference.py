#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 21 16:13:02 2017
@author: leo

Try to infer properties of the reference file based on given matches (from manual 
training or exact match on a given field). In particular: guess words that 
SHOULD be present in a given column. You can then restrict the reference to 
lines that ALL contain these words.

For example: if source only contains companies listed in departement:"Essonne" 
in the reference for training matches, you can suggest that we should only 
search for matches within rows of the reference that have departement:"Essonne"

# TODO: Add threshold for value presence to account for user mistake

"""

import pandas as pd

#==============================================================================
# Generic functions to restrict reference
#==============================================================================

def find_common_words(ref_match, cols=None):
    """
    Use on result of training and/or exact match to infer common words in 
    columns to restrict matching to a subset of the data. 
    
    INPUT:
        - ref_match: pandas DataFrame to consider
        - cols: (defaults to None) columns in which too look for common words
                None will use all columns except for "_has_match"
    
    OUTPUT: 
        - all_candidate_words: dict with key the column name and value a list
                               of words in common
    """
    if cols is None:
        cols = [x for x in ref_match.columns if x != '_has_match']
    
    all_candidate_words = dict()
    for col in cols:
        all_candidate_words[col] = _find_common_words_in_col(ref_match, col)
    return all_candidate_words
   
def _find_common_words_in_col(ref_match, col):
    """
    Finds words that are present in all values of the column specified by col.
    """
    all_words = pd.Series(ref_match[col].str.cat(sep=' ').split()).value_counts()
    sel = all_words >= len(ref_match)
    common_words = []
    for word in all_words[sel].index:
        if ref_match[col].str.contains(word).all():
            common_words.append(word)
    return common_words    

def find_common_vals(ref_match, cols=None):
    """
    Use on result of training and/or exact match to infer common exact values
    in columns to restrict matching to a subset of the data. 
    
    INPUT:
        - ref_match: pandas DataFrame to consider
        - cols: (defaults to None) columns in which too look for common words
                None will use all columns except for "_has_match"
    
    OUTPUT: 
        - all_candidate_words: dict with key the column name and value a list
                               of words in common
    """
    if cols is None:
        cols = [x for x in ref_match.columns if x != '_has_match']    

    all_candidate_values = dict()
    for col in cols:
        if (ref_match[col] == ref_match[col].iloc[0]).all():
            all_candidate_values[col] = ref_match[col].iloc[0]
        else:
            all_candidate_values[col] = None
    return all_candidate_values


def filter_by_words(ref, col_words):
    """
    Filters rows in ref by words specified in col_words
    
    INPUT:
        - ref: pandas DataFrame
        - col_words: dictionnary mapping lists_of words to columns (same as 
                    output of find_common_words). Specifies the words to look 
                    for in each column (to keep).
    OUTPUT:
        - ref: table filtered by words to keep for each column
        - run_info: original table length and new length
    """
    
    run_info = {'og_len': len(ref)}
    run_info['has_modifications'] = False
    
    for col, words in col_words.iteritems():
        for word in words:
            ref = ref[ref[col].str.contains(word)]
            run_info['has_modifications'] = True            
            
    run_info['new_len'] = len(ref)
    return ref, run_info


def filter_by_vals(ref, col_vals):
    """
    Filters rows in ref by words specified in col_words
    
    INPUT:
        - ref: pandas DataFrame
        - col_vals: dictionnary mapping values to columns (same as 
                    output of find_common_vals). Specifies the value to look 
                    for in each column (to keep).
    OUTPUT:
        - ref: table filtered by words to keep for each column
        - run_info: original table length and new length
    """
    run_info = {'og_len': len(ref)}
    run_info['has_modifications'] = False
    
    for col, val in col_vals.iteritems():
        if val is not None:
            ref = ref[ref[col] == val]
            run_info['has_modifications'] = True 
            
    run_info['new_len'] = len(ref)
    return ref, run_info

#==============================================================================
# Project specific module
#==============================================================================

def training_to_ref_df(training):
    '''
    Takes as input a dedupe training file and returns a pandas DataFrame with
    the data corresponding to match samples in the referential.
    '''
    training_df = pd.DataFrame([x['__value__'][1] for x in training['match']])
    return training_df

if __name__ == '__main__':
    from linker import UserLinker
    
    project_id = '78246d462d500c1234903cc338c7c495'    
    proj = UserLinker(project_id)    
    training = proj.read_config_data('dedupe_linker', 'training.json')    
    
    training_df = training_to_ref_df(training)
    common_words = find_common_words(training_df)
    common_vals = find_common_vals(training_df)