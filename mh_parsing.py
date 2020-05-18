# -*- coding: utf-8 -*-
"""
Created on Wed Apr  1 10:20:52 2020

@author: Ben
"""
import re
import copy

import logging

# import loghelper

logger = logging.getLogger(__name__)


def nextToken(string):
    """
    Extract and classify next token from a string

    Parameters
    ----------
    string : string to parse

    Returns
    -------
    [tok, toktype, newstring] : where
        `tok` : a substring of `string`, or '' if nothing found

        `newstring` : is input `string` with tokens consumed

        `toktype` : either \'literal\', \'command\', or \'other\'


    Notes
    --------------
    toktypes:
        literal:
            for "a a\' "+<backslash>+"n" in `string` set
            `tok`  = "a a\' "+<endl>

        command:
            for substring <backslash>+"mycmd", tok = "mycmd"

         otherwise tok = substring
    list of escaped characters in literal mode:
        default :  <backslash><char> -> <char>
            e.g. for literal \' in string, ' is added to tok
        newline : <backslash>n : <endl>
            e.g. ...
    """
    # determine type:
    toks = string.split()
    toktype = 'other'
    continue_from = 0  # index of first character after parsed content
    try:
        if toks[0][0] == '\'':
            toktype = 'literal'
        elif toks[0][0] == '\\':
            toktype = 'command'
        continue_from = string.find(toks[0])+len(toks[0])
    except IndexError:
        return ['', 'other', '']

    if toktype == 'command':
        # strip leading slash and return
        return [toks[0][1:], 'command', string[continue_from:]]
    if toktype == 'literal':
        lit_start = string.find('\'')+1  # start of string
        str_build = ''
        # find string end
        escaped = False
        esc_repl = {'n': '\n'}
        i = 0
        for i, c in enumerate(string[lit_start:]):
            if escaped:
                c = esc_repl.get(c, c)
                str_build = str_build+c  # just c unless c in esc_repl
                escaped = False
            elif c == '\\':  # escape next char
                escaped = True
            elif c == '\'':  # unescaped '  => end of literal
                break
            else:
                str_build = str_build+c  # just c unless c in esc_repl
        return [str_build, 'literal', string[lit_start+i+1:]]

    # other
    return [toks[0], 'other', string[continue_from:]]


def makeTokens(string):
    '''
    By repeatedly calling `nextToken` split `string` into list of tokens
    Returns
    --------
    [[tok0, toktype0], ...]
    '''
    ret = []
    while string:
        val = nextToken(string)
        string = val[2]
        ret.append(val[:2])
    return ret

###############################################################################
# command evaluation/distribution


class ParseError(Exception):
    '''
    raised to indicate an error parsing script line
    '''


class IfStop(Exception):
    '''
    raised to end a branch in lieu of a token
    '''

    def __init__(self):
        super().__init__("Unexpected \\end!")


def interpret(toks, n, lines, cur_line, out_lines, variables):
    '''
    Given list of tokens [`value`, `toktype`]
    try to return a list of `n` variables consisting of literals,
    these are:
        *the literal tokens themselves,

        *obtained by evaluating command tokens

        *or substitutions for other tokens
    Parameters:
    -----------
    toks : the list of tokens

    n : max literals to return

    lines : list of lines (un parsed) in current file

    cur_line : index in lines of current line

    out_lines : list of lines to be output by parsing current file

    variables : dictionary of variables. commands are only processed if they
    involve variable names appearing here.
    Variables are also used to substitute 'other' type tokens

    Returns
    -------
    up to `n` strings, but may be fewer if `line` ends beforehand

    '''
    ret = []
    while len(ret) < n:
        val = None
        try:
            tok = toks.pop(0)
            val = tok[0]
        except IndexError:
            raise ParseError("Not enough tokens!")
        if tok[1] == 'command':
            val = command_list[tok[0]](toks,
                                       lines, cur_line, out_lines,
                                       variables)
        elif tok[1] == 'literal':
            pass  # default is to treat tok as literal
        else:  # assume other and try substitution
            try:
                val = variables[tok[0]]
            except KeyError:
                pass
        if val is not None:
            # double check it's a string
            ret.append(str(val))
    return ret

###############################################################################
# command handlers


