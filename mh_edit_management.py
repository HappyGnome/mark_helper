# -*- coding: utf-8 -*-
"""
Created on Mon May 11 12:11:45 2020

@author: Ben

Methods involving creating and editing marked documents
"""
import os
import subprocess as sp
import shlex

import logging


import loghelper

import mh_hash
import mh_parsing as mhp
import mh_script_management as mhsm

logger = logging.getLogger(__name__)


def make_from_template(file_path, script_base_path, page_count, cfg):
    '''
    Using mh_parsing generate a new source file from template

    Parameters
    ----------
    `file_path` : Output path for new file

    `script_base_path` : variable to pass to parser specifying the prefix of
    the script path relative to the new source file. e.g. for a script residing
    in "myscript_1.pdf, myscript_2.pdf", this parameter should be "../myscript"

    `page_count` : number of pages in script across all files

    `cfg` : MarkingConfig (specifies parse line delimiter and template)

    Variables passed to parser:
        "_in_path" - prefix of path(s) of document(s) to mark,
        "_#pages" - number of pages in document
        "_init" - flag indicating initial file construction
    '''
    try:
        mhp.process_file(cfg.template(), file_path,
                         {"_in_path": script_base_path,
                          "_#pages": str(page_count),
                          "_init": "1"}, cfg.source_escape())
    except mhp.ParseError as e:
        print(e)
        raise


def reset_file_final_check(path, cfg):
    '''
    Open file at `path`, process with mhu and save back to same path

    Variables passed to parser:
        "_final_assert_reset" - flag indicating file should be set up
        for final assert
    '''
    try:
        mhp.process_file(path, path, {"_final_assert_reset": "1"},
                         cfg.source_escape())
    except mhp.ParseError as e:
        print(e)
        raise


def do_file_final_check(path, cfg):
    '''
    Open file at `path`, process with mhu and save back to same path

    Variables passed to parser:
        "_final_assert" - flag initially ='0' that should
        be '1' after parsing file iff the file should be reported as marked

    Returns
    --------
    bool : True iff assert succeeds
    '''
    var = {"_final_assert": "0"}
    try:
        mhp.process_file(path, path, var, cfg.source_escape())
        return var["_final_assert"] == "1"
    except mhp.ParseError as e:
        print(e)
        raise


def reset_file_q(path, question_name, cfg, previous_mark=''):
    '''
    Open file at `path`, process with mhu and save back to same path

    Variables passed to parser:
        "_question_reset" - flag indicating file should be set up
        for marking a question

        "_question_name" - name of the question e.g. '3a'
    '''
    try:
        mhp.process_file(path, path, {"_question_reset": "1",
                                      "_question_name": question_name,
                                      "_question_prevmark": previous_mark},
                         cfg.source_escape())
    except mhp.ParseError as e:
        print(e)
        raise


def do_file_q_check(path, question_name, cfg):
    '''
    Open file at `path`, process with mhu and save back to same path
    Attempt to extract mark for named question

    Variables passed to parser:
        "_question_mark" - (output) should be set to mark for completed
        question

        "_question_name" - name of the question being extracted e.g. '3a'

        "_question_assert" - (output) set to 1 to report marking validated for
        selected question
        N.B. the assert will be set to fail if _question_mark =''

    Returns
    -------
    [marked, score]
        `marked` : boolean indicating value of assert

        `score` : the string representing the score
    '''
    var = {"_question_mark": "", "_question_assert": "0",
           "_question_name": question_name}
    try:
        mhp.process_file(path, path, var, cfg.source_escape())
        marked = var["_question_assert"] == "1" and var["_question_mark"]
        return [marked, var["_question_mark"]]
    except mhp.ParseError as e:
        print(e)
        raise


