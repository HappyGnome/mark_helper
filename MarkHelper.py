'''
MarkHelper.py

Author Ben Pooley
Date 01/04/2020

Tool to help streamline marking pdf scripts in tex
'''
import json
import sys
import os

import logging
logger=logging.getLogger(__name__)
logging.basicConfig(filename="Log.txt")

import LogHelper
import MHScriptManagement as mhsm
import MHEditManagement as mhem

# mport subprocess as sp
#import PyPDF2 as ppdf


#load config or create it
config = {"editor":"texworks.exe", "numsep":"_", "template":'mkh_template.tex',\
        "marked suffix":"_marked.tex", "output suffix":"_marked.pdf",\
        "script_dir":"ToMark", "compile_command":"pdflatex", 
        "merged suffix":"_marked.pdf"}

'''
MKH file format:
#mkh is a json file dict indexed by
#tag = filename prefix of marked files

values=[filenames,hash,questions,final_valid, [output_hash,qs_valid]]

#filenames is the list of file paths corresponding to the tag
#hash is a hash value of those files at the time they were deemed marked
#questions={'question':'mark'} for questions asserted as marked
#final_valid is set true when source file passed a final validation check
    last time it was marked
output_hash= '' or a hash of the output (pdf) when both source and output 
    validation have succeeded
qs_valid= {question_name: mark} (as in questions) for all questions checked
when output_hash set
'''

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
    config["merged suffix"]=input("Suffix for final merged output files e.g.\'_m.pdf\': ")
    #config["output viewer"]=input("Viewer application: ")
    config["script_dir"]=input("Script directory: ")
    config["compile_command"]=input("Compile command (e.g. \'pdflatex\' to run  \'pdflatex <source file>\'): ")
    try:
        with open("MarkHelper.cfg","w") as config_file:
            json.dump(config,config_file)
    except Exception:
        LogHelper.print_and_log(logger,"Warning: Config not saved!")
    return True

def cmd_begin(args):#begin marking 
    script_directory=config["script_dir"]
    
    inp=input("Questions to mark (separated by spaces): ")
    question_names=inp.split()
    
    source_validate=input("Do final validation of source file? [y/n]: ") in ["y","Y"]
    
    quit_flag=False
    while not quit_flag:
        print("Checking marking state...")
        try:
            to_mark=mhsm.check_marking_state(script_directory,question_names,
                                        source_validate, numsep=config["numsep"],
                                        output_suffix=config["output suffix"])[0]#initialize to_mark from given script directory
        except Exception:
            LogHelper.print_and_log(logger,
                                    "Failed to update marking state!")
            return True
        if to_mark=={}:
            print("Marking complete!")
            break
        try:#precompile
            print("Precompiling...")
            mhem.pre_build(to_mark,script_directory,config["template"],
                           config["compile_command"], marked_suffix=config["marked suffix"])
            print("Precompiling successful!")
        except Exception:
            LogHelper.print_and_log(logger,"Precompiling failed!")
        for tag in to_mark:
            print("Now marking "+tag)
            quit_flag=not mhem.mark_one_loop(tag,to_mark,script_directory,
                                        config["template"],question_names,
                                        source_validate,False,
                                        output_suffix=config["output suffix"],
                                        marked_suffix=config["marked suffix"], 
                                        editor=config["editor"])
            mhsm.declare_marked(tag,script_directory,to_mark)#update marking state in file
            if quit_flag: break     
    return True


'''
for iterable data print up to n entries
'''
def print_some(data, n=10):
    en=list(enumerate(data))
    
    for r in range(min(n,len(en))):
        #print(en[r])#debug
        print("{}".format(en[r][1]))
'''
compile all marked scripts and open for the user to preview/edit allowing
them to check/modify the output. record successful scripts as having output
validated


'''
def cmd_build_n_check(args):
    script_directory=config["script_dir"]
    
    inp=input("Questions required in completed scripts (separated by spaces): ")
    question_names=inp.split()

    print("Checking marking state...")
    try:
        #check for scripts with unmarked questions (from list) or which
        #have not had the source validated
        to_mark,done_mark=mhsm.check_marking_state(script_directory,
                                                   question_names,True,False, 
                                                   numsep=config["numsep"],
                                        output_suffix=config["output suffix"])
        if to_mark!={}:
            print("Some scripts missing marks or validation: ")
            print_some(to_mark)
            return True
        #now all scripts validly marked
        #get all of those that need user to check output
        to_mark,done_mark=mhsm.check_marking_state(script_directory,
                                                   question_names,True,True,
                                                   numsep=config["numsep"],
                                        output_suffix=config["output suffix"])
    except Exception:
        LogHelper.print_and_log(logger,"Failed to update marking state!")
        return True
    
    try:#compile
        print("Compiling...")
        mhem.batch_compile(mhsm.get_marked_path(script_directory),
                           [tag+config["marked suffix"] for tag in to_mark],
                           config["compile_command"])
        print("Compiling successful!")
    except Exception:
        LogHelper.print_and_log(logger,"Compiling failed!")
        return True
    for tag in to_mark:
        print("Now checking "+tag)
        quit_flag=not mhem.mark_one_loop(tag,to_mark,script_directory,
                                    config["template"],question_names,
                                    True,True,
                                    output_suffix=config["output suffix"],
                                    marked_suffix=config["marked suffix"], 
                                    editor=config["editor"])
        mhsm.declare_marked(tag,script_directory,to_mark)#update marking state in file
        if quit_flag: break     
    return True