def cmd_echo_thisline(toks,
                      lines, cur_line, out_lines, variables):
    '''
    command to add current line to output and return no token

    <backslash>k
    '''

    out_lines.append(lines[cur_line][:])
    return None  # interpret(toks, 1, lines, cur_line, out_lines, variables)[0]


def cmd_delnxtline(toks,
                   lines, cur_line, out_lines, variables):
    '''
    command remove next line from input and returns no token
    <backslash>skip
    '''
    try:
        lines.pop(cur_line+1)
    except IndexError:
        pass
    return None  # interpret(toks, 1, lines, cur_line, out_lines, variables)[0]


def cmd_echo(toks, lines, cur_line, out_lines, variables):
    '''
    command to add line to output and return no token
    <backslash>echo <text>
    '''
    text = interpret(toks, 1,
                     lines, cur_line, out_lines, variables)[0]+"\n"

    out_lines.append(text)
    return None  # interpret(toks, 1, lines, cur_line, out_lines, variables)[0]


def cmd_concat(toks, lines, cur_line, out_lines, variables):
    '''
    command to concatenate two tokens
    <backslash>+ <str1> <str2>
    '''
    try:
        vals = interpret(toks, 2,
                         lines, cur_line, out_lines, variables)
        return vals[0]+vals[1]
    except ParseError:
        raise
    except Exception:
        logger.exception("Parsing error")
        raise ParseError("Concatenation failed!")


def cmd_addf(toks, lines, cur_line, out_lines, variables):
    '''
    command to interpret next two tokens as float numbers and add them
    <backslash>+f <str1> <str2>
    '''
    try:
        vals = interpret(toks, 2,
                         lines, cur_line, out_lines, variables)
        return str(float(vals[0])+float(vals[1]))
    except ParseError:
        raise
    except Exception:
        logger.exception("Parsing error")
        raise ParseError("Addition failed!")


def cmd_ftoi(toks, lines, cur_line, out_lines, variables):
    '''
    command to format next token (floating point) as integer
    <backslash>int <str1> <str2>
    '''
    try:
        return str(int(float(interpret(toks, 1,
                                       lines, cur_line, out_lines,
                                       variables)[0])))
    except ParseError:
        raise
    except Exception:
        logger.exception("Parsing error")
        raise ParseError("Integer conversion failed!")


def cmd_and(toks, lines, cur_line, out_lines, variables):
    '''
    return '1' or '0' corresponding to boolean and of next two tokens
    Token represents True if it's '1' otherwise it's false
    '''
    try:
        vals = interpret(toks, 2,
                         lines, cur_line, out_lines, variables)
        return str(int(vals[0] == '1' and vals[1] == '1'))
    except ParseError:
        raise
    except Exception:
        logger.exception("Parsing error")
        raise ParseError("Boolean \'and\' failed!")


def cmd_not(toks, lines, cur_line, out_lines, variables):
    '''
    return '1' or '0' corresponding to boolean not of next token
    Token represents True if it's '1' otherwise it's false
    '''
    try:
        vals = interpret(toks, 1,
                         lines, cur_line, out_lines, variables)
        return str(int(not vals[0] == '1'))
    except ParseError:
        raise
    except Exception:
        logger.exception("Parsing error")
        raise ParseError("Boolean \'not\' failed!")


def cmd_or(toks, lines, cur_line, out_lines, variables):
    '''
    return '1' or '0' corresponding to boolean and of next two tokens
    Token represents True if it's '1' otherwise it's false
    '''
    try:
        vals = interpret(toks, 2,
                         lines, cur_line, out_lines, variables)
        return str(int(vals[0] == '1' or vals[1] == '1'))
    except ParseError:
        raise
    except Exception:
        logger.exception("Parsing error")
        raise ParseError("Boolean \'or\' failed!")


def cmd_eqq(toks, lines, cur_line, out_lines, variables):
    '''
    return '1' or '0' corresponding to whether the following two tokens agree
    '''
    try:
        vals = interpret(toks, 2,
                         lines, cur_line, out_lines, variables)
        return str(int(vals[0] == vals[1]))
    except ParseError:
        raise
    except Exception:
        logger.exception("Parsing error")
        raise ParseError("\'==\' failed!")


