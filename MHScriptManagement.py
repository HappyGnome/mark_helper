# -*- coding: utf-8 -*-
"""
Created on Mon May 11 12:06:04 2020

@author: Ben

Methods involving tracking marking progress, and script files
"""
import os
import json

import PyPDF2 as ppdf

import MHhash


#return path for marked files relative to script directory
def get_marked_path(script_dir):
    return os.path.join(script_dir,"marked")
'''
Return {tag:file_list} where tag is the prefix of a collection of files in 
script_directory e.g. script1.pdf => tag=script1, and file_list is a 
list of the files (pdfs) that comprise the script
'''
def get_script_list(script_directory,numsep="_"):
    
    ret={}
    
    script_files_raw=os.listdir(script_directory)
    #extract only pdfs and strip '.pdf'
    script_files_pdf=[f[:-4] for f in script_files_raw if f[-4:]=='.pdf']
    script_files_pdf.sort()#ensure files with same tag appear in same order
    
    for s in script_files_pdf:#add file names to list, accounting for doc numbers
        tag=s#default tag in to_mark
        sep_ind=s.rfind(numsep)#look for trailing number
        if sep_ind>0:#sep found in valid place
            if  s[sep_ind+1:].isnumeric():
                tag=s[:sep_ind]
        if tag in ret:
            ret[tag].append(s+'.pdf')
        else:
            ret[tag]=[s+'.pdf']#,'',{},False]#hash computed later 
    return ret



'''
check source directory for files or file sets,
check which .mkh files exist and are up to date

if questions is set to a list of question names
then any scripts which have not had all of those questions marked will be returned

if final_assert=True then any file that has not passed final validation 
will also be included

return [to_mark,done_mark]: lists of scripts left to mark and marked in mkh format
(A script is 'marked' in this case if all requested questions are available 
and final validation reported complete, if final_assert==True)

if match_outhash==True then additionally, scripts will appear in to_mark
if the final output hash is not saved or does not match the actual output file
'''
def check_marking_state(script_directory,questions=[], final_assert=True,
                        match_outhash=False, output_suffix="_m.pdf", numsep="_"):
    to_mark={}
    done_mark={}#valid script sets with requested questions marked
       
    script_files_raw=os.listdir(script_directory)
    
    to_mark_temp=get_script_list(script_directory, numsep)
    
    for t in to_mark_temp:
        to_mark_temp[t]=[to_mark_temp[t],'',{},False,'']#input hash,question marks,source validate flag, output hash
        files_hash=MHhash.hash_file_list(to_mark_temp[t][0], script_directory)
        marked=False#file exists and all questions marked?
        #check for matching .mkh file
        if t+'.mkh' in script_files_raw:
            try:
                with open(os.path.join(script_directory,t+".mkh"),"r") as mkh:
                    mkh_data=json.load(mkh)
                    to_mark_temp[t][2:]=mkh_data[2:]#extract non-hash,non-path data
                    if mkh_data[:2]==[to_mark_temp[t][0],files_hash]:#if hashes don't match it's not marked!
                        marked=mkh_data[3] or not final_assert
                        marklist= mkh_data[2]
                        #in output validation mode check marks from validation instead
                        if match_outhash: marklist=mkh_data[4][1]
                        for q in questions:#make sure all questions marked too
                            if q not in marklist:
                                marked=False
                                break
                        if match_outhash:
                            outhash=MHhash.hash_file_list([t+output_suffix], 
                                               get_marked_path(script_directory))
                            #outhash valid and matches saved value
                            marked=marked and outhash==mkh_data[4][0] and outhash
                            
                    else:
                        print("Warning: originals modified for script {}".format(t))
            except:
                marked=False
        #add to to_mark
        if not marked:
            to_mark[t]=to_mark_temp[t]
            to_mark[t][1]=files_hash
        else:
            done_mark[t]=to_mark_temp[t]
            done_mark[t][1]=files_hash
    return [to_mark,done_mark]



'''
Do extra checks on timestamps for source (e.g. latex) file and final pdf output
(If source has been modified since last compilation then latest changes may not 
be reflected) 

if neither has changed since time edit_epoch then the test passes in any case

Return [res,mtime]
res=False if modification dates are in the wrong order
mtime= last tie that one of the files was modified or 0 if res==False
'''
def check_mod_timestamps(source_path,final_path, edit_epoch=0):
    try:
        src_stat=os.stat(source_path)
        fin_stat=os.stat(final_path)
        #print("{} {}".format(src_stat.st_mtime,fin_stat.st_mtime))#debug
        last_time=max(src_stat.st_mtime,fin_stat.st_mtime)
        if last_time<=edit_epoch or fin_stat.st_mtime==last_time:
            return [True,last_time]
        return [False,0]
        
    except:
        return [False,0]

'''
Do extra checks on page counts 

return False if number of pages in all files listed in the list
input_file_paths does not match the page count in pdf_path (or if a file cannot be
read)
'''
def check_page_counts(input_pdf_paths,output_pdf_path):
    return count_pdf_pages(input_pdf_paths)==count_pdf_pages([output_pdf_path])
'''
given a list of file paths (all pdfs) sum the numbers of pages in those files 

return number of pages found
'''
def count_pdf_pages(file_paths):
    pages=0
    for f in file_paths:
        try:
            reader=ppdf.PdfFileReader(f)
            pages+=reader.getNumPages()
        except:
            print("Could not count pages in {}".format(f))
    return pages
'''
call when marking of script with given tag deemed complete/partially complete.
Create/update associated mkh file

tag=internal tag of script
script_directory= ...
to_mark=dictionary of mkh entry data for current doc list (tag is a key for this)
'''
def declare_marked(tag, script_directory, to_mark):
    with open(os.path.join(script_directory,tag+".mkh"),"w") as mkh:
        json.dump(to_mark[tag],mkh)
