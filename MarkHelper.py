'''
MarkHelper.py

Author Ben Pooley
Date 01/04/2020

Tool to help streamline marking pdf scripts in tex
'''
import json
import sys
import MHutils as mhu
import os
import subprocess as sp
import PyPDF2 as ppdf

#Look for files / sets of files to mark
#check .mkh file (create if needed)
#produce tex file from template for next file set and open in selected editor
#when editor closes, check for %#mdone in source and modification times of files 
    #Also double check things that should have been removed e.g. "grid"
#method to run through all examples at the end for user to check

#FILES: template files, check templates,  config --editors

#load config or create it
config={"editor":"texworks.exe", "numsep":"_", "template":'mkh_template.tex',\
        "marked suffix":"_marked.tex", "output suffix":"_marked.pdf",\
        "output viewer":"C:\Program Files\SumatraPDF\sumatrapdf.exe"}

#script_directory=""#path containing script pdfs

#to_mark={}#list of files to mark. See mkh entry format.

#mkh is a json file containing list of [filenames,hash,questions,final_valid]
#tag = filename prefix of marked files
#filenames is the list of file paths corresponding to the tag
#hash is a hash value of those files at the time they were deemed marked
#questions={'question':'mark'} for questions asserted as marked
#final_valid is set true when file set passes a final validation check
'''
check source directory for files or file sets,
check which .mkh files exist and are up to date

if questions is set to a list of question names
then any scripts which have not had all of those questions marked will be returned

if final_assert=True then any file that has not passed final validation 
will also be included

return to_mark: list of scripts left to mark in mkh format
'''
def check_marking_state(script_directory,questions=[], final_assert=True):
    to_mark_temp={}
    to_mark={}
    
    script_files_raw=os.listdir(script_directory)
    #extract only pdfs and strip '.pdf'
    script_files_pdf=[f[:-4] for f in script_files_raw if f[-4:]=='.pdf']
    script_files_pdf.sort()#ensure files with same tag appear in same order
    
    for s in script_files_pdf:#add file names to list, accounting for doc numbers
        tag=s#default tag in to_mark
        sep_ind=s.rfind(config["numsep"])#look for trailing number
        if sep_ind>0:#sep found in valid place
            if  s[sep_ind+1:].isnumeric():
                tag=s[:sep_ind]
        if tag in to_mark_temp:
            cur_entry=to_mark_temp[tag]
            cur_entry[0].append(s+'.pdf')
        else:
            to_mark_temp[tag]=[[s+'.pdf'],'',{},False]#hash computed later    
    
    for t in to_mark_temp:
        files_hash=mhu.hash_file_list(to_mark_temp[t][0], script_directory)
        marked=False#file exists and all questions marked?
        #check for matching .mkh file
        if t+'.mkh' in script_files_raw:
            try:
                with open(os.path.join(script_directory,t+".mkh"),"r") as mkh:
                    mkh_data=json.load(mkh)
                    if mkh_data[:2]==[to_mark_temp[t][0],files_hash]:
                        marked=mkh_data[3] or not final_assert
                        for q in questions:#make sure all questions marked too
                            if q not in mkh_data[2]:
                                marked=False
                                break
            except:pass
        #add to to_mark
        if not marked:
            to_mark[t]=to_mark_temp[t]
            to_mark[t][1]=files_hash
    return to_mark

'''
Do extra checks on timestamps for source (e.g. latex) file and final pdf output
(If source has been modified since last compilation then latest changes may not 
be reflected) 

Return False if modification dates are in the wrong order
'''
def check_mod_timestamps(source_path,final_path):
    try:
        src_stat=os.stat(source_path)
        fin_stat=os.stat(final_path)
        #print("{} {}".format(src_stat.st_mtime,fin_stat.st_mtime))#debug
        return src_stat.st_mtime<=fin_stat.st_mtime
        
    except:
        return False

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
    
