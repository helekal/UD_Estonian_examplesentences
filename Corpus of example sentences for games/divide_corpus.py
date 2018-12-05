"""
CoNLL-X and CoNLL-U file readers and writers
"""
__author__ = "Pierre Nugues"
# https://raw.githubusercontent.com/pnugues/ilppp/master/programs/labs/relation_extraction/python/conll.py
# code has been adapted to serve a different purpose
# python divide_corpus.py folder_name

import os
import re
from collections import defaultdict
import argparse
import codecs

parser = argparse.ArgumentParser(description='Divides sentences into different files based on their level tags.')
parser.add_argument('folder', type=str,
                     help="folder with tagged (levels) conllu-files")

args = parser.parse_args()

def get_files(dir):
    """
    Returns all the files in a folder ending with suffix
    Recursive version
    :param dir:
    :param suffix:
    :return: the list of file names
    """
    files = []
    for file in os.listdir(dir):
        path = dir + '/' + file
        if os.path.isdir(path):
            files += get_files(path)
        elif os.path.isfile(path):
            files.append(path)
    return files


def read_sentences(file):
    """
    Creates a list of sentences from the corpus
    Each sentence is a string
    :param file:
    :return:
    """
    with open (file, "r", encoding="utf8") as f:
        sentences=f.read().strip()
        sentences = sentences.split('\n\n')
        return sentences


def split_rows(sentences, column_names):
    """
    Creates a list of sentence where each sentence is a list of lines
    Each line is a dictionary of columns
    :param sentences:
    :param column_names:
    :return:
    """
    new_sentences = []
    texts=[]
    root_values = ['0', 'ROOT', 'ROOT', 'ROOT', 'ROOT', 'ROOT', '0', 'ROOT', '0', 'ROOT']
    start = [dict(zip(column_names, root_values))]
    for sentence in sentences:
        info=[]
        rows = sentence.split('\n')
        sentence = [dict(zip(column_names, row.split())) for row in rows if row[0] != '#']
        sentence = start + sentence
        new_sentences.append(sentence)
        if "newdoc id" in rows[0]: # beginnings of new docs
            info.append(rows[1])
            info.append(rows[2])
            texts.append(info)
        else:
            info.append(rows[0])
            info.append(rows[1])
            texts.append(info)
    return new_sentences, texts


def save(formatted_corpus, column_names, sent_id, text, key):
    for_check=[]
    for old_sentence,id,sent_text in zip(formatted_corpus,sent_id,text):
        sentence=[]
        if id not in for_check:
            for_check.append(id)
            f_out.write(id + '\n') # adds sentence id and plain sentence
            f_out.write(sent_text + '\n')
            for i in old_sentence:
                new_sentence = dict((k,v) for k,v in i.items())
                new_misc=re.sub("Lvl=([^|]*).*",r"\1",new_sentence["misc"])
                new_misc=new_misc.split(",") # [1,14]
                if len(new_misc)==1: # other level tags are removed
                    for number in new_misc:
                        if key==number:
                            new_sentence["misc"]="Lvl="+key
                            sentence.append(new_sentence)
                        else:
                            new_sentence["misc"]="_"
                            sentence.append(new_sentence)
                if len(new_misc)>1: # if one word has more than one level tag
                    info=[]
                    for number in new_misc:
                        if key==number:
                            info.append(number)
                        else:
                            continue
                    if len(info)==1:
                       new_sentence["misc"]="Lvl="+key
                       sentence.append(new_sentence)
                    else:
                        new_sentence["misc"]="_"
                        sentence.append(new_sentence)
            for row in sentence[1:]:
                for col in column_names[:-1]:
                    if col in row:
                        f_out.write(row[col] + '\t')
                    else:
                        f_out.write('_\t')
                col = column_names[-1]
                if col in row:
                    f_out.write(row[col] + '\n')
                else:
                    f_out.write('_\n')
            f_out.write('\n')
        else:
            pass


if __name__ == '__main__':

    divided_sentences=defaultdict(list)
    column_names_u = ['id', 'form', 'lemma', 'upostag', 'xpostag', 'feats', 'head', 'deprel', 'deps', 'misc']
    files = get_files(args.folder) # folder of all the files with level tags
    for file in files:
        sentences = read_sentences(file)
        formatted_corpus = split_rows(sentences, column_names_u)
        for sentence_list, info_list in zip(formatted_corpus[0],formatted_corpus[1]):
            for_check=[]
            for sentence_dict in sentence_list:
                for_check.append(sentence_dict["misc"])
            if "Lvl=NotTrv" in for_check or "Lvl=Not" in for_check or "Lvl=NotTrv|SpaceAfter=No" in for_check or "Lvl=Not|SpaceAfter=No" in for_check:
                continue
            for sentence_dict in sentence_list:
                new_misc=re.sub("Lvl=([^|]*).*",r"\1",sentence_dict["misc"])
                if "," not in new_misc:
                    if new_misc.isdigit():
                        add=sentence_list, info_list
                        divided_sentences[new_misc].append(add)
                else:
                    new_misc=new_misc.split(",")
                    for number in new_misc:
                        if number.isdigit():
                            add=sentence_list, info_list
                            divided_sentences[number].append(add)

    divided_sentences=dict(divided_sentences)
    #print(divided_sentences)
    for key, value in divided_sentences.items(): 
        sentences=[]
        id=[]
        text=[]
        for item in value:       
            sentences.append(item[0])
            id.append(item[1][0])
            text.append(item[1][1])
        
        with open("level_"+key+".conllu", 'w') as f_out:
            save(sentences,column_names_u, id, text, key)
