# -*- coding: utf-8 -*-
"""
Created on Mon May 11 12:11:45 2020

@author: Ben

Methods involving creating and editing marked documents
"""
import os
import subprocess as sp

import MHhash
import MHParsing as mhp
import MHScriptManagement as mhsm

'''
#print template text to the path
#make given substitutions using process_markup_line
#ARGUMENTS PASSED TO FILE: "_in_path" - prefix of path(s) of document(s) to mark, 
#"_#pages" - number of pages in document
#"_init" - flag indicating initial file construction
'''
def make_from_template(file_path, script_base_path, page_count, template_path):
    try:
        mhp.process_file(template_path,file_path,
                     {"_in_path":script_base_path,"_#pages":str(page_count), "_init":"1"})
    except mhp.ParseError as e:
        print(e)
        raise
'''
Open file at path, process with mhu and save back to same path
#ARGUMENTS PASSED TO FILE: "_final_assert_reset" - flag indicating file should be set up
for final assert 
'''
def reset_file_final_check(path):
    try:
        mhp.process_file(path,path,{"_final_assert_reset":"1"})
    except mhp.ParseError as e:
        print(e)
        raise
            
'''
Open file at path, process with mhu and save back to same path
#ARGUMENTS PASSED TO FILE: "_final_assert" - flag initially ='0' that should
be '1' after parsing file iff the file should be reported as marked

returns True iff assert succeeds
'''
def do_file_final_check(path):
    var={"_final_assert":"0"}
    try:
        mhp.process_file(path,path,var)
        return var["_final_assert"]=="1"
    except mhp.ParseError as e:
        print(e)
        raise

'''
Open file at path, process with mhu and save back to same path
#ARGUMENTS PASSED TO FILE: "_question_reset" - flag indicating file should be set up
for marking a question
"_question_name" - name of the question e.g. '3a'
'''
def reset_file_q(path,question_name,previous_mark=''):
    try:
        mhp.process_file(path,path,{"_question_reset":"1", "_question_name":question_name,"_question_prevmark":previous_mark})
    except mhp.ParseError as e:
        print(e)
        raise
'''
Open file at path, process with mhu and save back to same path
#ARGUMENTS PASSED TO FILE:
"_question_mark" - should be set to mark for completed question
"_question_name" - name of the question being extracted e.g. '3a'
"_question_assert" - set to 1 to report marking validated for final question

N.B. the assert will be set to fail if _question_mark =''

return [marked, score]
marked is boolean indicating value of assert
score is the string representing the score
'''
def do_file_q_check(path,question_name):
    var={"_question_mark":"", "_question_assert":"0","_question_name":question_name}
    try:
        mhp.process_file(path,path,var)
        marked=var["_question_assert"]=="1" and var["_question_mark"]
        return [marked, var["_question_mark"]]
    except mhp.ParseError as e:
        print(e)
        raise

'''
#prepare blank file for user to mark, based on teplate
#open it in the editor
#when editor closes check that the job is done (all listed questions reported 
#           marked and marks available)
#if final_validate_source==True then also check that source file passes final 
'all-marked' checks
if final_validate_output==True check also that source has been compiled since saving
 and generate a hash value for the output to return
 NB: final output validation fails automatically if source validation disabled

#return [marks,success,outhash] where marks={name:mark} for all questions validly marked
#and success=False only if final_validate_source==True and source validation fails, or if 
#one of the requested questions fails validation (output validation has no effect)

outhash='' or a hash string of the final output file 
(as generated by MHhash.hash_file_list), if final_validate_output==True and 
all tests are passed (including final source validation)
'''
def make_user_mark(tag, to_mark,script_directory,template_path, questions=[],
                   final_validate_source=True,final_validate_output=False,
                   output_suffix="_m.pdf",marked_suffix="_m.tex", editor="texworks"):
    filedir=mhsm.get_marked_path(script_directory)
    if not os.path.isdir(filedir):#create directory if necessary
        os.mkdir(filedir)
    #file to create/edit
    filepath=os.path.join(filedir,tag+marked_suffix)
    
    #output files
    output_name=tag+output_suffix#name of output file
    final_path=os.path.join(filedir,output_name)
            
    edit_epoch=0#time after which unsaved edits cause validation failure
    try:#check file exists
        with open(filepath,'r'):pass
        
        try:#get time of last change if output file exists and newer than source
            _,edit_epoch=mhsm.check_mod_timestamps(filepath,final_path)
        except: pass
    except:#create new file
        try:
            make_from_template(filepath,'../'+tag,
                            mhsm.count_pdf_pages([os.path.join(script_directory,p)\
                                                     for p in to_mark[tag][0]]),
                            template_path)
        except:
            print("Failed to create new file at: {}".format(filepath))
        

    #reset all variables to inspect later
    for q in questions:
        try:
            reset_file_q(filepath,q,to_mark[tag][2].get(q,''))
        except:
            print("Failed to reset question {} in {}".format(q,filepath))
    if final_validate_source:
        try:
            reset_file_final_check(filepath)
        except: print("Failed to reset master assert in {}".format(filepath))
    try:   
        proc=sp.Popen([editor,filepath])
        proc.wait()
    except:
        print("Error occurred editing document. Check that the correct appliction is selected.")
    finally:#check state of resulting file (must be called as counterpart to each reset)
        ret=[{},True,'']#{question:mark} for all validly marked questions. Bool indicates overall success
        output_hash=''#set to indicate output checks passed (but will not be returned unless source also validated)
        if final_validate_output:
            #do this first or timestamps change
            #ignore edits before edit_epoch (start of this method) if applicable
            if not mhsm.check_mod_timestamps(filepath,final_path,edit_epoch):
                print("Remember to compile after saving!")
            else:#generate hash (also warn about page counts)
                if not mhsm.check_page_counts([os.path.join(script_directory,p) \
                                          for p in to_mark[tag][0]],final_path):
                    print("Warning: page count in {} doesn't match input.".format(final_path))
                output_hash=MHhash.hash_file_list([output_name],filedir)
        if final_validate_source:
            try:
                ret[1]=ret[1] and do_file_final_check(filepath)    
            except: 
                print("Failed to perform final source validation in {}".format(filepath))
                ret[1]=False
        #inspect selected variables
        for q in questions:
            try:
                marked,score=do_file_q_check(filepath,q)
                if marked:
                    ret[0][q]=score
                else: ret[1]=False
            except:
                print("Failed to extract data for question {} in {}".format(q,filepath))
                ret[1]=False
        #if source validation succeeded (incl final tests) set the hash of the output
        if ret[1] and final_validate_source:ret[2]=output_hash

        return ret


    

