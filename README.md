## Corpus of syntactically annotated example sentences divided into game levels
Corpus is designed especially for games teaching parts of the sentence where example sentences are needed. Corpus contains of 13 files in CoNLL-U-format. Filenames describe for what level the sentences in every file are meant for (eg level_1.conllu consists of sentences for level 1). Every game level has more than 200 sentences.

Every sentence has it's own ID (# sent_id). In all the sentence there is at least one Lvl-tag (eg Lvl=1). Words with such tags are suitable to be asked in a game. 

FOR EXAMPLE:
If Lvl=1 is tagged to a word with syntactic relation "nsubj" in a sentence, it means in that sentence a player has to either find a subject OR the word with Lvl-tag is brought out and a player is supposed to give a correct syntactic function to it.

Below are given what parts of the sentences different syntactic relations used in corpus stand for:
Subject -> nsubj; nsubj:cop; csubj; csubj:cop
Predicate -> root (used in Level 1 and Level 13)
Object ->	obj
Predicative -> governors of nsubj:cop and csubj:cop (used in Level 6, Level 11, Level 13)
Modifier ->	amod; nmod; acl (adj); appos (appositional modifier)
Adverbial ->	obl; advmod; xcomp (adj, sup, noun)
Direct address ->	vocative


### How to run the programs that compile the corpus?
LISADA

### Syntactically annotated example sentences with Sketch Engine
LISADA
