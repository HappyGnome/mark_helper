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


#load config or create it
config={"editor":"texworks.exe", "numsep":"_", "template":'mkh_template.tex',\
        "marked suffix":"_marked.tex", "output suffix":"_marked.pdf",\
        "script_dir":"ToMark","output viewer":"C:\Program Files\SumatraPDF\sumatrapdf.exe"}

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


'''
Return {tag:file_list} where tag is the prefix of a collection of files in 
script_directory e.g. script1.pdf => tag=script1, and file_list is a 
list of the files (pdfs) that comprise the script
'''
def get_script_list(script_directory):
    
    ret={}
    
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
def check_marking_state(script_directory,questions=[], final_assert=True, match_outhash=False):
    to_mark={}
    done_mark={}#valid script sets with requested questions marked
       
    script_files_raw=os.listdir(script_directory)
    
    to_mark_temp=get_script_list(script_directory)
    
    for t in to_mark_temp:
        to_mark_temp[t].extend(['',{},False,''])#input hash,question marks,source validate flag, output hash
        files_hash=mhu.hash_file_list(to_mark_temp[t][0], script_directory)
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
                            outhash=mhu.hash_file_list([t+config['output suffix']], 
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
    try:
        mhu.process_file(config['template'],file_path,
                     {"_in_path":script_base_path,"_#pages":str(page_count), "_init":"1"})
    except mhu.ParseError as e:
        print(e)
        raise
'''
Open file at path, process with mhu and save back to same path
#ARGUMENTS PASSED TO FILE: "_final_assert_reset" - flag indicating file should be set up
for final assert 
'''
def reset_file_final_check(path):
    try:
        mhu.process_file(path,path,{"_final_assert_reset":"1"})
    except mhu.ParseError as e:
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
        mhu.process_file(path,path,var)
        return var["_final_assert"]=="1"
    except mhu.ParseError as e:
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
        mhu.process_file(path,path,{"_question_reset":"1", "_question_name":question_name,"_question_prevmark":previous_mark})
    except mhu.ParseError as e:
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
        mhu.process_file(path,path,var)
        marked=var["_question_assert"]=="1" and var["_question_mark"]
        return [marked, var["_question_mark"]]
    except mhu.ParseError as e:
        print(e)
        raise


    
#return path for marked files relative to script directory
def get_marked_path(script_dir):
    return os.path.join(script_dir,"marked")

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
(as generated by mhu.hash_file_list), if final_validate_output==True and 
all tests are passed (including final source validation)
'''
def make_user_mark(tag, to_mark,script_directory, questions=[],
                   final_validate_source=True,final_validate_output=False):
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
        proc=sp.Popen([config['editor'],filepath])
        proc.wait()
    except:
        print("Error occurred editing document. Check that the correct appliction is selected.")
    finally:#check state of resulting file (must be called as counterpart to each reset)
        ret=[{},True,'']#{question:mark} for all validly marked questions. Bool indicates overall success
        output_hash=''#set to indicate output checks passed (but will not be returned unless source also validated)
        if final_validate_output:
            output_name=tag+config["output suffix"]#name of output file
            final_path=os.path.join(filedir,output_name)
            if not check_mod_timestamps(filepath,final_path):#do this first or timestamps change
                print("Remember to compile after saving!")
            else:#generate hash (also warn about page counts)
                if not check_page_counts([os.path.join(script_directory,p) \
                                          for p in to_mark[tag][0]],final_path):
                    print("Warning: page count in {} doesn't match input.".format(final_path))
                output_hash=mhu.hash_file_list([output_name],filedir)
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
make_user_check: open a script in the editor for preview 

'''
    

'''
Run pdflatex on a set of files (assuming pdflatex is available in path)

runs pdflatex in the given directory for each tex file listed in files
'''
def batch_compile(directory, files):
    here=".."
    try:
        here=os.getcwd()
        os.chdir(directory)
        for s in files:#compile examples
            try:
                #TODO allow other commands to be set in config
                sp.run(["pdflatex",s,"-aux-directory=./aux_files"],check=True, capture_output=True)
            except sp.CalledProcessError:
                raise#debug
                print("Compilation failed. Continuing...")
    finally:
        os.chdir(here) 

'''
Create tex files for marking all scripts in to_mark (assumed originals contained in script_directory)

run compiler on the output using batch_compile
'''
def pre_build(to_mark,script_directory):
    filedir=get_marked_path(script_directory)
    if not os.path.isdir(filedir):#create directory if necessary
        os.mkdir(filedir)
    to_compile=[]
    for tag in to_mark:
        #file to create/edit
        filepath=os.path.join(filedir,tag+config["marked suffix"])
        try:#check file exists
            with open(filepath,'r'):pass
        except:#create new file
            try:
                make_from_template(filepath,'../'+tag,
                                   count_pdf_pages([os.path.join(script_directory,p) for p in to_mark[tag][0]]))
                to_compile.append(tag+config["marked suffix"])
            except:
                print("Failed to create new file at: {}".format(filepath))
    batch_compile(filedir,to_compile)
    
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
def mark_one_loop(tag,to_mark,script_directory,question_names,source_validate,\
                  output_validate=False):
    marks_done={}#questions already marked for this script this pass
    quit_flag=False
    
    #source and output validation reset
    to_mark[tag][3]=False
    to_mark[tag][4]=['',{}]
    
    print("Marks on file: "+', '.join(["Q"+q+": "+to_mark[tag][2][q] \
                                       for q in to_mark[tag][2]]))
            
    while not quit_flag:
        
        marks,marked,outhash=make_user_mark(tag,to_mark,script_directory,\
                question_names,\
                source_validate, output_validate)
        #record scores in to_mark
        to_mark[tag][2].update(marks)
        marks_done.update(marks)


        if marked:
            print("Marks updated: "+', '.join(["Q"+q+": "+marks_done[q] for q in marks_done]))
            inp=input("Continue? (\'q\' to quit, \'r\' to review last) : ")
            if inp in ['q','Q']:
                quit_flag=True
                break
            if not inp in ['r','R']:
                #check also validation verdict from make_user_mark
                to_mark[tag][3]=source_validate#marked==True here. if not source_validate, don't assume checks complete
                
                #source validate should already be True if output_validate!
                if source_validate and output_validate: 
                    to_mark[tag][4][0]=outhash
                    to_mark[tag][4][1]={q:marks_done[q] for q in marks_done}
                break#all done for this script
        else:
            selection=input("Marking of "+tag+" not complete. Continue? (\'q\' to quit, \'s\' to skip this file): ")
            quit_flag=selection in ['q','Q']
            if selection in ['s','S']: break
    return not quit_flag


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
    config["script_dir"]=input("Script directory: ")
    try:
        with open("MarkHelper.cfg","w") as config_file:
            json.dump(config,config_file)
    except:
        print("Warning: Config not saved!")
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
            to_mark=check_marking_state(script_directory,question_names,source_validate)[0]#initialize to_mark from given script directory
        except:
            print("Failed to update marking state!")
            return True
        if to_mark=={}:
            print("Marking complete!")
            break
        try:#precompile
            print("Precompiling...")
            pre_build(to_mark,script_directory)
            print("Precompiling successful!")
        except:
            #raise#debug
            print("Precompiling failed!")
        for tag in to_mark:
            print("Now marking "+tag)
            quit_flag=not mark_one_loop(tag,to_mark,script_directory,question_names,
                                        source_validate,False)
            declare_marked(tag,script_directory,to_mark)#update marking state in file
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
        to_mark,done_mark=check_marking_state(script_directory,question_names,True,False)
    except:
        print("Failed to update marking state!")
        return True
    if to_mark!={}:
        print("Some scripts missing marks or validation: ")
        print_some(to_mark)
        return True
    try:#compile
        print("Compiling...")
        pre_build(to_mark,script_directory)#TODO VV
        print("Compiling successful!")
    except:
        #raise#debug
        print("Compiling failed!")
    for tag in to_mark:
        print("Now marking "+tag)
        quit_flag=not mark_one_loop(tag,to_mark,script_directory,question_names,
                                    source_validate,False)
        declare_marked(tag,script_directory,to_mark)#update marking state in file
        if quit_flag: break     
    return True

def cmd_makecsv(args):#begin marking 
    script_directory=config["script_dir"]
    
    out_path=os.path.join(get_marked_path(script_directory),
                          input("CSV filename: "))
    
    try:
        with open(out_path,'r'): pass
        if not input("File {} exists, overwrite? [y/n]: ".format(out_path)) in ['y','Y']:
            print("Operation cancelled.")
            return True
    except: pass
    
    inp=input("Questions for which to extract marks (separated by spaces): ")
    question_names=inp.split()
    
    final_validate=input("Require final validation of marking? [y/n]: ") in ["y","Y"]
    
    try:
         to_mark,done_mark=check_marking_state(script_directory,question_names,final_validate)#initialize to_mark from given script directory
    except:
        print("Failed to read marking state!")
        return True
    
    if to_mark!={}:
        print("Warning! Selected questions not marked in some scripts. Including scripts: ")
        print_some(to_mark)
    
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
                    file.write(",{}".format(done_mark[d][2][q]))
    except:
        print("Failed to write csv file.")
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
handlers={"quit":cmd_exit, "config":cmd_config, "begin":cmd_begin, 'makecsv':cmd_makecsv}#define handlers
def parse_cmd(cmd):
    toks=cmd.split()
    if len(toks)==0: return True#basic checks
    
    if toks[0] in handlers:
        try:
            return handlers[toks[0]](toks[1:])
        except:
            raise#debug
            print("Problem occured in {}".format(toks[0]))
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