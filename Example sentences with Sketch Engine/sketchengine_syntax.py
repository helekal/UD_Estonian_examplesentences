# cleans corpus created from sentences from subcorpus wiki17 (Sketch Engine)

import argparse
import codecs
import csv
from estnltk import Text
import re
import pandas as pd

parser = argparse.ArgumentParser(description='Cleans the corpus, outputs syntactically analysed sentences.')
parser.add_argument('filename', type=str,
                     help="filename of your corpus")
parser.add_argument('--input-encoding',dest='input',type=str,default='utf8',
                     help="current encoding")
parser.add_argument('--output-encoding',dest='output',type=str,default='utf8',help='new encoding')
parser.add_argument('--unsuitable-words',dest='inappropriatewords',type=str,default='inappropriate_words.txt',help='list of unsuitable words')

args = parser.parse_args()

sentences = []

if args.input:
    with open(args.filename, 'r', encoding=args.input) as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            sentences.append(row)
        
unsuitable_words = []
with open(args.inappropriatewords,"r",encoding="utf8") as f:
    words = f.read()
    words = re.sub(r"\s+", "\n", words).split("\n")
    for word in words: # unsuitable words are added to list
        if not word.isdigit():
            unsuitable_words.append(word)
    
clean_sentences = [] # parts not needed are taken out
for sentence in sentences[4:]:
    clean_sentences.append(sentence[2])

analysed_sentences = []
for sentence in clean_sentences: 
    sentence_lemmas=[]
    text = Text(sentence)
    maltparser = text.tag_syntax() # syntactic analysis
    for info in maltparser['words']:
        sentence_lemmas.append(info['text'].lower())
        for i in info['analysis']:
            sentence_lemmas.append(i['lemma'])
    if not any(unsuitable in sentence_lemmas for unsuitable in unsuitable_words): # if sentence is suitable, syntactic analysis is added
        malt_info = list(zip(maltparser.word_texts, maltparser['conll_syntax']))
        for item in malt_info:
            info= item[0],item[1]['parser_out'][0][0]
            analysed_sentences.append(info)
        analysed_sentences.append("\n")   

with open('wiki17_corpus_malt.csv','w', encoding=args.output,newline='') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerows(analysed_sentences)