def ready_source_file(filepath, tag, to_mark, cfg):
    """
    Check whether source file exists and create it from template if not

    Parameters
    ----------
    filepath : Desired path for the file
    tag : Key for the associated script data in to_mark
    to_mark : Dict of script data for current marking task (MKH format)
    cfg : MarkingConfig for current task (specifies template etc)

    Returns
    -------
    None.

    """
    make_new = False
    try:  # check file exists
        with open(filepath, 'r'):
            pass
    except OSError:  # create new file
        make_new = True
    if make_new:
        try:
            make_from_template(filepath, '../'+tag,
                               mhsm.count_pdf_pages
                               ([os.path.join(cfg.script_dir(), p)
                                 for p in to_mark[tag][0]]),
                               cfg)
        except Exception:
            loghelper.print_and_log(logger,
                                    "Failed to create new file at: {}"
                                    .format(filepath))


def open_one_to_edit(cfg, sourcefile):
    '''
    Run editor specified in `cfg` on selected sourcefile.
    Block until editor closes
    '''
    try:
        proc = sp.Popen([cfg.editor(),
                         sourcefile])
        proc.wait()
    except Exception:
        loghelper.print_and_log(logger,
                                "Error occurred editing document." +
                                " Check that the correct appliction is" +
                                " selected.")


def make_user_mark(tag, to_mark, cfg, questions=None,
                   final_validate_source=True, final_validate_output=False):
    '''
    Prepare blank file for user to mark, based on template
    open it in the editor
    when editor closes check that the job is done (all listed questions
    reported marked and marks available)

    Parameters
    ----------
    `tag` :
        prefix of script to mark (key in `to_mark`)

    `to_mark` :
        dict of scripts to mark in mkh format

    `cfg` :
        MarkingConfig object specifying details of marking job

    `final_validate_source` :
        if True then also check that source file passes
    final 'all-marked' checks

    `final_validate_output` :
        True check also that source has been compiled since saving and
        generate a hash value for the output to return
     NB: final output validation fails automatically if source validation
     disabled


    Returns
    -------
    `[marks,success,outhash]` : where:
        *`marks={name:mark}` for all questions validly marked

        *`success` =False only if final_validate_source==True
        and source validation fails, or if
        one of the requested questions fails validation
        (output validation has no effect)

        *`outhash` ='' or a hash string of the final output file
        (as generated by mh_hash.hash_file_list), if
        final_validate_output==True and
        all tests are passed (including final source validation)
    '''

    if not questions:
        questions = []

    if not os.path.isdir(cfg.marking_dir()):  # create directory if necessary
        os.mkdir(cfg.marking_dir())

    sourcefile = cfg.tag_to_sourcepath(tag)
    ready_source_file(sourcefile, tag, to_mark, cfg)

    # reset all variables to inspect later
    for q in questions:
        try:
            reset_file_q(sourcefile,
                         q, cfg, to_mark[tag][2].get(q, ''))
        except Exception:
            loghelper.print_and_log(logger,
                                    "Failed to reset question {} in {}"
                                    .format(q, sourcefile))
    if final_validate_source:
        try:
            reset_file_final_check(sourcefile, cfg)
        except Exception:
            loghelper.print_and_log(logger,
                                    "Failed to reset master assert in {}"
                                    .format(sourcefile))
    # get time of last change if output file exists and newer than source
    old_edit_epoch = -1
    try:
        old_edit_epoch = mhsm.get_edit_epoch([sourcefile,
                                              cfg.tag_to_outputpath(tag)])
    except OSError:
        pass  # old_edit_epoch=-1 already signifies it's not valid
    try:
        open_one_to_edit(cfg, sourcefile)
    # check state of resulting file
    # (must be called as counterpart to each reset)
    finally:
        # {question:mark} for all validly marked questions.
        # Bool indicates overall success
        ret = [{}, True, '']

        # set to indicate output checks passed
        # (but will not be returned unless source also validated)
        output_hash = ''
        if final_validate_output:
            # do this first or timestamps change
            new_edit_epoch = old_edit_epoch+1
            try:
                new_edit_epoch =\
                    mhsm.get_edit_epoch([sourcefile,
                                         cfg.tag_to_outputpath(tag)])
            except OSError:
                pass  # the following will fail by default. It's okay
            if old_edit_epoch < new_edit_epoch:
                print("Files edited. They should be checked again...")
            else:  # generate hash (also warn about page counts)
                if not mhsm.check_page_counts(
                        [os.path.join(cfg.script_dir(), p)
                         for p in to_mark[tag][0]],
                        cfg.tag_to_outputpath(tag)):
                    print("Warning: page count in {} doesn't match input."
                          .format(cfg.tag_to_outputpath(tag)))
                output_hash = mh_hash.hash_file_list([tag+cfg.output_suffix()],
                                                     cfg.marking_dir())
        if final_validate_source:
            try:
                ret[1] = ret[1] \
                    and do_file_final_check(sourcefile, cfg)
            except Exception:
                loghelper.print_and_log(logger,
                                        "Failed to perform final source" +
                                        " validation in {}"
                                        .format(sourcefile))
                ret[1] = False
        # inspect selected variables
        for q in questions:
            try:
                marked, score = do_file_q_check(sourcefile, q, cfg)
                if marked:
                    ret[0][q] = score
                else:
                    ret[1] = False
            except Exception:
                loghelper.print_and_log(logger,
                                        "Failed to extract data for" +
                                        " question {} in {}"
                                        .format(q, sourcefile))
                ret[1] = False
        # if source validation succeeded (incl final tests) set the
        # hash of the output
        if ret[1] and final_validate_source:
            ret[2] = output_hash

        return ret