def cmd_assert_regex(toks, lines, cur_line, out_lines, variables):
    '''
    return '1' if following line matches regex given in next token. else '0'
    '''
    regex = ''
    try:
        regex = interpret(toks, 1,
                          lines, cur_line, out_lines, variables)[0]
        return str(int(len(re.findall(regex, lines[cur_line+1])) > 0))
    except ParseError:
        raise
    except Exception:
        logger.exception("Parsing error")
        raise ParseError("Invalid/missing regex or missing line below!" +
                         " Regex = {}".format(regex))


def cmd_set_var(toks, lines, cur_line, out_lines, variables):
    '''
    <backslash>setvar <key> <value>
    Set or create new variable in the list and do not produce token
    '''
    try:
        key, val = interpret(toks, 2, lines, cur_line, out_lines, variables)
        assert_valid_varname(key)
        variables[key] = val
    except ParseError:
        raise
    except Exception:
        logger.exception("Parsing error")
        raise ParseError("Could not set variable!")

    return None


def cmd_the_out_line(toks, lines, cur_line, out_lines, variables):
    '''
    returns the current length of out_lines as a string
    '''
    return str(len(out_lines))


def cmd_echo_at(toks, lines, cur_line, out_lines, variables):
    '''
    <backslash>echo_at <insert_pos> <string>

    Add <string> to output at line index <insert_pos>
    '''
    try:
        at, string = interpret(toks, 2, lines, cur_line, out_lines, variables)
        out_lines.insert(int(at), string+"\n")
    except ParseError:
        raise
    except Exception:
        logger.exception("Parsing error")
        raise ParseError("Echo_at failed. Check line numbers are valid")
    return None


def cmd_repeat(toks, lines, cur_line, out_lines, variables):
    '''
    <backslash>r <num repeats> ...

    tokens following <num repeats> will be interpreted that number of times
    only those consumed by last repeat will be removed from toks

    returns from interpreting the 'repeated' tokens are ignored
    '''
    num = 0
    try:
        num = int(interpret(toks, 1, lines, cur_line, out_lines, variables)[0])
    except ParseError:
        raise
    except Exception:
        logger.exception("Parsing error")
        raise ParseError("Missing or invalid numerical argument for \\r")
    toks_bkp = toks
    for n in range(num):
        toks_bkp = toks[:]
        try:
            interpret(toks_bkp, 1, lines, cur_line, out_lines, variables)
        except IfStop:
            pass
    toks[:] = toks_bkp
    return None


def cmd_if(toks, lines, cur_line, out_lines, variables):
    '''
    Interpret next token, then attempt to interpret two more (or catch IfStops)
    If first token  == '1' then first of the two results (incl changes to
    arguments) is kept and otherwise the other

    if valid option returns a token, `\\ if` returns that token, otherwise None
    '''
    # true or false value
    tf = interpret(toks, 1, lines, cur_line, out_lines, variables)[0]
    # evaluate two tokens/catch IfStops instead
    ret = None

    # dummy variables for wrong branch
    lines_dmy = lines[:]
    out_lines_dmy = out_lines[:]
    variables_dmy = copy.deepcopy(variables)

    if tf == '1':
        try:
            ret = interpret(toks, 1, lines, cur_line, out_lines, variables)[0]
        except IfStop:
            pass
        try:
            interpret(toks, 1, lines_dmy, cur_line, out_lines_dmy,
                      variables_dmy)
        except IfStop:
            pass
    else:
        try:
            interpret(toks, 1, lines_dmy, cur_line, out_lines_dmy,
                      variables_dmy)
        except IfStop:
            pass
        try:
            ret = interpret(toks, 1, lines, cur_line, out_lines, variables)[0]
        except IfStop:
            pass
    return ret


def cmd_endif(toks, lines, cur_line, out_lines, variables):
    '''signify end of if/else block without returning token'''
    raise IfStop()


def assert_valid_varname(name):
    if "=" in name or len(name.split()) != 1:
        raise ParseError("\'{}\' is invalid variable name!".format(name))


# k for keep
#
command_list = {'k': cmd_echo_thisline, 'skip': cmd_delnxtline,
                'echo': cmd_echo, '+': cmd_concat,
                "&&": cmd_and, "||": cmd_or, "!!": cmd_not,
                "regex": cmd_assert_regex,
                '+f': cmd_addf, 'ftoi': cmd_ftoi,
                '#ol': cmd_the_out_line, 'echo@': cmd_echo_at,
                'r': cmd_repeat, 'set': cmd_set_var, 'if': cmd_if,
                'end': cmd_endif,
                '==': cmd_eqq}


