# -*- coding: utf-8 -*-
"""
Created on Tue May  5 09:16:34 2020

@author: Ben
"""

import random
import string
import os
import subprocess as sp

#Attempt to generate N random strings
def gen_filenames(N,strlen=8):
    ret=[]
    for n in range(N):
        name=''.join((random.choice(string.ascii_uppercase+string.digits) for j in range(strlen)))
        if not name in ret: ret.append(name)
    return ret
#15, 15, 15
questions={'1':{'a':2,'b':3,'c':5,'d':5},'2':{'a':8,'b':2,'c':5},'3':{'a':3,'b':3,'c':4,'d':5}}#{question_name:[part_max_marks]}
paper_width=21
paper_height=29.7
minmax_pages_per_q_part=[0.5,2]

stu_nums=gen_filenames(4)
prob_miss_part=0.1

#{stu_num:{q_name:mark}}
stu_marks={}

#get header for tex file
headerlines=[]
with open('dummy_header.txt','r') as f:
    headerlines=f.readlines()
    
def skip_pages(at,file):
    #file.write("\\begin{mpage}\n")
    for m in range(int(at)):
       file.write("\\end{mpage}\n\\begin{mpage}\n") 
       
    return at%1
#change coordinate systems and add margins at top/botom of page
def at2actual(at):
    return 0.95-at*0.9        
    
for s in stu_nums:
    stu_marks[s]={}
    filepath=os.path.join('DummyScripts',s+'.tex')
    with open(filepath,'w') as f:
        f.writelines(headerlines)
        at=0#position (as proportion of a page) in script file modulo 1 page
        
        
        f.write("\\begin{mpage}\n")
        for q in questions:
            mark=0#track mark as it's generated
            at+=0.1
            at=skip_pages(at,f)
            f.write("\\mnoth{{{}}}{{{}}} {{\\Large Question {}}}\n".format(0.2*paper_width,at2actual(at)*paper_height, q))
            for part in questions[q]:
                if random.random()>prob_miss_part:
                    at+=0.03
                    at=skip_pages(at,f)
                    f.write("\\mnoth{{{}}}{{{}}} {{({})}}\n".format(0.2*paper_width,at2actual(at)*paper_height, part))
                    at+=random.uniform(*minmax_pages_per_q_part)
                    at=skip_pages(at,f)
                    part_mark=int(random.random()*questions[q][part])
                    mark+=part_mark
                    f.write("\\mnoth{{{}}}{{{}}} {{...Work worth {} marks}}\n"\
                            .format(random.uniform(0.1*paper_width,0.8*paper_width),at2actual(at)*paper_height, part_mark))
            stu_marks[s][q]=mark
        f.write("\\end{mpage}\n\end{document}")
        
      
os.chdir("DummyScripts")
for s in stu_nums:#compile examples
    sp.run(["pdflatex",s+".tex","-aux-directory=./aux_files"])
os.chdir("..")                   
                    
                    

#save correct marks
with open('mark_check.csv','w') as f:
    f.write("Student #")
    for q in questions:
        f.write(",{}".format(q))
    for s in sorted(stu_marks):
        f.write("\n{}".format(s))
        for q in questions:
            f.write(",{}".format(stu_marks[s][q]))