def batch_compile(directory, files, compile_command, **kwargs):
    '''
    Runs string `compile_command` in terminal in the given `directory` for each
    source file listed in `files`

    Parameters
    ----------
    `directory` : directory in which to run compiler

    `files` : list of file paths to compile (relative to `directory`)

    `compile_command` : command line command to which file paths will be
    appended. shlex will be run on this argument to generate command line
    tokens

    `kwargs` :  Options are `cfg` - MarkingConfig for current job
    `manual_fallback` - if True `cfg` must be given
    user will be prompted to manually compile any files that
    failed
    '''
    here = ".."
    fail_list = []  # list of files that did not compile
    try:
        here = os.getcwd()
        os.chdir(directory)
        for i, s in enumerate(files):  # compile examples
            try:
                print("\rCompiling: {}/{}. ".format(i+1, len(files)), end='\r')
                cmd_toks = shlex.split(compile_command)
                cmd_toks.append(s)
                sp.run(cmd_toks, check=True, stdin=sp.PIPE, stdout=sp.PIPE,
                       stderr=sp.PIPE)

            except sp.CalledProcessError:
                fail_list.append(s)
                loghelper.print_and_log(logger,
                                        "Compilation failed for {}.".format(s))
                print(" Continuing...")
    finally:
        print('')  # newline to break from progress bar
        os.chdir(here)
    go_manual = kwargs.get('manual_fallback', False)
    if go_manual:
        print("There are {} files to compile manually.".format(len(fail_list)))
        for s in fail_list:
            open_one_to_edit(kwargs['cfg'], os.path.join(directory, s))
            if input("Continue compiling? (\'q\' to quit): ") in ["q", "Q"]:
                break


def batch_check_exist(directory, files):
    '''
    Try to open each file listed in `files` in folder `directory`. This
    is a basic check that e.g. a batch compilation has succeeded
    (though not sufficient in itself of course).

    OSError will occur from trying to open one of the files if it doesn't exist
    '''
    for file in files:
        try:
            with open(os.path.join(directory, file), 'r'):
                pass
        except Exception:
            print("Compiled file {} not available!".format(file))
            raise


def batch_compile_and_check(directory, tags, cfg, comp_if_output_exists=True):
    """
    Run a batch compile and batch check

    Parameters
    ----------
    directory : source file directory (also directory in which to run
    cfg.compile_command() )

    tags : iterable yielding prefixes of source files/output files

    cfg : MarkingConfig - used to add source and output suffixes to the tags

    comp_if_output_exists : if True (default) try to compile all source files
    indicated by `tags`. Otherwise check which already exist and ignore those.

    Returns
    -------
    None.

    Raises
    ------
    May raise e.g. OSError on failed check or other exceptions from batch
    compilation
    """
    if not comp_if_output_exists:
        newtags = []
        for tag in tags:
            try:
                with open(cfg.tag_to_outputpath(tag), 'r'):
                    pass
            except Exception:
                newtags.append(tag)
        tags = newtags
    source_filelist = [tag + cfg.marked_suffix() for tag in tags]
    output_filelist = [tag + cfg.output_suffix() for tag in tags]
    batch_compile(directory, source_filelist, cfg.compile_command(),
                  cfg=cfg, manual_fallback=True)
    batch_check_exist(directory, output_filelist)


