# -*- coding: utf-8 -*-
"""
Created on Tue May 12 09:15:12 2020

@author: Ben
"""

def print_and_log(logger,msg):
    '''
    desc
    ---------
    Print a message in the terminal and adds the last exception to a logger with 
    that message 
    
    params
    ---------
    **logger** - logger from logging module, used to output the error
    
    **msg** - string to print to user and save with the log entry
    '''
    print(msg)
    print("See log for details")
    logger.exception(msg)
