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

script_directory=""#path containing script pdfs

to_mark={}#list of files to mark. See mkh entry format.

#mkh is a json file containing list of {tag:[filenames,hash]}
#tag = filename prefix of marked files
#filenames is the list of file paths corresponding to the tag
#hash is a hash value of those files at the time they were deemed marked
'''
check source directory for files or file sets,
check which .mkh files exist and are up to date
set to_mark to list of scripts left to mark
'''
def check_marking_state():
    to_mark_temp={}
    global to_mark
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
            to_mark_temp[tag]=[[s+'.pdf'],'']#hash computed later    
    
    for t in to_mark_temp:
        files_hash=mhu.hash_file_list(to_mark_temp[t][0], script_directory)
        marked=False
        #check for matching .mkh file
        if t+'.mkh' in script_files_raw:
            try:
                with open(os.path.join(script_directory,t+".mkh"),"r") as mkh:
                    mkh_data=json.load(mkh)
                    if mkh_data==[to_mark_temp[t][0],files_hash]:
                        marked=True
            except:pass
        #add to to_mark
        if not marked:
            to_mark[t]=[to_mark_temp[t][0],files_hash]

'''
call when marking of script with given tag deemed complete.
Create/update associated mkh file
'''
def declare_marked(tag):
    with open(os.path.join(script_directory,tag+".mkh"),"w") as mkh:
        json.dump(to_mark[tag],mkh)
    
#print template text to the given file (open for writing)
#make given substitutions using process_markup_line
def make_from_template(file, subs={}):
    with open(config['template'], 'r') as template:
        lines=template.readlines()
        out_lines=mhu.process_lines(lines,subs)
        file.writelines(out_lines)

def reset_file(path):
    out_lines=[]
    with open(path,'r') as file:
        lines=file.readlines()
        out_lines=mhu.process_lines(lines,{'reset':''})
    with open(path,'w') as file:
        file.writelines(out_lines)
            
def get_var_from_file(path,vartoget):#initialise values in vartoget from commands in file
    with open(path,'r') as file:
        lines=file.readlines()
        mhu.process_lines(lines,vartoget)

def get_marked_path():
    return os.path.join(script_directory,"marked")
    
#prepare blank file for user to mark, based on teplate
#open it in the editor
#when editor closes check that the job is done
#return true on completed job
def make_user_mark(tag):
    filedir=get_marked_path()
    if not os.path.isdir(filedir):#create directory if necessary
        os.mkdir(filedir)
    #file to create/edit
    filepath=os.path.join(filedir,tag+config["marked suffix"])
    vartoget={'marking_complete':'0', 'assert':'1'}
    try:#file exists, ake sure it requires user editing before acceptance
        reset_file(filepath)
    except:#create new file
        try:
            with open(filepath,'w') as file:
                make_from_template(file,subs={'tag':'../'+tag})
        except:
            print("Failed to create new file at: {}".format(filepath))
            
    try:
        proc=sp.Popen([config['editor'],filepath])
        proc.wait()
    except:
        print("Error occurred editing document. Check that the correct appliction is selected.")
        return False
    try:
        get_var_from_file(filepath,vartoget)
        if vartoget["marking_complete"]=='1' and vartoget['assert']=='1':
            return True
    except: pass
    return False
    
    
    

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
    
    quit_flag=False
    while not quit_flag:
        print("Checking marking state...")
        try:
            check_marking_state()#initialize to_mark from given script directory
        except:
            print("Failed to update marking state!")
            return True
        if to_mark=={}:
            print("Marking complete!")# Use \'review\' to check marked documents.")#TODO: implement this
            break
        for tag in to_mark:
            print("Now marking "+tag)
            while not make_user_mark(tag):
                selection=input("Marking of "+tag+" not complete. Continue? (\'q\' to quit): ")
                quit_flag=selection in ['q','Q']
                if quit_flag: break
            if quit_flag: break
            else:#make_user_mark returned true
                declare_marked(tag)
                selection=input("Continue? (\'q\' to quit): ")
                if selection in ['q','Q']:
                    quit_flag=True
                    break    
     
    return True
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
*******************************************************************************
*******************************************************************************
Main CLI cmd parser

return False to terminate main loop
'''
handlers={"quit":cmd_exit, "config":cmd_config, "begin":cmd_begin,
          "declare":cmd_declare_marked}# "del":cmdDel, ""}#define handlers
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