#  -*- coding: utf-8 -*-
"""
Created on Mon May 11 12:06:04 2020

@author: Ben

Methods involving tracking marking progress, and script files
"""
import os
import json
import logging

import PyPDF2 as ppdf

import mh_hash
import loghelper
import config

logger = logging.getLogger(__name__)


class MarkingConfig(config.Config):
    '''
    Config with fields defining a marking task and directory structures
    '''

    def __init__(self, filepath="Default.cfg"):
        super().__init__(filepath)
        self.add_category("script")  # script file names directories etc
        self.add_property("script", "numsep", value="_",
                          prompt="File number separator: ")
        self.add_property("script", "suffix", value=".pdf",
                          prompt="Script suffix e.g. \'.pdf\': ")
        self.add_property("script", "directory", value="",
                          prompt="Script directory: ")
        # source file names directories, editors etc
        self.add_category("marking")
        self.add_property("marking", "editor", value="texworks",
                          prompt="Editor command: ")
        self.add_property("marking", "template", value="template.txt",
                          prompt="Template file path: ")
        self.add_property("marking", "directory", value="marking",
                          prompt="Sub-directory used for source files: ")
        self.add_property("marking", "marked suffix", value="_m.tex",
                          prompt="Suffix for marked source files e.g." +
                          "\'_m.tex\': ")
        self.add_property("marking", "output suffix", value="_m.pdf",
                          prompt="Suffix for marked output files e.g." +
                          "\'_m.pdf\': ")
        self.add_property("marking", "compile command", value="pdflatex",
                          prompt="Compile command (e.g. \'pdflatex\' to" +
                          " run \'pdflatex <source file>\'): ")
        self.add_property("marking", "source escape", value="%#",
                          prompt="Escape string to start active comment" +
                          " lines in template/source files e.g. \'%#\': ")
        self.add_category("merge")
        self.add_property("merge", "merged suffix", value="_m.pdf",
                          prompt="Suffix for final merged output files e.g." +
                          "\'_m.pdf\': ")
        self.add_property("merge", "merge directory", value="merge",
                          prompt="Sub-directory used to prepare for merge: ")
        self.add_property("merge", "final directory", value="final",
                          prompt="Sub-directory where final output appears: ")

    # handy access functions
    def numsep(self):
        '''
        Returns script/numsep property
        '''
        return self._categories["script"]["numsep"]

    def script_suffix(self):
        '''
        Returns script/suffix property
        '''
        return self._categories["script"]["suffix"]

    def script_dir(self):
        '''
        Returns script/directory property
        '''
        return self._categories["script"]["directory"]

    def editor(self):
        '''
        Returns marking/editor property
        '''
        return self._categories["marking"]["editor"]

    def template(self):
        '''
        Returns marking/template property
        '''
        return self._categories["marking"]["template"]

    def marking_dir(self):
        '''
        Returns full path to marking directory (sub directory of script dir)
        '''
        return os.path.join(self.script_dir(),
                            self._categories["marking"]["directory"])

    def marked_suffix(self):
        '''
        Returns marking/marked suffix property
        '''
        return self._categories["marking"]["marked suffix"]

    def output_suffix(self):
        '''
        Returns marking/output suffix property
        '''
        return self._categories["marking"]["output suffix"]

    def compile_command(self):
        '''
        Returns marking/compile command property
        '''
        return self._categories["marking"]["compile command"]
    
    def source_escape(self):
        '''
        Returns escape string used to start \'active comment\' lines in source 
        files
        '''
        return self._categories["marking"]["source escape"]

    def merged_suffix(self):
        '''
        Returns merge/merged suffix property
        '''
        return self._categories["merge"]["merged suffix"]

    def merged_dir(self):
        '''
        Returns full path to merging directory (sub directory of script dir)
        '''
        return os.path.join(self.script_dir(),
                            self._categories["merge"]["merge directory"])

    def merged_sourcedir(self):
        '''
        Returns full path to directory for source files
        when merging (sub directory of merging dir)
        '''
        return os.path.join(self.merged_dir(), "source")

    def final_dir(self):
        '''
        Returns full path to final merge output
        directory (sub directory of script dir)
        '''
        return os.path.join(self.script_dir(),
                            self._categories["merge"]["final directory"])

    def tag_to_sourcepath(self, tag):
        '''
        Given `tag` return full path to associated source file
        '''
        return os.path.join(self.marking_dir(), tag+self.marked_suffix())

    def tag_to_outputpath(self, tag):
        '''
        Given `tag` return full path to associated output file
        '''
        return os.path.join(self.marking_dir(), tag+self.output_suffix())

    def tag_to_mergesource(self, tag):
        '''
        Given `tag` return full path to associated source file in merge folder
        '''
        return os.path.join(self.merged_sourcedir(),
                            tag+self.marked_suffix())

    def tag_to_mergeoutput(self, tag):
        '''
        Given `tag` return full path to associated compiled output in merge
        folder
        '''
        return os.path.join(self.merged_sourcedir(),
                            tag+self.output_suffix())

    def tag_to_mergefinal(self, tag):
        '''
        Given `tag` return full path to associated final merged output file
        '''
        return os.path.join(self.final_dir(), tag+self.merged_suffix())


