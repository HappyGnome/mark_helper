'''
MarkHelper.py

Author Ben Pooley
Date 01/04/2020

Tool to help streamline marking pdf scripts in tex
'''

import os
import logging


import loghelper
import mh_script_management as mhsm
import mh_edit_management as mhem

logger = logging.getLogger(__name__)
logging.basicConfig(filename="Log.txt")

g_config = mhsm.MarkingConfig("marking.cfg")

###############################################################################
# Command line interface
###############################################################################

# ************************************************************
# Command handlers


def cmd_exit(args):
    '''
    **CLI command:** Causes CLI loop to quit
    '''
    return False


def cmd_begin(args):
    """
    **CLI command:** Let user select some questions, then open each script
    source file in turn for editing. Check user's progress on each script when
    they close it
    """
    inp = input("Questions to mark (separated by spaces): ")
    question_names = inp.split()

    source_validate = input("Do final validation of source file? [y/n]: ") \
        in ["y", "Y"]

    quit_flag = False
    while not quit_flag:
        print("Checking marking state...")
        try:
            # initialize to_mark from given script directory
            to_mark = mhsm.check_marking_state(g_config, question_names,
                                               source_validate)[0]
        except Exception:
            loghelper.print_and_log(logger,
                                    "Failed to update marking state!")
            return True
        if to_mark == {}:
            print("Marking complete!")
            break
        try:  # precompile
            print("Precompiling...")
            mhem.pre_build(to_mark, g_config)

            print("Precompiling successful!")
        except Exception:
            loghelper.print_and_log(logger, "Precompiling failed!")
        for tag in to_mark:
            print("Now marking " + tag)
            quit_flag = not mhem.mark_one_loop(tag, to_mark, g_config,
                                               question_names,
                                               source_validate, False)
            # update marking state in file
            mhsm.declare_marked(tag, to_mark, g_config)
            if quit_flag:
                break
    return True


def print_some(data, n=10):
    '''
    for iterable `data` print up to `n` entries
    '''
    en = list(enumerate(data))

    for r in range(min(n, len(en))):
        # print(en[r])#debug
        print("{}".format(en[r][1]))


def cmd_build_n_check(args):#TODO detect changes and rebuild-check etc
    '''
    **CLI command:**
    Compile all marked scripts and open for the user to preview/edit, allowing
    them to check/modify the output. Record scripts for which
    this succeeds as having output validated
    '''

    inp = input("Questions required in completed scripts " +
                "(separated by spaces): ")
    question_names = inp.split()

    quit_flag=False
    while not quit_flag:
        print("Checking marking state...")
        try:
            # check for scripts with unmarked questions (from list) or which
            # have not had the source validated
            to_mark, done_mark = mhsm.check_marking_state(g_config,
                                                          question_names,
                                                          True, False)
            if to_mark != {}:
                print("Some scripts missing marks or validation: ")
                print_some(to_mark)
                return True
            # now all scripts validly marked
            # get all of those that need user to check output
            to_mark, done_mark = mhsm.check_marking_state(g_config,
                                                          question_names,
                                                          True, True)
        except Exception:
            loghelper.print_and_log(logger, "Failed to update marking state!")
            return True

        if to_mark == {}:
            print("Checking complete!")
            break

        try:  # compile
            print("Compiling...")
            mhem.batch_compile_and_check(g_config.marking_dir(), to_mark,
                                         g_config)
            print("Compiling successful!")
        except Exception:
            loghelper.print_and_log(logger, "Compiling failed!")
            return True
        for tag in to_mark:
            print("Now checking " + tag)
            quit_flag = not mhem.mark_one_loop(tag, to_mark, g_config,
                                               question_names,
                                               True, True)
            # update marking state in file
            mhsm.declare_marked(tag, to_mark, g_config)
            if quit_flag:
                break
    return True


def cmd_reset_validation(args):
    '''
    **CLI command:** Reset validation for particular file, or all files.
    Use argument \'all\' to reset all validation
    '''

    tags = []  # tags to reset
    if 'all' in args and input("Are you sure you would like to " +
                               "reset validation checks in ALL scripts?" +
                               " [y/n]: ") in ['y', 'Y']:
        tags = mhsm.get_script_list(g_config).keys()
    else:
        tags = [input("Enter script prefix (e.g. \'tag\' if \'tag.mkh\' " +
                      "needs resetting): ")]
    for tag in tags:
        try:
            mhsm.reset_validation(tag, g_config)
        except Exception:
            loghelper.print_and_log(logger, "Warning! Failed to reset " +
                                    "validation for {}".format(tag))
    return True