def pre_build(to_mark, cfg):
    '''
    Create tex files for marking all scripts in to_mark

    Run compiler on all source files using batch_compile

    Parameters
    ----------
    `to_mark` : dict of mkh entries for scripts to mark

    `cfg` : MarkingConfig for current task
    '''
    if not os.path.isdir(cfg.marking_dir()):  # create directory if necessary
        os.mkdir(cfg.marking_dir())
    for tag in to_mark:
        # file to create/edit
        filepath = cfg.tag_to_sourcepath(tag)
        ready_source_file(filepath, tag, to_mark, cfg)
    batch_compile_and_check(cfg.marking_dir(), to_mark, cfg, False)


def mark_one_loop(tag, to_mark, cfg, question_names=None,
                  source_validate=False, output_validate=False):
    '''
    Perform loop to mark one script (or until user quits/skips file)
    Try to mark script `tag` in `to_mark`
    User will be prompted to edit file until all questions listed in
    `question_names` are marked.

    Parameters
    ----------
    `tag` :
        prefix of script to mark (key in `to_mark`)

    `to_mark` :
        dict of scripts to mark in mkh format

    `cfg` :
        MarkingConfig object specifying details of marking job

    `source_validate` :
        if True, also require source file to pass final validation

    `output_validate` : if True, also require output file to pass validation
                (fails anyway if `source_validate`==False)

    N.B. `to_mark[tag]` will be updated with any questions validly marked and
    applicable flags and hashes from validation

    Returns
    --------
    bool : True unless user quit loop early (returns True also if they chose to
                                              skip script rather than quit )

    '''
    marks_done = {}  # questions already marked for this script this pass
    quit_flag = False

    # source and output validation reset
    to_mark[tag][3] = False
    to_mark[tag][4] = ['', {}]

    print("Marks on file: " + ", ".join(["Q" + q + ": " + to_mark[tag][2][q]
                                         for q in to_mark[tag][2]]))

    while not quit_flag:

        marks, marked, outhash = make_user_mark(tag, to_mark, cfg,
                                                question_names,
                                                source_validate,
                                                output_validate)
        # record scores in to_mark
        to_mark[tag][2].update(marks)
        marks_done.update(marks)

        print("Marks updated: "+", ".join(["Q" + q + ": "+marks_done[q]
                                           for q in marks_done]))

        if marked:
            inp = input("Continue? (\'q\' to quit, \'r\' to review last) : ")
            # quit this loop and caller (but still try validating)
            if inp in ['q', 'Q']:
                quit_flag = True
            if inp not in ['r', 'R']:  # no validation yet
                # check also validation verdict from make_user_mark
                # marked==True here. if not source_validate,
                # don't assume checks complete
                to_mark[tag][3] = source_validate

                # source validate should already be True if output_validate!
                if source_validate and output_validate and outhash:
                    to_mark[tag][4][0] = outhash
                    to_mark[tag][4][1] = {q: marks_done[q] for q in marks_done}
                break  # all done for this script
        else:
            selection = input("Marking of "+tag+" not complete. Continue? " +
                              "(\'q\' to quit, \'s\' to skip this file): ")
            quit_flag = selection in ['q', 'Q']
            if selection in ['s', 'S']:
                break
    return not quit_flag


def copyFile(path_in, path_out):
    '''
    Attempt to copy
    source file from `path_in` to `path_out`
    (overwriting path_out if it exists)
    '''
    buflen = 100000
    with open(path_in, 'rb') as ifile:
        with open(path_out, 'wb')as ofile:
            while True:
                buf = ifile.read(buflen)
                if buf == b'':
                    break  # eof
                ofile.write(buf)