'''
#print template text to the path
#make given substitutions using process_markup_line
#ARGUMENTS PASSED TO FILE: "_in_path" - prefix of path(s) of document(s) to mark, 
#"_#pages" - number of pages in document
#"_init" - flag indicating initial file construction
'''
def make_from_template(file_path, script_base_path, page_count):
    mhu.process_file(config['template'],file_path,
                     {"_in_path":script_base_path,"_#pages":str(page_count), "_init":"1"})

'''
Open file at path, process with mhu and save back to same path
#ARGUMENTS PASSED TO FILE: "_final_assert_reset" - flag indicating file should be set up
for final assert 
'''
def reset_file_final_check(path):
    mhu.process_file(path,path,{"_final_assert_reset":"1"})
            
'''
Open file at path, process with mhu and save back to same path
#ARGUMENTS PASSED TO FILE: "_final_assert" - flag initially ='0' that should
be '1' after parsing file iff the file should be reported as marked

returns True iff assert succeeds
'''
def do_file_final_check(path):
    var={"_final_assert":"0"}
    mhu.process_file(path,path,var)
    return var["_final_assert"]=="1"

'''
Open file at path, process with mhu and save back to same path
#ARGUMENTS PASSED TO FILE: "_question_reset" - flag indicating file should be set up
for marking a question
"_question_name" - name of the question e.g. '3a'
'''
def reset_file_q(path,question_name):
    mhu.process_file(path,path,{"_question_reset":"1", "_question_name":question_name})
    
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
    mhu.process_file(path,path,var)
    marked=var["_question_assert"]=="1" and var["_question_mark"]
    return [marked, var["_question_mark"]]



    
#return path for marked files relative to script directory
def get_marked_path(script_dir):
    return os.path.join(script_dir,"marked")
    
#prepare blank file for user to mark, based on teplate
#open it in the editor
#when editor closes check that the job is done (all listed questions reported 
#           marked and marks available)
#if final_validate==True then also check that file passes final 'all-marked' checks
#return [marks,success] where marks={name:mark} for all questions validly marked
#and success=False only if final_validate==True and validation fails, or if 
#one of the requested questions fails validation
def make_user_mark(tag, to_mark,script_directory, questions=[], final_validate=True):
    filedir=get_marked_path(script_directory)
    if not os.path.isdir(filedir):#create directory if necessary
        os.mkdir(filedir)
    #file to create/edit
    filepath=os.path.join(filedir,tag+config["marked suffix"])
    try:#check file exists
        with open(filepath,'r'):pass
    except:#create new file
        try:
            make_from_template(filepath,'../'+tag,
                               count_pdf_pages([os.path.join(script_directory,p) for p in to_mark[tag][0]]))
        except:
            print("Failed to create new file at: {}".format(filepath))
        
    try:
        #reset all variables to inspect later
        for q in questions:
            try:
                reset_file_q(filepath,q)
            except:
                print("Failed to reset question {} in {}".format(q,filepath))
        if final_validate:
            try:
                reset_file_final_check(filepath)
            except: print("Failed to reset master assert in {}".format(filepath))
        
        proc=sp.Popen([config['editor'],filepath])
        proc.wait()
    except:
        print("Error occurred editing document. Check that the correct appliction is selected.")
    finally:#check state of resulting file (must be called as counterpart to each reset)
        ret=[{},True]
        if final_validate:
            try:
                final_path=os.path.join(filedir,tag+config["output suffix"])
                if not check_mod_timestamps(filepath,final_path):#do this first or timestamps change
                    ret[1]=False
                    print("Remember to compile after saving!")
                elif not check_page_counts([os.path.join(script_directory,p) for p in to_mark[tag][0]]\
                    ,final_path):
                    print("Warning: page count in {} doesn't match input.".format(final_path))
                ret[1]=ret[1] and do_file_final_check(filepath)
            except: 
                print("Failed to perform master assert in {}".format(filepath))
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

        return ret
    
    
    

'''############################################################################
Command line interface
############################################################################'''
'''
************************************************************
Command handlers
'''
def cmd_exit(args):
    return False

