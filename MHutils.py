# -*- coding: utf-8 -*-
"""
Created on Wed Apr  1 10:20:52 2020

@author: Ben
"""
import hashlib
import os

#read each file in the list "files" and return a hash of entire stream
#return hex digest of the hash
def hash_file_list(files, directory=''): 
    buf_size=2048#bytes
    the_hash=hashlib.sha256()
    for f in files:
        the_file=open(os.path.join(directory,f),"rb")
        while True:#until eof
            chunk=the_file.read(buf_size)
            if len(chunk)==0: break
            the_hash.update(chunk)            
        the_file.close()
    return the_hash.hexdigest()

#return line with substitutions made
#Commandsin the line  must be enclosed by %# and #%, if the content matches
    #key in sub then value of sub is substituted
    #if command is key=... and key is in vartoset then that key is set to 
    #what follows '='(before #%)
    #if syntax for vartoset is used and key appears in vartoreset, then
    #the command syntax is replaced in the output by a command %#key=vartoreset[key]#%
    #setting commands  are stripped from the returned line
    #unmatched commands are left in the returned line
def process_markup_line(line, sub={}, vartoget={}, vartoset={}):
    ret=""#line returned
    consumed=0#first character in line not dealt with
    while consumed<len(line):
        spos=line[consumed:].find('%#')#start of command
        if spos<0:
            ret+=line[consumed:]
            break
        spos=spos+2+consumed#point to start of command
        epos=line[spos:].find('#%')
        if epos<0:
            ret+=line[consumed:]
            break
        epos=epos+spos  #next character position after command
        cmd=line[spos:epos]
        
        eqpos=cmd.find('=')#set or get command
        key=cmd[:eqpos]
        ret+=line[consumed:spos-2]#keep initial segment
        consumed=spos-2
        handled=False#command recognised and dealt with
        if eqpos<0 and cmd in sub:#substitution
            ret+=sub[cmd]
            handled=True
        else:           
            if key in vartoget:#extract value
                vartoget[key]=cmd[eqpos+1:]
                handled=True
            if key in vartoset:
                ret+="%#"+key+"="+vartoset[key]+"#%"
                handled=True
        if not handled:
                #default: leave everything
                ret+=line[consumed:epos+2]
        consumed=epos+2
    return ret
    
'''
###############################################################################
'''
if __name__=='__main__':
    #print(hash_file_list(["HashTest/f1.txt","HashTest/f2.txt","HashTest/f3.txt"]))
    print(process_markup_line("my line 1"))
    print(process_markup_line("my line%#ok#% 1"))
    print(process_markup_line("my %#ok#% line %#ok#% 1",{'ok':'okay'}))
    reqs={'foo':''}
    print(process_markup_line("my %#foo#% line %#foo#% 1",{'ok':'okay'}))
    print(reqs)
    print(process_markup_line("my %#foo#% line %#foo=1#% 1",{'ok':'okay'},reqs))
    print(reqs)
    print(process_markup_line("my %#ok#% line %#foo=1#% 1",{'ok':'okay'},reqs))
    print(reqs)
    print(process_markup_line("my %#foo=2#% line %#foo=haha#% 1",{'ok':'okay'},reqs,{'foo':'3'}))
    print(reqs)