def get_script_list(cfg):
    '''
    Parameters
    ----------
    cfg : MarkingConfig specifying current job

    Return
    ------
    {tag:file_list} where tag is the prefix of a collection of files in
    script_directory e.g. script1.pdf  => tag = script1, and file_list is a
    list of the files (pdfs) that comprise the script
    '''

    ret = {}

    script_files_raw = os.listdir(cfg.script_dir())
    suffix = cfg.script_suffix()

    # extract only pdfs and strip '.pdf'
    script_files_pdf = [f[:-len(suffix)] for f in script_files_raw
                        if f.endswith(suffix)]
    script_files_pdf.sort()  # ensure files with same tag appear in same order

    # add file names to list, accounting for doc numbers
    for scr in script_files_pdf:
        tag = scr  # default tag in to_mark
        sep_ind = scr.rfind(cfg.numsep())  # look for trailing number
        if sep_ind > 0:  # sep found in valid place
            if scr[sep_ind+1:].isnumeric():
                tag = scr[:sep_ind]
        if tag in ret:
            ret[tag].append(scr+suffix)
        else:
            ret[tag] = [scr+suffix]
    return ret


def check_marking_state(cfg, questions=None, final_assert=True,
                        match_outhash=False):
    '''
    check source directory for files or file sets,
    check which .mkh files exist and are up to date

    Parameters
    ----------
    cfg : MarkingConfig specifying current job

    questions : if set to a list of question names
    then any scripts which have not had all of those questions marked will be
    returned

    final_assert : if True then any file that has not passed final validation
    will also be included

    Returns
    -------
    [to_mark, done_mark]: lists of scripts left to mark and marked in mkh
    format.
    (A script is 'marked' in this case if all requested questions are available
    and final validation reported complete, if final_assert == True)

    if match_outhash == True then additionally, scripts will appear in to_mark
    if the final output hash is not saved or does not match the actual output
    file
    '''

    script_directory = cfg.script_dir()
    if not questions:
        questions = []

    to_mark_temp = get_script_list(cfg)
    ret = [{}, {}]  # to_mark, done_mark

    for tag in to_mark_temp:
        # input hash, question marks, source validate flag, output hash
        to_mark_temp[tag] = [to_mark_temp[tag], '', {}, False, '']
        files_hash = mh_hash.hash_file_list(to_mark_temp[tag][0],
                                            script_directory)
        marked = False  # file exists and all questions marked?
        # check for matching .mkh file
        if tag+'.mkh' in os.listdir(script_directory):
            try:
                with open(os.path.join(script_directory, tag+".mkh"),
                          "r")as mkh:
                    mkh_data = json.load(mkh)
                    # extract non-hash, non-path data
                    to_mark_temp[tag][2:] = mkh_data[2:]
                    # if hashes don't match it's not marked!
                    if mkh_data[:2] == [to_mark_temp[tag][0], files_hash]:
                        marked = mkh_data[3] or not final_assert
                        marklist = mkh_data[2]
                        #  in output validation mode
                        #  check marks from validation instead
                        if match_outhash:
                            marklist = mkh_data[4][1]
                        # make sure all questions marked too
                        for que in questions:
                            if que not in marklist:
                                marked = False
                                break
                        if match_outhash:
                            outhash = mh_hash.hash_file_list(
                                [tag + cfg.output_suffix()],
                                cfg.marking_dir())
                            # outhash valid and matches saved value
                            marked = marked and outhash == \
                                mkh_data[4][0] and outhash

                    else:
                        print("Warning: originals modified for script {}"
                              .format(tag))
            except (OSError, TypeError, ValueError):
                loghelper.print_and_log(logger, "Error occurred checking {}"
                                        .format(tag))
                marked = False

        # add to to_mark
        if not marked:
            ret[0][tag] = to_mark_temp[tag]
            ret[0][tag][1] = files_hash
        else:
            ret[1][tag] = to_mark_temp[tag]
            ret[1][tag][1] = files_hash
    return ret


def get_edit_epoch(paths):
    """
    Return maximum modification timestamp among files at a list of directories

    Parameters
    ----------
    paths : list of strings specifying the filepaths to check

    Returns
    ------
    result of os.stat(...).st_mtime called on last modified file
    """
    times=[os.stat(path).st_mtime for path in paths]
    return max(times)


def check_page_counts(input_pdf_paths, output_pdf_path):
    """
    Do extra checks on page counts

    Parameters
    ----------
    input_pdf_paths : list of filepaths making up a script

    output_pdf_path : single filepath of output file to compare

    Returns
    -------
    bool : False if number of pages in all files listed in the list
    input_file_paths does not match the page count in pdf_path (or if a file
    cannot be read)
    """
    return count_pdf_pages(input_pdf_paths) \
        == count_pdf_pages([output_pdf_path])


