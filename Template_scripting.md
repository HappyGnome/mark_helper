# Template scripting

## Introduction

When a template file is parsed to create a script file or a script file is analysed, certain 'active' lines can contain scripting to modify the output, return data to the parser (e.g. marks) or perform validation/cleanup. This section describes the scripting syntax and the way scripts are run in `mark_helper`.

In this section we will use the term 'source file' for the input to the parser in this section, although the input may be a template or something else during program operation.
We will use the term 'output' for the list of lines output from the parser to be saved in another text file (as opposed to the (pdf) output by the selected source compiler).

### Active lines
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

## Literals
Literal tokens begin and end with `'` and use the following escape sequences

|Text in literal | String interpreted by parser|
|---|---|
`\n`|newline
`\<char>`|`<char>`, for all other characters `<char>`

E.g. the active line `%#myline='"it\'s a yes\\no question"\n'` sets the variable `myline` (if recognised) to `"it's a yes\no question"` terminated by a newline.

## Command strings
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

### Command list
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
`\ftoi`|1|1|Convert string representing a float to string representing an integer
`\#ol`|0|1|Returns the line number for the next line of output (useful for bookmarking the current position in the output).
`\echo@`|2|None| Add the second string to the output at line number given by the first. E.g. `\echo@ \#ol 'here'` is equivalent to `\echo 'here'`.
`\r`|2|0 |The first string is a positive integer (`n`). The parser runs the rest of the input line (until a string results or unconsumed `\end`) `n` times and consumes the output. E.g. `\r '3' \echo 'ok' \end` adds three lines to output that each read `'ok'`.
`\set`|2|0|Set a recognised variable. First string consumed is the variable name and the second is its value. Adds new recognised variable if name not recognised. E.g.  `\set 'myvar' 'hi'` (note that the variable name is a literal).
`\==`|2|1 bool| Evaluates to true if two strings are identical.

## Lifecycle of a source file in mark_helper
Mark_helper creates source files by parsing a template file and re-parsing source files at various points. The lifecycle of a source file is as follows:
1. The file is created by running the parser on a template file with the following recognised variables:
    * `_init` : Flag (no input/output from parser - execution control only)
    * `_#pages` : Number of pages in associated script to mark (accross all pdf files)
    * `_in_path` : Prefix of path(s) of pdf documents for the script (E.g. '../myfile' for '../myfile.pdf', or '../myfile_1.pdf', '../myfile_2.pdf' etc.)

2. Before a file is opened for editing/marking, for each question to be marked the parser runs on the file with the recognised variables:
    *  `_question_reset` : Flag
    * `_question_name` : Name (or number) of the question that will be marked
    * `_question_prevmark` : The mark currently saved for this question, or an empty string '' if none is available.

3. Also before a file is opened for editing/marking, if validation will occur afterwards, the parser runs with the recognised variable:
    * `_final_assert_reset` : Flag

4. After the editor closes, if validation mode is active, he parser runs with the recognised variables:
    * `_final_assert` : This should be set to '1' during parsing if source file should pass validation.

5. For each question that was meant to be marked, the parser runs on the file with the recognised variables:
    * `_question_name` : The name of the question being queried
    * `_question_assert` : Should be set to '1' if named question is validly marked
    * `_question_mark` : Should be set to the mark of the selected question.

## Examples
*Comig soon...*
