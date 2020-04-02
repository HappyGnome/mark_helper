# -*- coding: utf-8 -*-
"""
Created on Wed Apr  1 10:20:52 2020

@author: Ben
"""
import hashlib

#read each file in the list "files" and return a hash of entire stream
#return hex digest of the hash
def HashFileList(files): 
    buf_size=2048#bytes
    the_hash=hashlib.sha256()
    for f in files:
        the_file=open(f,"rb")
        while True:#until eof
            chunk=the_file.read(buf_size)
            if len(chunk)==0: break
            the_hash.update(chunk)            
        the_file.close()
    return the_hash.hexdigest()

'''
###############################################################################
'''
if __name__=='__main__':
    print(HashFileList(["HashTest/f1.txt","HashTest/f2.txt","HashTest/f3.txt"]))