def cmd_makecsv(args):
    '''
    **CLI command:** Prompt user for question names and try to extract marks
    from each script mkh file for those questions. Store the results in a csv
    file specified by the user (stored in the original script directory)
    '''
    out_path = os.path.join(g_config.script_dir(),
                            input("CSV filename: "))

    try:
        with open(out_path, 'r'):
            pass
        if not input("File {} exists, overwrite? [y/n]: ".format(out_path))\
           in ['y', 'Y']:
            print("Operation cancelled.")
            return True
    except OSError:
        pass

    inp = input("Questions for which to extract marks (separated by spaces): ")
    question_names = inp.split()

    try:
        # initialize to_mark from given script directory
        to_mark, done_mark = mhsm.check_marking_state(g_config,
                                                      question_names,
                                                      True, True)
    except Exception:
        loghelper.print_and_log(logger, "Failed to read marking state!")
        return True

    if to_mark != {}:
        print("Selected questions may not be validly marked in some" +
              " scripts. Including: ")
        print_some(to_mark)
        print("Remember to run \'check\' command for final version.")
        return True

    try:
        with open(out_path, 'w') as file:
            file.write("Script #")  # header line
            for q in question_names:
                file.write(", Question {}".format(q))
            # body
            for d in sorted(done_mark.keys()):
                file.write("\n{}".format(d))
                for q in question_names:
                    file.write(",{}".format(done_mark[d][4][1][q]))
    except Exception:
        loghelper.print_and_log(logger, "Failed to write csv file.")
    return True


def cmd_make_merged_output(args):
    '''
    **CLI command:** Create blank pdf for each script and compile marked
    source files over the corresponding blank.

    Merge the output pdfs on top of copies of the original scripts to produce
    'final merged output'
    '''

    inp = input("Confirm questions required in completed scripts " +
                "(separated by spaces): ")
    question_names = inp.split()

    print("Checking marking state...")
    try:
        # check for scripts with unmarked questions (from list) or which
        # have not had the source validated
        to_mark, done_mark = mhsm.check_marking_state(g_config,
                                                      question_names,
                                                      True, True)
        if to_mark != {}:
            print("Some scripts missing marks or validation: ")
            print_some(to_mark)
            print("Please ensure all marking completed before merging.")
            return True
    except Exception:
        loghelper.print_and_log(logger, "Failed to update marking state!")
        return True

    '''
    Make blanks
    '''
    print("Making blanks...")
    blankdir = g_config.merged_dir()
    newsourcedir = g_config.merged_sourcedir()
    newfinaldir = g_config.final_dir()
    for path in [blankdir, newsourcedir, newfinaldir]:
        if not os.path.isdir(path):  # create directory if necessary
            os.mkdir(path)
    for d in done_mark:
        try:
            for file in done_mark[d][0]:  # constituent files
                mhsm.make_blank_pdf_like(os.path.join(g_config.script_dir(),
                                                      file),
                                         os.path.join(blankdir, file))
        except Exception:
            loghelper.print_and_log(logger,
                                    "Warning! Failed to make blanks for {}"
                                    .format(d))

    '''
    copy source files
    '''
    print("Copying source files...")
    to_compile = []
    for d in done_mark:
        try:
            mhem.copyFile(g_config.tag_to_sourcepath(d),
                          g_config.tag_to_mergesource(d))
            to_compile.append(d)
        except Exception:
            loghelper.print_and_log(logger, "Warning! Failed to copy source " +
                                    "file for {}".format(d))

    '''
    compile source files
    '''
    print("Compiling...")
    mhem.batch_compile_and_check(newsourcedir, to_compile, g_config)

    '''
    Merge files
    '''
    print("Merging...")
    for d in done_mark:
        try:
            mhsm.merge_pdfs(done_mark[d][0], g_config.tag_to_mergeoutput(d),
                            g_config.tag_to_mergefinal(d),
                            g_config.script_dir())
        except Exception:
            loghelper.print_and_log(logger,
                                    "Warning! Failed to merge output for {}"
                                    .format(d))
    print("Merge complete.")
    return True


# *****************************************************************************
# *****************************************************************************
# Main CLI cmd parser


g_handlers = {"quit": cmd_exit, "config": g_config.cmd_config,
              "begin": cmd_begin,
              'makecsv': cmd_makecsv,
              'check': cmd_build_n_check,
              'makemerged': cmd_make_merged_output,
              'invalidate': cmd_reset_validation}  # define handlers


def parse_cmd(cmd):
    '''
    Tokenize a string `cmd` and dispatch tokens [1:] to handler specified by
    the first from g_handlers.

    Returns
    -------
    True, or the value returned by the called handler
    '''
    toks = cmd.split()
    if len(toks) == 0:
        return True  # basic checks

    if toks[0] in g_handlers:
        try:
            return g_handlers[toks[0]](toks[1:])
        except Exception:
            loghelper.print_and_log(logger,
                                    "Problem occured in {}".format(toks[0]))
            return True
    else:
        print("Unrecognized command!")
        return True


# Initialization  #############################################################
try:  # load config
    g_config.load()
except OSError:
    g_config.cmd_config(['all'])

# Main CLI loop  ##############################################################
while True:
    cmd = input(">")
    if not parse_cmd(cmd):
        break
