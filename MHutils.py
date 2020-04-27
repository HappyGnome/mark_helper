# -*- coding: utf-8 -*-
"""
Created on Wed Apr  1 10:20:52 2020

@author: Ben
"""
import os
import re

import hashlib


#read each file in the list "files" and return a hash of entire stream
#return hex digest of the hash
def hash_file_list(files, directory=''): 
    buf_size=2048#bytes
    the_hash=hashlib.sha256()
    for f in files:
        the_file=open(os.path.join(directory,f),"rb")
        while True:#until eof
            chunk=the_file.read(buf_size)
            if len(chunk)==0: break
            the_hash.update(chunk)            
        the_file.close()
    return the_hash.hexdigest()


'''
return [tok, toktype, newstring] where tok is a substring of string, or '' if nothing found

newstring is input string with tokens consumed

type in ['literal','command','other']
if literal: for substring 'a a\\' \\n' tok='a a\' \n'
if command: for substring '\mycmd', tok='cmd'
otherwise tok=substring

list of escaped characters in literal mode: 
    default:
        \\<char> -> <char>  e.g. for literal \' in string, ' is added to tok
    \\n -> \n
'''
def nextToken(string):
    #determine type:
    toks=string.split()
    toktype='other'
    continue_from=0#index of first character after parsed content
    try:
        if toks[0][0]=='\'':
            toktype='literal'
        elif toks[0][0]=='\\':
            toktype='command'
        continue_from=string.find(toks[0])+len(toks[0])
    except:
        return ['','other','']
    
    if toktype=='command':
        #strip leading slash and return
        return [toks[0][1:],'command',string[continue_from:]]
    elif toktype=='literal':
        lit_start=string.find('\'')+1#start of string
        str_build=''
        #find string end 
        escaped=False
        esc_repl={'n':'\n'}
        for i,c in enumerate(string[lit_start:]):
            if escaped:
                c=esc_repl.get(c,c)
                str_build=str_build+c#just c unless c in esc_repl
                escaped=False
            elif c=='\\':#escape next char
                escaped=True
            elif c=='\'':#unescaped ' => end of literal
                break
            else:
                str_build=str_build+c#just c unless c in esc_repl
        return [str_build,'literal',string[lit_start+i+1:]]
        
    else:#other
        return [toks[0],'other',string[continue_from:]]
    
'''
By repeatedly calling nextToken split string into list of tokens
return [[tok0, toktype0],...]
'''
def makeTokens(string):
    ret=[]
    while string:
        val=nextToken(string)
        string=val[2]
        ret.append(val[:2])
    return ret
'''
###############################################################################
command evaluation/distribution
'''

class ParseError(Exception):
    pass

'''
Given list of tokens [value, toktype](commands literals, other) try to return a 
list of n variables consisting of literals, results returned by
evaluated commands and substitutions for other tokens, starting t first token

returns up to n, but may be fewer if line ends beforehand

other arguments used by commands:
lines=list of lines (un parsed) in current file 
cur_line=index in lines of current line
out_lines=list of lines to be output by parsing current file

variables=dictionary of variables. commands are only processed if they
involve varaible names appearing here. Variables are also used to substitute
'other' type tokens

'''
def interpret(toks,n, lines, cur_line, out_lines, variables):
    ret=[]
    while len(ret)<n:
        val=''
        try:                        
            tok=toks.pop(0)
            val=tok[0]
        except: raise ParseError("Not enough tokens!")
        if tok[1]=='command':
            val=command_list[tok[0]](toks,
                       lines, cur_line, out_lines, variables)
        elif tok[1]=='literal':
            pass#default is to treat tok as literal
        else: #assume other and try substitution
            try:
                val=variables[tok[0]]
            except: pass
    
        ret.append(val)
    return ret
'''
###############################################################################
command handlers
'''
'''
command to add current line to output then return an evaluation of the rest of the toks

\k <num repeats>
'''
def cmd_echo_thisline(toks,
                       lines, cur_line, out_lines, variables):
    num=0
    try:
        num=int(interpret(toks,1,
                       lines, cur_line, out_lines, variables)[0])
    except:raise ParseError("Missing numerical argument for \\k")
    for n in range(num):
        out_lines.append(lines[cur_line][:])
    return interpret(toks,1,
                       lines, cur_line, out_lines, variables)[0]
    
