## Corpus of syntactically annotated example sentences divided into game levels
Corpus is designed especially for games teaching parts of the sentence where example sentences are needed. Corpus contains of 13 files in CoNLL-U-format. Filenames describe for what level the sentences in every file are meant for (eg level_1.conllu consists of sentences for level 1). Every game level has more than 200 sentences.

Every sentence has it's own ID (# sent_id). In all the sentence there is at least one Lvl-tag (eg Lvl=1). Words with such tags are suitable to be asked in a game. 

FOR EXAMPLE:
If Lvl=1 is tagged to a word with syntactic relation "nsubj" in a sentence, it means in that sentence a player has to either find a subject OR the word with Lvl-tag is brought out and the player is supposed to give a correct syntactic function for it.

Below are given parts of the sentence and their corresponding syntactic relations used in this version of corpus:

| Part of the sentence | Syntactic relation | 
| --- | --- | 
| Subject | nsubj; nsubj:cop; csubj; csubj:cop |
| Predicate | root (used in Level 1 and Level 13) |
| Object | obj |
| Predicative | governors of nsubj:cop and csubj:cop (used in Level 6, Level 11, Level 13) |
| Modifier | amod; nmod; acl (adj); appos (appositional modifier) |
| Adverbial | obl; advmod; xcomp (adj, sup, noun) |
| Direct address | vocative |


### How to run and compile a similar corpus?
File "marklevels.py" reads a file in CoNLL-U-format, adds information about levels (Lvl="level_number") or unsuitable sentences ("Not"/"NotTrv"). For running files "marklevels.py" and "markrootlevels.py" have to be in the same folder (udapi-python/udapi/block/ud). The location of files "inappropriate_words.txt" (list of inappropriate words) and "unsuitable_adverbs.txt" (list of unsuitable adverbs) depends on Python Path.

Python file "marklevels.py" is a command line program:  cat „INPUT_FILE“ | udapy -s ud.MarkRootLevels | udapy -s ud.MarkLevels > „OUTPUT_FILE“. 

Input file has to be a file in CoNLL-U-format (eg files of Universal Dependencies Treebank).

File "divide_corpus.py" removes from "marklevels.py" output file all the sentences with tags "Not" or "NotTrv" and divides sentences into different files according level tags. Every sentence can be in more than one file, if it had several level tags. 

Python file "divide_corpus.py" is a command line program, that takes a foldername (folder consisting only "marklevels.py" output file(s)) as a required argument.

Programs as Udapi, Python 3 and tool Estnltk 1.4 have to be installed.

### Syntactically annotated example sentences with Sketch Engine
Python file "sketchengine_syntax.py" cleans corpus downloaded from Sketch Engine subcorpus wiki17 and adds syntactic analysis. The output is a CSV-file where every word with it's syntactic function is on a separate line, between sentences there is a blank line. The quality of syntactic analysis was weak and thus the output was not used in the making of real corpus described below.

Python file "sketchengine_syntax.py" is a command line program, that takes a filename of downloaded Sketch Engine corpus as a required argument.
For running files "inappropriate_words.txt" (list of inappropriate words) has to be in the same folder with the program file.
