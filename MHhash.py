# -*- coding: utf-8 -*-
"""
Created on Wed Apr  1 10:20:52 2020

@author: Ben
"""
import os

import hashlib


#read each file in the list "files" and return a hash of entire stream
#return hex digest of the hash
def hash_file_list(files, directory=''): 
    buf_size=2048#bytes
    the_hash=hashlib.sha256()
    #print(files)#debug
    for f in files:
        with open(os.path.join(directory,f),"rb") as the_file:
            while True:#until eof
                chunk=the_file.read(buf_size)
                if len(chunk)==0: break
                the_hash.update(chunk)            
    return the_hash.hexdigest()


'''
###############################################################################
'''
if __name__=='__main__':
    #print(hash_file_list(["HashTest/f1.txt","HashTest/f2.txt","HashTest/f3.txt"]))
    pass  