def cmd_makecsv(args):#begin marking 
    script_directory=config["script_dir"]
    
    out_path=os.path.join(mhsm.get_marked_path(script_directory),
                          input("CSV filename: "))
    
    try:
        with open(out_path,'r'): pass
        if not input("File {} exists, overwrite? [y/n]: ".format(out_path)) in ['y','Y']:
            print("Operation cancelled.")
            return True
    except OSError: pass
    
    inp=input("Questions for which to extract marks (separated by spaces): ")
    question_names=inp.split()
    
    #final_validate=input("Require final validation of marking? [y/n]: ") in ["y","Y"]
    
    try:
        to_mark,done_mark=mhsm.check_marking_state(script_directory,
                                                    question_names,True,True,
                                                   numsep=config["numsep"],
                                        output_suffix=config["output suffix"])#initialize to_mark from given script directory
    except Exception:
        LogHelper.print_and_log(logger,"Failed to read marking state!")
        return True
    
    if to_mark!={}:
        print("Warning! Selected questions may not be validly marked in some scripts. Including: ")
        print_some(to_mark)
        print("Remember to run \'check\' command for final version.")
    
    try:
        with open(out_path,'w') as file:
            file.write("Script #")#header line
            for q in question_names:
                file.write(", Question {}".format(q))
            #body
            for d in sorted(done_mark.keys()):
                file.write("\n{}".format(d))
                #print(done_mark[d])#debug
                for q in question_names:
                    file.write(",{}".format(done_mark[d][4][1][q]))
    except Exception:
        LogHelper.print_and_log(logger,"Failed to write csv file.")
    return True

'''
Create blank pdf for each script and compile marked source files over the 
corresponding blank.

Merge the output pdfs on top of copies of the original scripts
'''
def cmd_make_merged_output(args):
    script_directory=config["script_dir"]
    
    inp=input("Confirm questions required in completed scripts (separated by spaces): ")
    question_names=inp.split()
    
    print("Checking marking state...")
    try:
        #check for scripts with unmarked questions (from list) or which
        #have not had the source validated
        to_mark,done_mark=mhsm.check_marking_state(script_directory,
                                                   question_names,True,True, 
                                                   numsep=config["numsep"],
                                        output_suffix=config["output suffix"])
        if to_mark!={}:
            print("Some scripts missing marks or validation: ")
            print_some(to_mark)
            print("Please ensure all marking completed before merging.")
    except Exception:
        LogHelper.print_and_log(logger,"Failed to update marking state!")
        return True
    
    '''
    Make blanks
    '''
    blankdir=os.path.join(script_directory,"merged")
    newsourcedir=os.path.join(blankdir,"source")
    newfinaldir=os.path.join(blankdir,"final")
    for path in [blankdir,newsourcedir,newfinaldir]:
        if not os.path.isdir(path):#create directory if necessary
            os.mkdir(path)
    for d in done_mark:
        try:
            for file in done_mark[d][0]:#constituent files                
                mhsm.make_blank_pdf_like(os.path.join(script_directory,file),
                                         os.path.join(blankdir,file))
        except Exception:
            LogHelper.print_and_log(logger,"Warning! Failed to make blanks for {}".format(d))
    
    '''
    copy source files
    '''
    oldsourcedir=mhsm.get_marked_path(script_directory)
    to_compile=[]
    for d in done_mark:
        try:
            new_source_path=os.path.join(newsourcedir,d+config["marked suffix"])
            mhem.copyFile(os.path.join(oldsourcedir,d+config["marked suffix"]),
                          new_source_path)
            to_compile.append(new_source_path)
        except Exception:
            LogHelper.print_and_log(logger,"Warning! Failed to copy source file for {}".format(d))
             
    '''
    compile source files
    '''
    mhem.batch_compile(newsourcedir,to_compile,config["compile_command"])
    
    '''
    Merge files
    '''
    for d in done_mark:
        try:
            merged_filepath=os.path.join(newfinaldir,
                                         d+config["merged suffix"])
            overlay_filepath= os.path.join(newsourcedir,
                                           d+config["output suffix"])
            mhsm.merge_pdfs(d[0], overlay_filepath, merged_filepath,
                            script_directory)
        except Exception:
            LogHelper.print_and_log(logger,
                                    "Warning! Failed to merge output for {}"
                                    .format(d))
    return True

'''
*******************************************************************************
*******************************************************************************
Main CLI cmd parser

return False to terminate main loop
'''
handlers={"quit":cmd_exit, "config":cmd_config, "begin":cmd_begin, 
          'makecsv':cmd_makecsv,
          'check':cmd_build_n_check,
          'makemerged':cmd_make_merged_output}#define handlers
def parse_cmd(cmd):
    toks=cmd.split()
    if len(toks)==0: return True#basic checks
    
    if toks[0] in handlers:
        try:
            return handlers[toks[0]](toks[1:])
        except Exception:
            LogHelper.print_and_log(logger,"Problem occured in {}".format(toks[0]))
            return True
    else: 
        print("Unrecognized command!")
        return True
'''
Initialization  ###############################################################
'''    
try:#load config
    with open("MarkHelper.cfg","r") as config_file:
        config.update(json.load(config_file))
except Exception:
    if not cmd_config(None):
        LogHelper.print_and_log(logger,"Failed to create config! Exiting...")
        sys.exit(1)    
'''
Main CLI loop  ################################################################
'''
while True:
    cmd=input(">")
    if not parse_cmd(cmd): break
