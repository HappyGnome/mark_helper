# mark_helper

## Outline
Python command line interface (CLI) application to paritially automate
marking/grading pdf files using third party source compiler e.g. pdflatex.
Suggested companion project <https://github.com/HappyGnome/markpage>

### Dependencies
 Requires **python 3.7** with the standard library, and the following additional modules:
* [PyPDF2](https://pypi.org/project/PyPDF2/)

## Basic operation
Launch the CLI by running `mark_helper.py` with python

### Configuration
When you first launch the CLI you will be asked for various configuration options, including the path to your folder of script files. These options are explained in the [reference](#config_ref) for the `config` command. Options left blank will be set to default values.

### Naming for input pdf files
The program will look in the selected scripts directory for pdf files or groups of pdf files constituting a single script to mark. By default, files will be grouped together if they share the same name up to the suffix `_<n>.pdf` for an integer `<n>`.

Normally the **tag** that identifies the script internally will be the filename (without trailing `.pdf`). However for grouped files the tag is the part of the filename preceding `_<n>.pdf`

### Templates
A template is used to generate a source file for each script.

The template can include script lines using a special syntax, which are interpreted to generate parts of the source file. The same scripting is used to extract values (e.g. marks) and validate the source file. See [Template scripting](#template_scripting).

### Starting marking (`begin`)
With the configuration options set, type `begin` at the prompt to start marking. You will be asked to input the question numbers to mark; enter these in one line separated by spaces (question names/numbers shoud not contain spaces and need not match anything in the underlying script).

You will be prompted about whether to do final validation on the source file once it is closed (default is no). Select 'y' at this point when (and only when) you intend this as the final pass before checking and merging. **If you forget** you will later have to revisit each un-finalised script with another pass of `begin` (with finalise selected!)

The mark_helper will then find all scripts which have not had those questions validly marked and open them one at a time for you to edit. If final validation is enabled then any un-validated source files will also be opened.

When you close a script, some checks are performed and if successful you can press `Enter` at the continue prompt to open the next script. If a problem is detected (or you elect to revisit the last script), the same one will open again for further editing.

You can quit between scripts or skip an incomplete script by entering `q` or `s` respectively, when prompted. Existing progress on the current script and previous ones will be saved*.

\* Data about the marking state of each script is held in `*.mkh` files in the script directory. Modifying these may have unexpected results.

### Checking marking (`check`)
The `check` command should be used after all the desired questions have been marked in all scripts (and the last one with the finalise option selected).

As with `begin`, `check` prompts for a list of questions. This time list **all** of the questions that you are supposed to have marked.

`check` may direct you to run `begin` more times to mark/finalise incomplete scripts. Otherwise all of the scripts will be compiled (this may take some time) and opened once again in the editor for you to check the output.

If you are happy with the preview of a script file simply close the editor. If you spot a mistake (or the marks shown in the CLI are incorrect) you can correct the source file here.

Note that saving or compiling a file will be detected and you will be prompted to re-check it later.

### Merging output (`makemerged`)
*EXPERIMENTAL*

Some features present in the script file may be stripped out by the marking process\*. E.g. if marking with LaTeX and pdfpages then annotations from other markers ay have been removed. To circumvent this, then `makemerged` function is used to extract your modifications to the script and add them back over the original.

When checking is complete, you can run `makemerged`. Once again you are prompted for the questions that are required to be marked. The merge will not complete unless all checking has been done for those questions in all scripts.

The process of generating the merged output is as follows:
1. For each script file, a pdf with matching page dimensions but no content is produced in the merging sub-directory (as specified in the config).
2. Each source file is copied into a sub-directory of the merging directory and compiled, to produce annotations over a blank document.
3. The new outputs are merged over the original scripts page-by-page to produce new pdfs in the 'final' sub-directory (as set in config)

\* If your marking process may strip pdf features make sure that your students are not using those features!
### Other commands
#### `config`
See [config options](#config_ref) section

#### `invalidate`
Prompts user for the tag of a script file from which to remove validation (causing it to need re-marking and re-checking). Marks currently saved for each question are not removed.

Use `invalidate all` to do this for all scripts. **Warning:** This will mean having to remark and recheck all scripts!

#### `makecsv`
Extract the marks for selected questions to produce a csv file. Will fail if these questions have not been marked or not checked for one of the scripts.

#### `quit`
Exits the CLI

## Config options <a name="config_ref"></a>
Use command `config <sec>` to set a particular section of the config options, or `config all` to set all sections. Available sections are:
+ `script` : concerning script filenames and directories
+ `marking` : concerning templates, source files, editor applications and source file compilation
+ `merge` : concerning merging process of new annotations into (copies of) the original script files

When prompted for a configuration option you can enter a new value to change it, or enter nothing to leave it unchanged.

### Main options in `config script`
The script directory is the main option here. This is where the program will look for the script files. All directories used for source files and merging will be sub-directories of this one.

### Main options in `config marking`
The editor option specifies the terminal command to open a source file in your prefered editor. The program will try to call `<editor> <source_file>` from the terminal, where `<source_file>` is the name of the source file to open and `<editor>` is the string you set here.

The template filepath specifies the template file to parse to generate each source file.

The compile command is the command that will be run on the terminal to compile your source files. Similar to the editor option. The working directory for this command will be the directory containing the source file. E.g. set this to `pdflatex` to run `pdflatex <source_file>` to compile `<source_file>`.

The source escape option allows you to change how 'active' lines begin in the template and source files.
An 'active' line is one to be parsed and should use the syntax defined in [Template scripting](#template_scripting). Default is '%#' as these are already comment lines in TeX.

## Template scripting <a name="template_scripting"></a>

### Introduction

When a template file is parsed to create a script file or a script file is analysed, certain 'active' lines can contain scripting to modify the output, return data to the parser (e.g. marks) or perform validation/cleanup. This section describes the scripting syntax and the way scripts are run in `mark_helper`.

In this section we will use the term 'source file' for the input to the parser in this section, although the input may be a template or something else during program operation.
We will use the term 'output' for the list of lines output from the parser to be saved in another text file (as opposed to the (pdf) output by the selected source compiler).

#### Active lines
Lines in source files beginning with `%#` (or as set in `config marking`) are
**active** lines that will be analysed closely by the parser. Other lines are generally
added directly to the output without modification.

An active line has the format `%#<varname>=<tokens>`. When `<varname>` is recognised, the tokens following `=` are interpreted from left to right until an unconsumed string results. That string is then assigned to the named variable (`<varname>`).

When the parser runs, it is given a list of **recognised** variables, and the values of these
variables after as modified in parsing the file may be read afterwards. In this way, the program can control which script lines execute during a particular parse. Active lines can also create new variables for use in later lines

By default, if `<varname>` is recognised, the active line is consumed and does not appear in the output, but this can be overridden (see `\k` command). Active lines in which `<varname>` is not recognised are treated like normal lines and added to the output.

`<tokens>` is a space separated sequence of `<token>` strings, each having one of three types:
+ **Commands** : begin with `\` and may consume some tokens following them
+ **Literals** : begin and end with unescaped `'` and can contain whitespace
+ **Other** : All other tokens contain no white space and if they match a recognised variable, the value of that variable will be substituted (after conversion to a string). Otherwise these tokens evaluate to the token string itself (but without any character escaping).

E.g. `token` and `'token'` evaluate to the same string (assuming `token` is not a recognised vairable name). However `'toke\n'` evaluates to a string with a newline at the end, whereas `toke\n` becomes a string ending `\n`.

**Good practice:** it's best not to rely on this default-literal behaviour. For a non-command token where
substitution by recognised variables is not desired, use an escaped literal.

### Literals
Literal tokens begin and end with `'` and use the following escape sequences

|Text in literal | String interpreted by parser|
|---|---|
`\n`|newline
`\<char>`|`<char>`, for all other characters `<char>`

E.g. the active line `%#myline='"it\'s a yes\\no question"\n'` sets the variable `myline` (if recognised) to `"it's a yes\no question"` terminated by a newline.

### Command strings
The only functionality available with just literals and other tokens is resetting recognised variable values.

With command strings, we can make the parser to perform certain other actions to influence the parsed output.

Many command tokens do not create strings to be consumed so that the evaluation of such commands does not end the parsing of the active line. Furthermore, many commands consume the parsed values of tokens that follow them.

**Example:** `\k` consumes no tokens and evaluates to `None` (not a string), while `\==` consumes two strings and returns one.

    `%#myvar=\== \k 'a' 'b'`

   sets
`myvar` to `'0'` as follows:
1. `\==` demands two strings from the parser.
2. `\k` is encountered and the command runs but returns no string
3. `'a'` is encountered
4. `'b'` is encountered
5. `\==` now has its two strings `'a'` and `'b'` and returns `'0'`
6. `'0'` is not consumed and so `myvar` receives this value and parsing of the line terminates.

#### Command list
The following commands are available. Note that a **bool** (Boolean) string is expected to be `'1'` or `'0'` representing true or false respetively.


|Command|# strings consumed|strings produced| Description|
|---|:---:|:---:|---|
`\k`|None|None| Adds current line to output (prevents default behaviour of consuming parsed lines).
`\skip`|None|None|Remove one line following this one from the input. Preventing it from being parsed or added to the output.
`\echo`| 1 |None| Append string to output (followed by a new line).
`\+`|2|1| Return the concatenation of two strings.
`\&&`|2 bools|1 bool| Logical AND
|<code>\\\|\|</code>|2 bools|1 bool| Logical OR
`\!!`|1 bool|1 bool| Logical NOT
`\if`|1 bool + 2 other/`end`s|1 or None| Consume first bool. If it's true, parse tokens until a string results, or unconsumed `\end` found, then skip tokens (suppressing all functionality) until string results or `\end` found. If the bool is false,  skip until one string results (or until `\end`) and then parse until 1 string results (or until `\end`).
`\end`|0|0|End argument of `\if` or `\r` before string results.
`\regex`|1|1 bool|Interpret a string as a [regex](https://docs.python.org/3/library/re.html). Return true if the input line following this one contains matches to the regex. Note that escape sequences in the regex still need to be escaped in the literal token. E.g. `\regex '\\\\'` creates the regex `'\\'` so results in `'1'` if the following line contains `\`.
`\+f`|2|1| Convert two strings to floats and add them.
`\+d`|2|1| Convert two strings to ints and add them.
`\#ol`|0|1|Returns the line number for the next line of output (useful for bookmarking the current position in the output).
`\echo@`|2|None| Add the second string to the output at line number given by the first. E.g. `\echo@ \#ol 'here'` is equivalent to `\echo 'here'`.
`\r`|2|0 |The first string is a positive integer (`n`). The parser runs the rest of the input line (until a string results or unconsumed `\end`) `n` times and consumes the output. E.g. `\r '3' \echo 'ok' \end` adds three lines to output that each read `'ok'`.
`\set`|2|0|Set a recognised variable. First string consumed is the variable name and the second is its value. Adds new recognised variable if name not recognised. E.g.  `\set 'myvar' 'hi'` (note that the variable name is a literal).
`\==`|2|1 bool| Evaluates to true if two strings are identical.



### Examples
*TODO*