'''
command remove next line from input and return following commands
\skip <num lines>
'''
def cmd_delnxtline(toks,
                       lines, cur_line, out_lines, variables):
    num=0
    try:
        num=int(interpret(toks,1,
                       lines, cur_line, out_lines, variables)[0])
    except:raise ParseError("Missing numerical argument for \\skip")
    try:
        for n in range(num):
            lines.pop(cur_line+1)
    except:pass
    return interpret(toks,1,
                       lines, cur_line, out_lines, variables)[0]
    
'''
command to add line to output and return evaluation of remaining
\echo <num repeats> <text>
'''
def cmd_echo(toks,lines, cur_line, out_lines, variables):
    num=0
    try:
        num=int(interpret(toks,1,
                       lines, cur_line, out_lines, variables)[0])
    except:raise ParseError("Missing numerical argument for \\echo")
    text=interpret(toks,1,
                       lines, cur_line, out_lines, variables)[0]
    for n in range(num):
        out_lines.append(text)
    return interpret(toks,1,
                       lines, cur_line, out_lines, variables)[0]
    
'''
command to concatenate two tokens
\+ <str1> <str2>
'''
def cmd_concat(toks,lines, cur_line, out_lines, variables):
    try:
        vals=interpret(toks,2,
                           lines, cur_line, out_lines, variables)
        return vals[0]+vals[1]
    except:
        raise ParseError("Concatenation failed!")

'''
return '1' or '0' corresponding to boolean and of next two tokens
Token represents True if it's '1' otherwise it's false
'''        
def cmd_and(toks,lines, cur_line, out_lines, variables):
    try:
        vals=interpret(toks,2,
                           lines, cur_line, out_lines, variables)
        return str(int(vals[0]=='1' and vals[1]=='1'))
    except:
        raise ParseError("Boolean \'and\' failed!")
        
'''
return '1' or '0' corresponding to boolean not of next token
Token represents True if it's '1' otherwise it's false
'''        
def cmd_not(toks,lines, cur_line, out_lines, variables):
    try:
        vals=interpret(toks,1,
                           lines, cur_line, out_lines, variables)
        return str(int(not vals[0]=='1' ))
    except:
        raise ParseError("Boolean \'not\' failed!")

'''
return '1' or '0' corresponding to boolean and of next two tokens
Token represents True if it's '1' otherwise it's false
'''        
def cmd_or(toks,lines, cur_line, out_lines, variables):
    try:
        vals=interpret(toks,2,
                           lines, cur_line, out_lines, variables)
        return str(int(vals[0]=='1' or vals[1]=='1'))
    except:
        raise ParseError("Boolean \'or\' failed!")
        
'''
return '1' if following line matches regex given in next token. else '0' 
'''
def cmd_assert_regex(toks,lines, cur_line, out_lines, variables):
    try:
        vals=interpret(toks,1,
                           lines, cur_line, out_lines, variables)
        return str(int(len(re.findall(vals[0],lines[cur_line+1]))>0))
    except:
        raise#debug
        #raise ParseError("Invalid/missing regex or missing line below!")
    
#k for keep
#
command_list={'k': cmd_echo_thisline, 'skip':cmd_delnxtline, 
              'echo':cmd_echo, '+':cmd_concat, 
              "&&":cmd_and, "||":cmd_or, "!!":cmd_not, "regex":cmd_assert_regex}

#process list of lines
#any starting with '%#' will be tokenized and interpreted using variable list given
#resulting output lines returned in a list
        #lines is copied and not modified. values of variables may change
