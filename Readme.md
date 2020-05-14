# mark_helper

## Description
Python command line interface (CLI) application to paritially automate
marking/grading pdf files using third party source compiler e.g. pdflatex.
Suggested companion project <https://github.com/HappyGnome/markpage>

## Getting started
Launch the CLI by running `mark_helper.py` with python

### Dependencies
 Requires **python 3.7** with the standard library, and the following additional modules:
* [PyPDF2](https://pypi.org/project/PyPDF2/)


### Configuration
When you first launch the CLI you will be asked for various configuration options, including the path to your folder of script files. These options are explained in the reference for the `config` command. Options left blank will be set to default values.

### Naming for input pdf files
The program will look in the selected scripts directory for pdf files or groups of pdf files constituting a single script to mark. By default, files will be grouped together if they share the same name up to the suffix `_<n>.pdf` for an integer `<n>`.

Normally the **tag** that identifies the script internally will be the filename (without trailing `.pdf`). However for grouped files the tag is the part of the filename preceding `_<n>.pdf`

### Templates
A template is used to generate a source file for each script.

The template can include script lines using a special syntax, which are interpreted to generate the source file. The same scripting is used to extract values (e.g. marks) and validate the source file. See [Template scripting](#template_scripting).

## Template scripting <a name="template_scripting"></a>