def count_pdf_pages(file_paths):
    '''
    given a list of file paths (all pdfs) sum the numbers of pages in those
    files

    Parameter
    ---------
    file_paths : list of paths to pdf files

    Returns
    -------
    number of pages found
    '''
    pages = 0
    for fip in file_paths:
        try:
            reader = ppdf.PdfFileReader(fip)
            pages += reader.getNumPages()
        except (ppdf.utils.PdfReadError, OSError):
            loghelper.print_and_log(logger,
                                    "Could not count pages in {}"
                                    .format(fip))
    return pages


def declare_marked(tag, to_mark, cfg):
    '''
    To be called when marking state of script with given tag deemed to have
    changed. Create/update associated mkh file

    Parameters
    ----------
    tag : internal tag of script

    script_directory : directory of script files (where mkh files live)

    to_mark : dictionary of mkh entry data for current doc list
    (tag is a key for this)


    MKH file format
    ===============
    *.mkh is a json file containing a list


    [`filenames`,`hash`,`questions`,`final_valid`,
     [`output_hash`,`qs_valid`]] where:

        `filenames` : list of file paths corresponding to the tag

        `hash` : hash value of those files at the time they were
        deemed marked

        `questions` : {'question':'mark'} for `question`s
        asserted as marked. `mark` is the recorded mark

        `final_valid` : True when source file passed a final validation
        check last time it was marked

        `output_hash` : '' or a hash of the output (pdf) when both source
        and output validation have succeeded

        `qs_valid` : {`question_name`: `mark`} (as in questions)
        for all questions checked when `output_hash` last set
    '''
    with open(os.path.join(cfg.script_dir(),
                           tag+".mkh"), "w") as mkh:
        json.dump(to_mark[tag], mkh)


def reset_validation(tag, cfg):
    '''
    Look for mkh file associated to `tag` and reset validation elements

    Parameters
    ----------

    `tag` : prefix of mkh file to look for

    `cfg` : config of marking job (specifies directory to check)

    Raises
    ------
    OSError if mkh file not found

    TypeError or ValueError if JSON fails

    ValueError if data format invalid
    '''
    filepath = os.path.join(cfg.script_dir(), tag+".mkh")
    mkh_data = None
    with open(filepath, 'r') as file:
        mkh_data = json.load(file)
    try:
        mkh_data[3:] = [False, ['', {}]]
    except (IndexError, KeyError):
        raise ValueError("Invalid mkh data for {}!".format(tag))
    with open(filepath, 'w') as file:
        json.dump(mkh_data, file)


def make_blank_pdf_like(in_path, out_path):
    '''
    Copy a pdf from `in_path` and create a new pdf at `out_path` (may overwrite
    existing file)
    with the same number of pages as input and each page the same size as the
    corresponding one in input. Each page of the output is blank.

    Parameters
    ----------
    in_path : path of file to use as template

    out_path : path of file to create/overwrite
    '''
    reader = ppdf.PdfFileReader(in_path)
    writer = ppdf.PdfFileWriter()
    for i in range(reader.getNumPages()):
        dims = reader.getPage(i).mediaBox
        writer.addBlankPage(abs(dims.lowerRight[0]-dims.lowerLeft[0]),
                            abs(dims.upperRight[1]-dims.lowerRight[1]))

    with open(out_path, "wb") as file:
        writer.write(file)


def merge_pdfs(files_below, file_above, out_path, below_dir=''):
    """
    Add content of a pdf above a another (spread over one or more files)
    to create one file.

    Parameters
    ----------
    files_below : list of strings
        Paths to the pdfs to use as base layer. files_below[0] contains page 1
        etc...
        full paths, or paths relative to below_dir, if set
    file_above : string
        full path to pdf to overlay
    out_path : string
        full path to output file to generate
    below_dir : directory for files in files_below

    Raises
    ------
    ValueError
            if number of pages in the two input files don't match
            or if page sizes don't match

    Returns
    -------
    None.

    """

    # pylint: disable=too-many-locals
    # not too bad

    readers_below = [ppdf.PdfFileReader(os.path.join(below_dir, f))
                     for f in files_below]
    reader_above = ppdf.PdfFileReader(file_above)

    pagecount_below = 0
    for rea in readers_below:
        pagecount_below += rea.getNumPages()
    if pagecount_below != reader_above.getNumPages():
        raise ValueError("Pagecount mismatch.")

    page_at = 0  # index of page being added
    writer = ppdf.PdfFileWriter()
    for reb in readers_below:
        for i in range(reb.getNumPages()):
            page = None
            page = reb.getPage(i)
            page_above = reader_above.getPage(page_at)

            dims = page.mediaBox
            dims_above = page.mediaBox
            if dims.lowerLeft != dims_above.lowerLeft or\
               dims.upperRight != dims_above.upperRight:
                raise ValueError("Page size mismatch")

            page.mergeScaledPage(page_above, 1.0, True)

            writer.addPage(page)
            page_at += 1

    with open(out_path, "wb") as file:
        writer.write(file)


###############################################################################
if __name__ == '__main__':
    make_blank_pdf_like("ToMark/silly_marked.pdf",
                        "ToMark/like_silly_marked.pdf")