def process_lines(lines, variables, comment_start='%#'):
    '''
    Process list of lines any starting with '%#' will be tokenized and
    interpreted using variable list given. Resulting output lines returned in
    a list lines is copied and not modified. values of variables may change

    Parameters
    ----------
    `lines` : list of strings to parse

    `variables` : Dictionary of variables accessible to the parser
    Returns

    `comment_start` : at the beginning of a line which indicates it should be
    parsed
    -------
    ret : Output lines
    '''

    # check for invalid variable names:
    for v in variables:
        assert_valid_varname(v)

    ret = []
    lines = lines[:]
    cur_line = 0
    while cur_line < len(lines):  # lines may change
        parsed = False
        line = lines[cur_line].strip()

        if line.startswith(comment_start):
            # strip comment string from line
            line = line[len(comment_start):]
            eq_at = line.find('=')
            if eq_at >= 0:
                try:
                    varname = line[:eq_at]
                    if varname in variables:
                        toks = makeTokens(line[eq_at+1:])
                        variables[varname] = interpret(toks, 1, lines,
                                                       cur_line, ret,
                                                       variables)[0]
                        parsed = True
                except Exception as e:
                    print("Failed to parse the following line:")
                    print(line)
                    print("Details: {}\n".format(e))

        if not parsed:
            ret.append(lines[cur_line])  # print original line
        cur_line = cur_line+1
    return ret


def process_file(input_path, output_path, variables, comment_start="%#"):
    '''
    Read whole file at input path, process all lines using variables and
    writh to output_path

    OSError may be raised y IO methods
    '''
    ilines = []
    with open(input_path, 'r') as ifile:
        ilines = ifile.readlines()
    with open(output_path, 'w') as ofile:
        ofile.writelines(process_lines(ilines, variables, comment_start))

###############################################################################


if __name__ == '__main__':
    '''print(process_markup_line("my line 1"))
    print(process_markup_line("my line%#ok#% 1"))
    print(process_markup_line("my %#ok#% line %#ok#% 1", {'ok':'okay'}))
    reqs = {'foo':''}
    print(process_markup_line("my %#foo#% line %#foo#% 1", {'ok':'okay'}))
    print(reqs)
    print(process_markup_line("my %#foo#% line %#foo = 1#% 1", {'ok':'okay'},
                              reqs))
    print(reqs)
    print(process_markup_line("my %#ok#% line %#foo = 1#% 1", {'ok':'okay'},
                              reqs))
    print(reqs)
    print(process_markup_line("my %#foo = 2#% line %#foo = haha#% 1",
                              {'ok':'okay'}, reqs, {'foo':'3'}))
    print(reqs)'''

    '''
    string = 'hello \\cmd \' lit\' \n bepp \'lit\\\\2\\2\\n\n\' \'lit3'
    while string:
        ret = nextToken(string)
        print(ret)
        string = ret[2]
    '''
    '''
    lines = ["", "line 1", "%#keep = \\k -1 'keep\\n this'", " %#echo =
             \\echo 2 \\+ 'hi' del 5",
           "%#del = \\skip echo !", "del0", "del1", "del2", "del3", "del4",
           "del5", "del6", "del7"
           , "%#and = \\&& and 1 f", "%#and = \\echo 1 \\!! and 0 f", "%#re =
           \\regex re",
           "\\usepackage[blahgrid, gridblah, grid, lo]{markpage}% grid"]
    #print(lines)
    varis = {'keep':'a', 'echo':7, 'del':'10', 'and':'1',
             're':'\\[.*\\bgrid\\b.*\\]'}
    print(process_lines(lines, varis))
    print(varis['re'])

    with open('junk.txt', 'w') as file:
        file.writelines(["\n", "a\n", "\n", "\\b"])
    '''
    var = {'_init': 0, '_#pages':'4','switch':'1',
           'count':'2', 'do':'', 'fruit':'mango', 'valid':'0'}
    process_file('junk_in.txt', 'junk_out.txt', var,'$$$')
    print(var)