def process_lines(lines, variables):
    ret=[]
    lines=lines[:]
    cur_line=0
    while cur_line<len(lines):#lines may change
        parsed=False
        l=lines[cur_line]
        try:
            if l.strip()[:2]=="%#":
                var_start=eq_at=l.find('#')+1
                eq_at=l.find('=')
                if eq_at>=0:
                    varname=l[var_start:eq_at]
                    if varname in variables:
                        toks=makeTokens(l[eq_at+1:])
                        variables[varname]=interpret(toks,1,lines,cur_line,ret,variables)[0]
                        parsed=True
        except Exception as e: 
            print("Failed to parse the following line:")
            print(l)
            print ("Details: {}".format(e))
            parsed=False
            
        if not parsed:
            ret.append(l)
        cur_line=cur_line+1
    return ret
'''
###############################################################################
'''
if __name__=='__main__':
    #print(hash_file_list(["HashTest/f1.txt","HashTest/f2.txt","HashTest/f3.txt"]))
    '''print(process_markup_line("my line 1"))
    print(process_markup_line("my line%#ok#% 1"))
    print(process_markup_line("my %#ok#% line %#ok#% 1",{'ok':'okay'}))
    reqs={'foo':''}
    print(process_markup_line("my %#foo#% line %#foo#% 1",{'ok':'okay'}))
    print(reqs)
    print(process_markup_line("my %#foo#% line %#foo=1#% 1",{'ok':'okay'},reqs))
    print(reqs)
    print(process_markup_line("my %#ok#% line %#foo=1#% 1",{'ok':'okay'},reqs))
    print(reqs)
    print(process_markup_line("my %#foo=2#% line %#foo=haha#% 1",{'ok':'okay'},reqs,{'foo':'3'}))
    print(reqs)'''
    
    '''
    string='hello \\cmd \' lit\' \n bepp \'lit\\\\2\\2\\n\n\' \'lit3'
    while string:
        ret=nextToken(string)
        print(ret)
        string=ret[2]
     '''
     
    lines=["","line 1", "%#keep= \k -1 'keep\\n this'", " %#echo= \echo 2 \+ 'hi' del 5",
           "%#del=\skip echo !","del0","del1","del2","del3","del4","del5","del6","del7"
           ,"%#and=\&& and 1 f","%#and=\echo 1 \!! and 0 f","%#re=\\regex re",
           "\\usepackage[blahgrid,gridblah,grid,lo]{markpage}% grid"]
    #print(lines)
    varis={'keep':'a','echo':7,'del':'10', 'and':'1','re':'\\[.*\\bgrid\\b.*\\]'}
    print(process_lines(lines,varis))
    print(varis['re'])
        

        
        
'''
###############################################################################
###############################################################################
JUNK
'''

#return line with substitutions made
#Commandsin the line  must be enclosed by %# and #%, if the content matches
    #key in sub then value of sub is substituted
    #if command is key=... and key is in vartoget then that vartoget[key] is set to 
    #what follows '='(before #%)
    #if key=... is used and key appears in vartoset, then
    #the command syntax is replaced in the output by a command %#key=vartoset[key]#%
    #setting commands  are stripped from the returned line
    #unmatched commands are left in the returned line
'''def process_markup_line(line, sub={}, vartoget={}, vartoset={}):
    ret=""#line returned
    consumed=0#first character in line not dealt with
    while consumed<len(line):
        spos=line[consumed:].find('%#')#start of command
        if spos<0:
            ret+=line[consumed:]
            break
        spos=spos+2+consumed#point to start of command
        epos=line[spos:].find('#%')
        if epos<0:
            ret+=line[consumed:]
            break
        epos=epos+spos  #next character position after command
        cmd=line[spos:epos]
        
        eqpos=cmd.find('=')#set or get command
        key=cmd[:eqpos]
        ret+=line[consumed:spos-2]#keep initial segment
        consumed=spos-2
        handled=False#command recognised and dealt with
        if eqpos<0 and cmd in sub:#substitution
            ret+=sub[cmd]
            handled=True
        else:           
            if key in vartoget:#extract value
                vartoget[key]=cmd[eqpos+1:]
                handled=True
            if key in vartoset:
                ret+="%#"+key+"="+vartoset[key]+"#%"
                handled=True
        if not handled:
                #default: leave everything
                ret+=line[consumed:epos+2]
        consumed=epos+2
    return ret'''