def cmd_config(args):#user update config file
    global config
    config["editor"]=input("Editor application: ")
    config["numsep"]=input("File number separator: ")#character in file names separating tag from document number
    config["template"]=input("Template file: ")
    config["marked suffix"]=input("Suffix for marked source files e.g.\'_m.tex\': ")
    config["output suffix"]=input("Suffix for marked output files e.g.\'_m.pdf\': ")
    config["output viewer"]=input("Viewer application: ")
    try:
        with open("MarkHelper.cfg","w") as config_file:
            json.dump(config,config_file)
    except:
        print("Warning: Config not saved!")
    return True

def cmd_begin(args):#begin marking 
    global script_directory
    script_directory=input("Folder of scripts: ")
    
    inp=input("Questions to mark (separated by spaces): ")
    question_names=inp.split()
    
    final_validate=input("Do final validation of marking? [y/n]: ") in ["y","Y"]
    '''all_qs=[]#all question names required in after this pass to pass validation 
    if final_validate:
        inp=input("Questions required for final validation (separated by spaces): ")
        all_qs=inp.split()'''
    
    quit_flag=False
    while not quit_flag:
        print("Checking marking state...")
        try:
            to_mark=check_marking_state(script_directory,question_names,final_validate)#initialize to_mark from given script directory
        except:
            print("Failed to update marking state!")
            return True
        if to_mark=={}:
            print("Marking complete!")# Use \'review\' to check marked documents.")#TODO: implement this
            break
        for tag in to_mark:
            print("Now marking "+tag)
            marks_done={}#questions already marked for this script this pass
            while True:
                
                marks,marked=make_user_mark(tag,to_mark,script_directory,[q for q  in question_names if not q in marks_done],final_validate)
                #record scores in to_mark
                to_mark[tag][2].update(marks)
                marks_done.update(marks)
                
                #check final validation
                '''all_marked=True
                if final_validate:#check all required marks available
                    for q in all_qs:
                        if not q in to_mark[tag][2]:
                            all_marked=False
                            print("Warning: question {} not marked!".format(q))'''
                #check also validation verdict from make_user_mark
                to_mark[tag][3]=marked and final_validate# and all_marked#if it's already True, reset it if not final_validate
                if marked:break#all done for this script
                else:
                    selection=input("Marking of "+tag+" not complete. Continue? (\'q\' to quit, \'s\' to skip this file): ")
                    quit_flag=selection in ['q','Q']
                    if quit_flag or selection in ['s','S']: break
            declare_marked(tag,script_directory,to_mark)#update marking state in file
            if quit_flag: break
            selection=input("Continue? (\'q\' to quit): ")
            if selection in ['q','Q']:
                quit_flag=True
                break    
     
    return True
'''
def cmd_declare_marked(args):#declare a script as marked (mostly diagnostic use)
    tag=input("Tag for file(s) confirmed marked: ")
    if tag not in to_mark:
        print("Tag not found!")
        return True
    print("Warning: manual declaration of marking completion is not advised!")
    go=input("Continue? [y/n]: ")
    if go not in ['y','Y']:
        print("declaration cancelled...")
    else: declare_marked(tag)
    
    return True
    '''
'''
*******************************************************************************
*******************************************************************************
Main CLI cmd parser

return False to terminate main loop
'''
handlers={"quit":cmd_exit, "config":cmd_config, "begin":cmd_begin}#define handlers
def parse_cmd(cmd):
    toks=cmd.split()
    if len(toks)==0: return True#basic checks
    
    if toks[0] in handlers:
        return handlers[toks[0]](toks[1:])
    else: 
        print("Unrecognized command!")
        return True
'''
Initialization  ###############################################################
'''    
try:#load config
    with open("MarkHelper.cfg","r") as config_file:
        config.update(json.load(config_file))
except:
    if not cmd_config(None):
        print("Failed to create config! Exiting...")
        sys.exit(1)    
'''
Main CLI loop  ################################################################
'''
while(True):
    cmd=input(">")
    if not parse_cmd(cmd): break