'''
Run pdflatex on a set of files (assuming pdflatex is available in path)

runs string compile_command in terminal in the given directory for each source file listed in files
'''
def batch_compile(directory, files, compile_command):
    here=".."
    try:
        here=os.getcwd()
        os.chdir(directory)
        for s in files:#compile examples
            try:
                sp.run([compile_command,s],check=True, capture_output=True)
            except sp.CalledProcessError:
                raise#debug
                print("Compilation failed. Continuing...")
    finally:
        os.chdir(here) 

'''
Create tex files for marking all scripts in to_mark (assumed originals contained in script_directory)

run compiler on new source files using batch_compile
'''
def pre_build(to_mark,script_directory, template_path,compile_command,marked_suffix="_m.tex"):
    filedir=mhsm.get_marked_path(script_directory)
    if not os.path.isdir(filedir):#create directory if necessary
        os.mkdir(filedir)
    to_compile=[]
    for tag in to_mark:
        #file to create/edit
        filepath=os.path.join(filedir,tag+marked_suffix)
        try:#check file exists
            with open(filepath,'r'):pass
        except:#create new file
            try:
                make_from_template(filepath,'../'+tag,
                    mhsm.count_pdf_pages([os.path.join(script_directory,p) \
                                          for p in to_mark[tag][0]]),
                    template_path)
                to_compile.append(tag+marked_suffix)
            except:
                print("Failed to create new file at: {}".format(filepath))
    batch_compile(filedir,to_compile,compile_command)
    
'''
Perform loop to mark one script (or until user quits/skips file)
Try to mark script for tag in to_mark (original scripts residing in script_directory)
User will be prompted to edit file until all questions listed in question_names
are marked.

if source_validate==True, also require source file to pass final validation
if output_validate==True, also require output file to pass validation 
            (fails anyway if source_validate==False)
            
to_mark will be updated with any questions validly marked and applicable
flags and hashes from validation

returns True unless user quit loop early (returns True also if they chose to
                                          skip script rather than quit )

'''
def mark_one_loop(tag,to_mark,script_directory,template_path,question_names,source_validate,\
                  output_validate=False,  
                  output_suffix="_m.pdf",marked_suffix="_m.tex", editor="texworks"):
    marks_done={}#questions already marked for this script this pass
    quit_flag=False
    
    #source and output validation reset
    to_mark[tag][3]=False
    to_mark[tag][4]=['',{}]
    
    print("Marks on file: "+', '.join(["Q"+q+": "+to_mark[tag][2][q] \
                                       for q in to_mark[tag][2]]))
            
    while not quit_flag:
        
        marks,marked,outhash=make_user_mark(tag,to_mark,script_directory,\
                template_path,question_names,source_validate, output_validate, 
                output_suffix="_m.pdf",marked_suffix="_m.tex", editor="texworks")
        #record scores in to_mark
        to_mark[tag][2].update(marks)
        marks_done.update(marks)

        print("Marks updated: "+', '.join(["Q"+q+": "+marks_done[q] for q in marks_done]))
            
        if marked:
            inp=input("Continue? (\'q\' to quit, \'r\' to review last) : ")
            if inp in ['q','Q']:#quit this loop and caller (but still try validating)
                quit_flag=True
            if not inp in ['r','R']:#no validation yet
                #check also validation verdict from make_user_mark
                to_mark[tag][3]=source_validate#marked==True here. if not source_validate, don't assume checks complete
                
                #source validate should already be True if output_validate!
                if source_validate and output_validate and outhash: 
                    to_mark[tag][4][0]=outhash
                    to_mark[tag][4][1]={q:marks_done[q] for q in marks_done}
                break#all done for this script
        else:
            selection=input("Marking of "+tag+" not complete. Continue? (\'q\' to quit, \'s\' to skip this file): ")
            quit_flag=selection in ['q','Q']
            if selection in ['s','S']: break
    return not quit_flag
