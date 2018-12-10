"""Block MarkLevels for dividing sentences into classes depending on their syntactic complexity.

Usage:
udapy -s ud.MarkLevels < in.conllu > marked.conllu 2> log.txt

"""
import collections
import logging
import re
import estnltk
from estnltk import synthesize

from udapi.core.block import Block

unsuitable_words = [] # list of unsuitable words (black list)
with open("inappropriate_words.txt","r",encoding="utf8") as f:
    words = f.read()
    words = re.sub(r"\s+", "\n", words).split("\n")
    for word in words:
        if not word.isdigit():
            unsuitable_words.append(word)

unsuitable_advmods=[] # list of adverbials that won't be asked (such as "ka", "aga" etc)
with open("unsuitable_adverbials.txt","r",encoding="utf8") as f:
    adverbials = f.read().splitlines()
    for word in adverbials:
        unsuitable_advmods.append(word)       
        

class MarkLevels(Block):
    """Block for determing syntactic complexity  in UD v2."""
    def __init__(self, save_stats=True, tests=None, skip=None, **kwargs):
        """Create the MarkBugs block object.

        Args:
        save_stats: store the bug statistics overview into `document.misc["bugs"]`?
        tests: a regex of tests to include.
            If `not re.search(tests, short_msg)` the node is not reported.
            You can use e.g. `tests=aux-chain|cop-upos` to apply only those two tests.
            Default = None (or empty string or '.*') which all tests.
        skip: a regex of tests to exclude.
            If `re.search(skip, short_msg)` the node is not reported.
            You can use e.g. `skip=no-(VerbForm|NumType|PronType)`.
            This has higher priority than the `tests` regex.
            Default = None (or empty string) which means no skipping.
        """
        super().__init__(**kwargs)
        self.save_stats = save_stats
        self.stats = collections.Counter()
        self.tests_re = re.compile(tests) if (tests is not None and tests != '') else None
        self.skip_re = re.compile(skip) if (skip is not None and skip != '') else None
        

    def log(self, node, short_msg, long_msg):
        """Log node.address() + long_msg and add ToDo=short_msg to node.misc."""
        if self.tests_re is not None and not self.tests_re.search(short_msg):
            return
        if self.skip_re is not None and self.skip_re.search(short_msg):
            return
        logging.debug('node %s %s: %s', node.address(), short_msg, long_msg)
        if node.misc['Lvl']:
            if short_msg not in node.misc['Lvl']:
                node.misc['Lvl'] += ',' + short_msg
        else:
            node.misc['Lvl'] = short_msg
        self.stats[short_msg] += 1
        
    
    def process_node(self, node):
        form, udeprel, upos, feats, deprel = node.form, node.udeprel, node.upos, node.feats, node.deprel
        parent = node.parent
        r = node
        while r.deprel != "root":
            r = r.parent

        if r.misc['Lvl']!= "Not":
            if deprel=="root" :
                l =[n.deprel for n in node.descendants] 
                # Not - unsuitable sentences
                if len(node.descendants)<2:
                    self.log(node,"Not","too short")
                    return
                if l.count("punct") == 0: 
                    self.log(node,"Not","no puncuation marks")
                    return
                if l.count("parataxis") > 0 :
                    self.log(node,'Not','indirect or direct speech')
                    return
                if l.count("orphan") > 0 :
                    self.log(node,'Not','elliptical sentence')
                    return
                if  upos!= "VERB" and "AUX" not in [n.upos for n in node.children] : 
                    self.log(node,'Not','without verb')
                    return
                for l in [n.lemma for n in node.root.descendants]:
                    for i in unsuitable_words:
                        l=l.lower()
                        if "=" in l:
                            l=l.replace("=","")
                            if l == i:
                                self.log(node,'Not','includes an unsuitable word')
                                return
                        elif "_" in l:
                            l=l.replace("_","")
                            if l == i:
                                self.log(node,'Not','includes an unsuitable word')
                                return
                        else:
                            if l == i:
                                self.log(node,'Not','includes an unsuitable word')
                                return
                if [n.form for n in node.descendants].count("?") < 1 and [n.form for n in node.root.descendants].count(".") < 1 and [n.form for n in node.root.descendants].count("!") < 1: 
                    self.log(node,'Not','not a correct punctuation mark')
                    return
                sorted_nodes = sorted([node] + node.descendants, key=lambda n: n.ord) # words are sorted by their order in the sentence
                pattern="[A-ZÜÕÄÖ].*" # word starts with a capital letter
                if not re.search(pattern, sorted_nodes[0].form):
                    self.log(node,'Not','no capital letter at the beginning of the sentence')
                    return
                if sorted_nodes[0].xpos == "J": 
                    self.log(node,'Not','sentence starts with a conjunction')
                    return
                unsuitable=["(",")","[","]","{","}",":",";","-","/","\\"] # some unsuitable marks
                for m in unsuitable:
                    if m in [n.form for n in node.descendants]:
                        self.log(node,'Not','sentence includes unsuitable marks')
                        return
                # NotTrv - not trivial
                if [n.upos for n in node.descendants].count("VERB") > 1: 
                    self.log(node,'NotTrv','too many verbs')
                    return
                if [n.upos for n in node.descendants].count("AUX") > 1:
                    self.log(node,'NotTrv','too many auxiliaries')
                    return
                if [n.xpos for n in node.root.descendants].count("V") > 1 and ([n.upos for n in node.root.descendants].count("CCONJ") > 0 or [n.upos for n in node.root.descendants].count("SCONJ") > 0): # eg aux and verb together if there is a conjunction (cop sentences are still possible then)
                    self.log(node,'NotTrv','can be unsuitable for simple clause (aux and verb together)') # excludes eg "kingad on märjad ja jalad külmetavad" if simple clause is expected
                    return
                                   
            # part for excluding
            obl_case_not=[] 
            obl_wrong_case=[]
            obl_wrong_upos=[]
            nmod_amod_not=[]
            xpos_y_not=[]
            advmod_not=[]
            amod_not_8=[]
            nmod_not_8=[]
            acl_not_8=[]
            xcomp_not=[]
            obj_not=[]
            xcomp_sup_not=[]
            advmod_yes=[]
            xcomp_yes=[]
            xcomp_sup_yes=[]       
                   
            for c in node.root.descendants:
                # case and appos not allowed as governees of obl
                if c.deprel =="obl" and ("case" in [o.deprel for o in c.children] or "appos" in [o.deprel for o in c.children] or "det" in [o.deprel for o in c.children] or "conj" in [o.deprel for o in c.children]): 
                    obl_case_not.append("1")
                # such obl not allowed in sentences where adverbial is asked (eg Level 4)
                if c.deprel=="obl" and c.feats["Case"] in ["Nom","Gen","Par"]: 
                    obl_wrong_case.append("1")
                # such obl not allowed in sentences where adverbial is asked (eg Level 4)
                if c.deprel=="obl" and c.upos not in ["NOUN","PROPN"]: 
                    obl_wrong_upos.append("1")
                # such nmod not allowed in sentences where modifier is asked (eg Level 5)
                if c.deprel=="nmod" and (c.feats["Case"]!="Gen" or c.upos not in ["NOUN","PROPN"] or len([o.deprel for o in c.children])!=0): 
                    nmod_amod_not.append("1")
                # amod not allowed to have governees in sentences where modifier is asked (eg Level 5)
                if c.deprel=="amod" and len([o.deprel for o in c.children])!=0: 
                    nmod_amod_not.append("1")
                # Y as xpos not allowed as a word to be asked
                if c.xpos=="Y": 
                    xpos_y_not.append("1")
                # specific excludes for Level 8
                if c.deprel=="amod" and (c.feats["Case"]!="Gen" or len([o.deprel for o in c.children])!=0 or c.xpos=="Y"): 
                    amod_not_8.append("1")
                if c.deprel=="nmod" and (c.feats["Case"]!="Gen" or len([o.deprel for o in c.children])!=0 or c.upos not in ["NOUN","PROPN"] or c.xpos=="Y"): 
                    nmod_not_8.append("1")
                if c.deprel=="acl" and (c.upos not in ["ADJ"] or len([o.deprel for o in c.children])!=0):
                    acl_not_8.append("1")
                if c.deprel == "xcomp" and (c.upos not in ["ADJ","NOUN"] or len([o.deprel for o in c.children])!=0):
                    xcomp_not.append("1")
                # obj not allowed to have governees
                if c.deprel=="obj" and len([o.deprel for o in c.children])!=0:
                    obj_not.append("1")
                # abbreviations not allowed as obj
                if c.feats["Abbr"]=="Yes":
                    obj_not.append("1")
                # nummod is excluded
                if "nummod" in c.deprel:
                    obl_wrong_upos.append("1")
                # excluded in levels where other xcomps are expected (eg Level 7)
                if c.deprel=="xcomp" and c.feats["VerbForm"]!="Sup" :
                    xcomp_sup_not.append("1")
                # wrong or unsuitable advmods are excluded
                if c.deprel=="advmod" and (c.parent.upos != "VERB" or c.form.lower() in unsuitable_advmods or "case" in [o.deprel for o in c.children]): 
                    advmod_not.append("1")
                if c.deprel=="root" and c.upos=="ADV":
                    advmod_not.append("1")
                # following lines make ensure that such functions are present in a sentence
                if c.deprel=="advmod" and c.parent.upos in ["VERB"] and c.form.lower() not in unsuitable_advmods and "case" not in [o.deprel for o in c.children]:
                    advmod_yes.append("1")
                if c.deprel=="xcomp" and c.feats["VerbForm"]=="Sup" and len([o.deprel for o in c.children])==0:
                    xcomp_sup_yes.append("1")
                if c.deprel=="xcomp" and c.upos in ["ADJ","NOUN"] and len([o.deprel for o in c.children])==0:
                    xcomp_yes.append("1") 
                

            l = [n.deprel for n in node.root.descendants] 
            u = [n.upos for n in node.root.descendants] 
            chdeprels = [c.deprel for c in node.children]
            sibdeprels = [s.deprel for s in node.parent.children]
                        
            # LEVELS 1-6, max 5 words (simple clauses)
            # max 5 words, 1 verb (except verb+aux if no conjunction), flat and conj not allowed as governees, 1 punct.
            if len(node.root.descendants)<7 and r.misc['Lvl']!= "NotTrv" and "conj" not in chdeprels and "flat" not in chdeprels and "case" not in chdeprels and l.count("punct") == 1: 
                
                # LEVEL 1
                # 2 different subjects, 1 predicate
                # nsubj - nom (predicate has to be present in the sentence, but is not specified)
                if deprel == "nsubj" and upos in ["NOUN","PRON","PROPN","ADJ","NUM"] and feats["Case"]=="Nom" :
                    self.log(node, '1','subject and predicate in short simple clauses') # nsubj - Lvl 1
                    self.log(node, '13','subject and predicate in short simple clauses') 
                # nsubj:cop - nom, subject in a copular sentence (predicate has to be present in the sentence, but is not specified)
                if deprel == "nsubj:cop" and upos in ["NOUN","PRON","PROPN","ADJ","NUM"] and feats["Case"]=="Nom":
                    self.log(node, '1','subject and predicate in short simple clauses') # nsubj:cop - Lvl 1
                    self.log(node, '13','subject and predicate in short simple clauses') 
                # root - simple predicate (subject has to be present in the sentence, but is not specified)
                if deprel == "root" and upos == "VERB" and "aux" not in chdeprels and "compound:prt" not in chdeprels and ("nsubj" in chdeprels or "nsubj:cop" in chdeprels):
                    self.log(node, '1','subject and predicate in short simple clauses.') # root (verb) - Lvl 1
                    self.log(node, '13','subject and predicate in short simple clauses') 
                
                # LEVEL 2
                # 1 object
                # obj - par
                if deprel == "obj" and feats["Case"]=="Par" and "obj" in sibdeprels :
                    gen_nom=synthesize(node.lemma,"sg n") # based on lemma generates nom and gen forms
                    gen_gen=synthesize(node.lemma,"sg g")
                    case_par=[] 
                    for c in node.root.descendants: # excludes sentences where are other words beside object in partitive case
                        if c.feats["Case"]=="Par":
                            case_par.append(node)
                    if (node.form not in gen_nom or node.form not in gen_gen) and len(case_par)==1: # excludes sentences where are other words beside object in partitive case; the form of object has to be different in nom and gen 
                        self.log(node, '2','object (par) in short simple clauses') # obj - Lvl 2
                        self.log(node, '13','object (par) in short simple clauses')
                                
                # LEVEL 3
                # 1 object
                # obj - nom, gen
                if deprel == "obj" and "obj" in sibdeprels:
                    listike_nom=[] 
                    listike_gen=[]
                    for c in node.root.descendants: # excludes sentences where are other words in either nom or gen case
                        if c.feats["Case"]=="Nom":
                            listike_nom.append(node)
                        if c.feats["Case"]=="Gen":
                            listike_gen.append(node)
                    if len(listike_nom)==1 and feats["Case"] == "Nom": # only object in nom 
                        self.log(node, '3','object (nom, gen) in short simple clauses') # obj - Lvl 3
                        self.log(node, '13','object (nom, gen) in short simple clauses')
                    if len(listike_gen)==1 and feats["Case"]=="Gen": # only object in gen 
                        self.log(node, '3','object (nom, gen) in short simple clauses') # obj - Lvl 3
                        self.log(node, '13','object (nom, gen) in short simple clauses')
                
                # LEVEL 4
                # 1 adverbial  
                # obl - sentence cannot contain advmod, xcomp, nummod - otherwise those would be counted wrong in some cases in game - only obl is asked in lvl 4
                if deprel=="obl" and feats["Case"] not in ["Nom","Gen","Par"] and upos in ["NOUN","PROPN"] and len(obl_case_not)==0 and len(obl_wrong_case)==0 and len(obl_wrong_upos)==0 and "advmod" not in l and "xcomp" not in l and "nummod" not in l and len(advmod_not)==0:
                    self.log(node, '4','adverbial in short simple clauses') # obl - Lvl 4  
                    self.log(node, '13','adverbial in short simple clauses')                    
                    
                # LEVEL 5
                # 2 modifiers
                # nmod - gen
                if deprel=="nmod" and upos in ["NOUN","PROPN"] and feats["Case"]=="Gen" and len(chdeprels)==0 and "nummod" not in l and "acl" not in l and len(xpos_y_not)==0 and len(nmod_amod_not)==0 :
                    self.log(node, '5','nominal modifier (gen) in short simple clauses') # nmod - Lvl 5
                    self.log(node, '13','nominal modifier (gen) in short simple clauses')
                # amod - all cases
                if deprel=="amod" and upos in ["ADJ"] and len(chdeprels)==0 and "nummod" not in l and "acl" not in l and len(xpos_y_not)==0 and len(nmod_amod_not)==0:
                    self.log(node, '5','adjectival modifier in short simple clauses') # amod - Lvl 5
                    self.log(node, '13','adjectival modifier in short simple clauses')
                
                # LEVEL 6
                # 4 predicatives
                # governor of nsubj:cop-i - nom, par
                if deprel == "root" and upos in ["NOUN","ADJ"] and feats["Case"] in ["Nom","Par"] and "nsubj:cop" in chdeprels and l.count("nsubj:cop")==1 and l.count("csubj:cop")==0:
                    self.log(node, '6','predicative in short simple clauses') # root nom/par - Lvl 6
                    self.log(node, '13','predicative in short simple clauses')
                # governor of csubj:cop - nom, par
                if deprel=="root" and upos in ["NOUN","ADJ"] and feats["Case"] in ["Nom","Par"] and "csubj:cop" in chdeprels and l.count("csubj:cop")==1 and l.count("nsubj:cop")==0:
                    self.log(node, '6','predicative in short simple clauses') # root nom/par - Lvl 6
                    self.log(node, '13','predicative in short simple clauses')
                # governor of nsubj:cop - inf
                if deprel == "root" and upos in ["VERB"] and feats["VerbForm"] in ["Inf"] and "nsubj:cop" in chdeprels and l.count("nsubj:cop")==1 and l.count("csubj:cop")==0:
                    self.log(node, '6','predicative in short simple clauses') # root inf - Lvl 6
                    self.log(node, '13','predicative in short simple clauses')
                # governor of nsubj:cop - part
                if deprel == "root" and upos in ["VERB"] and feats["VerbForm"] in ["Part"] and "nsubj:cop" in chdeprels and l.count("nsubj:cop")==1 and l.count("csubj:cop")==0:
                    self.log(node, '6','predicative in short simple clauses') # root part - Lvl 6    
                    self.log(node, '13','predicative in short simple clauses')
                    
                    
            # LEVELS 7-10, max 10 words (simple clauses)
            # min 6 words, max 10 words, 1 verb (except verb+aux if no conjunction), flat, conj and case not allowed as governees, 1 punct.
            # in these levels deprel that is asked is in a certain form, but other deprels, that also are requested, can usually be in any form (just have to present)
            if len(node.root.descendants)>6 and len(node.root.descendants)<12 and r.misc['Lvl']!="NotTrv" and "conj" not in chdeprels and "flat" not in chdeprels and "case" not in chdeprels and l.count("punct") == 1:
                       
                # LEVEL 7
                # adverbial (+ subject, predicative) or adverbial (+ subject, object) - only adverbial is asked, others just have to be there
                # 7 adverbials
                # obl (+ nsubj, obj)
                if deprel == "obl" and upos in ["NOUN","PROPN"] and "nsubj" in l and "obj" in l and "nummod" not in l and len(obl_wrong_upos)==0 and len(advmod_not)==0 and len(obl_case_not)==0 and len(xcomp_not)==0:
                    self.log(node, '7','adverbial, subject and object in longer simple clauses') # obl - Lvl 7
                    self.log(node, '13','adverbial, subject and object in longer simple clauses') 
                # obl (+ predicative)
                if deprel == "obl" and upos in ["NOUN","PROPN"] and "nsubj:cop" in l and "nummod" not in l and len(obl_wrong_upos)==0 and len(advmod_not)==0 and len(obl_case_not)==0 and len(xcomp_not)==0:
                    self.log(node, '7','adverbial, subject and predicative in longer simple clauses') # obl - Lvl 7
                    self.log(node, '13','adverbial, subject and object in longer simple clauses') 
                # advmod (+ nsubj, obj)
                if deprel == "advmod" and node.parent.upos in ["VERB"] and "nsubj" in l and "obj" in l and "nummod" not in l and len(obl_wrong_upos)==0 and len(advmod_not)==0 and len(obl_case_not)==0 and len(xcomp_not)==0:
                    self.log(node, '7','adverbial, subject and object in longer simple clauses') # advmod - Lvl 7
                    self.log(node, '13','adverbial, subject and object in longer simple clauses')
                # advmod (+ predicative)
                if deprel == "advmod" and node.parent.deprel in ["root"] and "nsubj:cop" in l and "nummod" not in l and len(obl_wrong_upos)==0 and len(advmod_not)==0 and len(obl_case_not)==0 and len(xcomp_not)==0:
                    self.log(node, '7','adverbial, subject and predicative in longer simple clauses') # advmod - Lvl 7
                    self.log(node, '13','adverbial, subject and object in longer simple clauses')
                # xcomp (adj/noun) (+ nsubj, obj)
                if deprel == "xcomp" and upos in ["NOUN","ADJ"] and "nsubj" in l and "obj" in l and "nummod" not in l and len(obl_wrong_upos)==0 and len(advmod_not)==0 and len(obl_case_not)==0 and len(xcomp_not)==0:
                    self.log(node, '7','adverbial, subject and object in longer simple clauses') # xcomp (adj/noun) - Lvl 7
                    self.log(node, '13','adverbial, subject and object in longer simple clauses')
                # supine (xcomp verbform=sup) (+ nsubj, obj)
                if deprel == "xcomp" and feats["VerbForm"]=="Sup" and "nsubj" in l and "obj" in l and "nummod" not in l and len(obl_wrong_upos)==0 and len(advmod_not)==0 and len(obl_case_not)==0 and len(xcomp_sup_not)==0:
                    self.log(node, '7','adverbial, subject and object in longer simple clauses') # xcomp (sup) - Lvl 7
                    self.log(node, '13','adverbial, subject and object in longer simple clauses')
                # supine (xcomp verbform=sup) (+ predicative)
                if deprel == "xcomp" and feats["VerbForm"]=="Sup" and "nsubj:cop" in l and "nummod" not in l and len(obl_wrong_upos)==0 and len(advmod_not)==0 and len(obl_case_not)==0 and len(xcomp_sup_not)==0:
                    self.log(node, '7','adverbial, subject and predicative in longer simple clauses') # xcomp (sup) - Lvl 7
                    self.log(node, '13','adverbial, subject and object in longer simple clauses')                    
                                            
                
                # LEVEL 8
                # 3 modifiers and 2 adverbials
                # nmod - gen (+ adverbial)
                if deprel=="nmod" and len(amod_not_8)==0 and len(nmod_not_8)==0 and node.feats["Case"]=="Gen" and upos in ["NOUN","PROPN"] and node.xpos!="Y" and "obl" in l and l.count("punct") == 1 and "nummod" not in l and len(acl_not_8)==0:
                    self.log(node, '8','nominal modifier and adverbial in longer simple clauses') # nmod - Lvl 8
                    self.log(node, '13','nominal modifier and adverbial in longer simple clauses')
                # amod - gen (+ adverbial)
                if deprel=="amod" and len(amod_not_8)==0 and len(nmod_not_8)==0 and node.feats["Case"]=="Gen" and node.xpos!="Y" and "obl" in l and l.count("punct") == 1 and "nummod" not in l and len(acl_not_8)==0:
                    self.log(node, '8','adjectival modifier and adverbial in longer simple clauses') # amod - Lvl 8
                    self.log(node, '13','adjectival modifier and adverbial in longer simple clauses')
                # acl (+ adverbial)
                if deprel=="acl" and upos in ["ADJ"] and len(amod_not_8)==0 and len(nmod_not_8)==0 and len(acl_not_8)==0 and "obl" in l and l.count("punct") == 1 and "nummod" not in l and len(chdeprels)==0:
                    self.log(node, '8','modifier and adverbial in longer simple clauses') # acl - Lvl 8
                    self.log(node, '13','modifier and adverbial in longer simple clauses')
                # obl - nom, gen, par (+ modifier)
                if deprel=="obl" and feats["Case"] in ["Nom","Gen","Par"] and upos in ["NOUN","PROPN"] and ("nmod" in [obj.deprel for obj in node.root.descendants] or "amod" in [obj.deprel for obj in node.root.descendants] or "acl" in [obj.deprel for obj in node.root.descendants]) and l.count("punct") == 1 and "nummod" not in l and "advmod" not in l and len(xcomp_not)==0 and len(obl_case_not)==0 and len(obl_wrong_case)==0 and len(obl_wrong_upos)==0:
                    self.log(node, '8','modifier and adverbial in longer simple clauses') # obl - Lvl 8
                    self.log(node, '13','modifier and adverbial in longer simple clauses')
                # xcomp adj/noun (+ modifier)
                if deprel == "xcomp" and upos in ["NOUN","ADJ"] and ("nmod" in [obj.deprel for obj in node.root.descendants] or "amod" in [obj.deprel for obj in node.root.descendants] or "acl" in [obj.deprel for obj in node.root.descendants]) and l.count("punct") == 1 and "nummod" not in l and "advmod" not in l and len(xcomp_not)==0 and len(obl_case_not)==0 and len(obl_wrong_case)==0 and len(obl_wrong_upos)==0: 
                    self.log(node, '8','modifier and adverbial in longer simple clauses') # xcomp - Lvl 8
                    self.log(node, '13','modifier and adverbial in longer simple clauses')
    
    
                # LEVEL 9
                # 4 subjects and 1 object
                # nsubj - nom ja par (+ obj)
                if deprel == "nsubj" and upos in ["NOUN","PRON","PROPN","ADJ","NUM"] and feats["Case"] in ["Nom","Par"] and len(obj_not)==0 and l.count("nsubj")==1 and l.count("obj")==1 and "conj" not in chdeprels:
                    self.log(node, '9','subject and object in longer simple clauses') # nsubj - Lvl 9
                    self.log(node, '13','subject and object in longer simple clauses')
                # csubj - inf (+ obj)
                if deprel == "csubj" and feats["VerbForm"]=="Inf" and len(obj_not)==0 and l.count("csubj")==1 and l.count("obj")==1 and "conj" not in chdeprels:
                    self.log(node, '9','subject and object in longer simple clauses') # csubj - Lvl 9
                    self.log(node, '13','subject and object in longer simple clauses')
                # nsubj:cop - nom, par (+ obj)
                if deprel == "nsubj:cop" and upos in ["NOUN","PRON","PROPN","ADJ","NUM"] and feats["Case"] ==["Nom","Par"] and node.parent.feats["Case"]!="Nom" and len(obj_not)==0 and l.count("nsubj:cop")==1 and l.count("obj")==1 and "conj" not in chdeprels:
                    self.log(node, '9','subject and object in short simple clauses.') # nsubj:cop - Lvl 9
                    self.log(node, '13','subject and object in longer simple clauses')
                # csubj:cop - inf (+ obj)
                if deprel == "csubj:cop" and feats["VerbForm"]=="Inf" and node.parent.feats["Case"]!="Nom" and len(obj_not)==0 and l.count("csubj:cop")==1 and l.count("obj")==1 and "conj" not in chdeprels:
                    self.log(node, '9','subject and object in longer simple clauses.') # csubj:cop inf - Lvl 9
                    self.log(node, '13','subject and object in longer simple clauses')
                # obj otsing - nom, gen, par (+ nsubj)
                if deprel == "obj" and feats["Case"] in ["Nom","Gen","Par"] and "obj" in sibdeprels and ("csubj" in l or "nsubj" in l or "nsubj:cop" in l or "csubj:cop" in l) and len(obj_not)==0 and l.count("obj")==1:
                    self.log(node, '9','subject and object in longer simple clauses.') # obj - Lvl 9
                    self.log(node, '13','subject and object in longer simple clauses')
                    
                    
                # LEVEL 10
                # 4 subjects, 2 objects, 4 adverbials
                # nsubj - nom, par (+ obj, adverbial)
                if deprel == "nsubj" and upos in ["NOUN","PRON","PROPN","ADJ","NUM"] and feats["Case"] in ["Nom","Par"] and "conj" not in chdeprels and "obj" in l and ("obl" in l or len(xcomp_yes)>0 or len(xcomp_sup_yes)>0 or len(advmod_yes)>0):
                    self.log(node, '10','subject, object and adverbial in short simple clauses') # nsubj - Lvl 10
                    self.log(node, '13','subject, object and adverbial in short simple clauses')
                # csubj - inf (+ obj, adverbial)
                if deprel == "csubj" and feats["VerbForm"]=="Inf" and "obj" in l and ("obl" in l or len(xcomp_yes)>0 or len(xcomp_sup_yes)>0 or len(advmod_yes)>0) :
                    self.log(node, '10','subject, object and adverbial in longer simple clauses') # csubj - Lvl 10
                    self.log(node, '13','subject, object and adverbial in short simple clauses')
                # nsubj:cop - nom, par (+ obj, adverbial)
                if deprel == "nsubj:cop" and upos in ["NOUN","PRON","PROPN","ADJ","NUM"] and feats["Case"] ==["Nom","Par"] and node.parent.feats["Case"]!="Nom" and "obj" in l and ("obl" in l or len(xcomp_yes)>0 or len(xcomp_sup_yes)>0 or len(advmod_yes)>0) :
                    self.log(node, '10','subject, object and adverbial in longer simple clauses') # nsubj:cop - Lvl 10
                    self.log(node, '13','subject, object and adverbial in short simple clauses')
                # csubj:cop - inf (+ obj, adverbial)
                if deprel == "csubj:cop" and feats["VerbForm"]=="Inf" and l.count("csubj:cop") == 1 and "obj" in l and ("obl" in l or len(xcomp_yes)>0 or len(xcomp_sup_yes)>0 or len(advmod_yes)>0) :
                    self.log(node, '10','subject, object and adverbial in longer simple clauses') # csubj:cop inf - Lvl 10
                    self.log(node, '13','subject, object and adverbial in short simple clauses')
                # obj - nom, gen, par (+ subject, adverbial)
                if deprel == "obj" and [n.deprel for n in node.descendants].count("obj") < 2 and feats["Case"] in ["Nom","Gen","Par"] and "obj" in sibdeprels and ("csubj" in l or "nsubj" in l or "nsubj:cop" in l or "csubj:cop" in l) and ("obl" in l or len(xcomp_yes)>0 or len(xcomp_sup_yes)>0 or len(advmod_yes)>0) :
                    self.log(node, '10','subject, object and adverbial in longer simple clauses') # obj - Lvl 10
                    self.log(node, '13','subject, object and adverbial in short simple clauses')
                # obj - nom, gen, par (+ subject, adverbial)
                if deprel=="obj" and feats["Case"] in ["Nom","Gen","Par"] and node.parent.feats["VerbForm"]=="Conv" and ("csubj" in l or "nsubj" in l or "nsubj:cop" in l or "csubj:cop" in l) and [n.deprel for n in node.descendants].count("obj") < 2 and [n.deprel for n in node.descendants].count("ccomp") == 0 and ("obl" in l or len(xcomp_yes)>0 or len(xcomp_sup_yes)>0 or len(advmod_yes)>0) :
                    self.log(node, '10','subject, object and adverbial in longer simple clauses') # obj - Lvl 10
                    self.log(node, '13','subject, object and adverbial in short simple clauses')
                # obl (+ subject, object)
                if deprel=="obl" and upos in ["NOUN","PROPN"] and "obj" in l and ("csubj" in l or "nsubj" in l or "nsubj:cop" in l or "csubj:cop" in l ) and len(xcomp_not)==0 and len(advmod_not)==0 and len(obl_wrong_upos)==0 and len(obl_case_not)==0:
                    self.log(node, '10','subject, object and adverbial in longer simple clauses') # obl - Lvl 10
                    self.log(node, '13','subject, object and adverbial in short simple clauses')
                # advmod otsing  (+ subject, object)
                if deprel=="advmod" and node.parent.upos in ["VERB"] and len(advmod_not)==0 and len(xcomp_not)==0 and ("csubj" in l or "nsubj" in l or "nsubj:cop" in l or "csubj:cop" in l ) and "obj" in l and len(obl_wrong_upos)==0 and len(obl_case_not)==0:
                    self.log(node, '10','subject, object and adverbial in longer simple clauses') # advmod - Lvl 10
                    self.log(node, '13','subject, object and adverbial in short simple clauses')
                # xcomp adj/noun (+ subject, object)
                if deprel == "xcomp" and upos in ["NOUN","ADJ"] and len(xcomp_not)==0 and len(advmod_not)==0 and "obj" in l and ("csubj" in l or "nsubj" in l or "nsubj:cop" in l or "csubj:cop" in l) and len(obl_wrong_upos)==0 and len(obl_case_not)==0:
                    self.log(node, '10','subject, object and adverbial in longer simple clauses') # xcomp (adj/noun) - Lvl 10
                    self.log(node, '13','subject, object and adverbial in short simple clauses')
                # xcomp sup (+ subject, object)
                if deprel == "xcomp" and feats["VerbForm"]=="Sup" and len(xcomp_sup_not)==0 and len(advmod_not)==0 and "obj" in l and ("csubj" in l or "nsubj" in l or "nsubj:cop" in l or "csubj:cop" in l) and len(obl_wrong_upos)==0 and len(obl_case_not)==0:
                    self.log(node, '10','subject, object and adverbial in longer simple clauses') # xcomp (sup) - Lvl 10
                    self.log(node, '13','subject, object and adverbial in short simple clauses')
                    
                    
            # LEVELS 11-13, max 12 words (not only simple clauses)
            # max 12 words, 1 verb (except verb+aux if no conjunction), flat, conj and case not allowed as governees, 1 punct.
            # in these levels deprel that is asked is in a certain form, but other deprels, that also are requested, can usually be in any form (just have to present)  
            if len(node.root.descendants)<14 and r.misc['Lvl']!="NotTrv" and "conj" not in chdeprels and "flat" not in chdeprels and "case" not in chdeprels:
                    
                # LEVEL 11
                # 4 adverbials, 2 subjects, 4 predicatives
                # nsubj:cop (+ adverbial, predicative)
                if deprel == "nsubj:cop" and upos in ["NOUN","PRON","PROPN","ADJ","NUM"] and "nsubj" not in l and "csubj" not in l and "csubj:cop" not in l and [n.deprel for n in node.root.descendants].count("nsubj:cop") < 2 and ("obl" in l or len(xcomp_yes)>0 or len(xcomp_sup_yes)>0 or len(advmod_yes)>0) :
                    self.log(node, '11','subject, predicative, adverbial in even longer simple clauses') # nsubj:cop - Lvl 12
                    self.log(node, '13','subject, predicative, adverbial in even longer simple clauses')
                # csubj:cop (+ adverbial, predicative)
                if deprel == "csubj:cop" and feats["VerbForm"]=="Inf" and [n.deprel for n in node.root.descendants].count("csubj:cop") < 2 and "nsubj" not in l and "csubj" not in l and "nsubj:cop" not in l and ("obl" in l or len(xcomp_yes)>0 or len(xcomp_sup_yes)>0 or len(advmod_yes)>0) :
                    self.log(node, '11','subject, predicative, adverbial in even longer simple clauses') # csubj:cop - Lvl 12
                    self.log(node, '13','subject, predicative, adverbial in even longer simple clauses')
                # governor of nsubj:cop - nom, par (+ subject, adverbial)
                if deprel == "root" and upos in ["NOUN","ADJ"] and feats["Case"] in ["Nom","Par"] and "nsubj:cop" in chdeprels and ("obl" in l or len(xcomp_yes)>0 or len(xcomp_sup_yes)>0 or len(advmod_yes)>0) :
                    self.log(node, '11','subject, predicative, adverbial in even longer simple clauses') # root - Lvl 12
                    self.log(node, '13','subject, predicative, adverbial in even longer simple clauses')
                # governor of csubj:cop - nom, par (+ subject, adverbial)
                if deprel=="root" and upos in ["NOUN","ADJ"] and feats["Case"] in ["Nom","Par"] and "csubj:cop" in chdeprels and ("obl" in l or len(xcomp_yes)>0 or len(xcomp_sup_yes)>0 or len(advmod_yes)>0) :
                    self.log(node, '11','subject, predicative, adverbial in even longer simple clauses') # root - Lvl 11
                    self.log(node, '13','subject, predicative, adverbial in even longer simple clauses')
                # governor of nsubj:cop - inf (+ subject, adverbial)
                if deprel == "root" and upos in ["VERB"] and feats["VerbForm"] in ["Inf"] and "nsubj:cop" in chdeprels and ("obl" in l or len(xcomp_yes)>0 or len(xcomp_sup_yes)>0 or len(advmod_yes)>0):
                    self.log(node, '11','subject, predicative, adverbial in even longer simple clauses') # root - Lvl 11
                    self.log(node, '13','subject, predicative, adverbial in even longer simple clauses')
                # governor of nsubj:cop - part (+ subject, adverbial)
                if deprel == "root" and upos in ["VERB"] and feats["VerbForm"] in ["Part"] and "nsubj:cop" in chdeprels and ("obl" in l or len(xcomp_yes)>0 or len(xcomp_sup_yes)>0 or len(advmod_yes)>0) :
                    self.log(node, '11','subject, predicative, adverbial in even longer simple clauses') # root - Lvl 11  
                    self.log(node, '13','subject, predicative, adverbial in even longer simple clauses')                    
                # obl (+ subject, predicative)
                if deprel=="obl" and len(obl_case_not)==0 and upos in ["NOUN","PROPN"] and ("nsubj:cop" in l or "csubj:cop" in l) and len(xcomp_not)==0 and len(advmod_not)==0 and len(obl_wrong_upos)==0:
                    self.log(node, '11','subject, predicative, adverbial in even longer simple clauses') # obl - Lvl 11
                    self.log(node, '13','subject, predicative, adverbial in even longer simple clauses')
                # advmod (+ subject, predicative)
                if deprel=="advmod" and node.parent.upos in ["VERB"] and len(advmod_not)==0 and len(xcomp_not)==0 and ("csubj:cop" in l or "nsubj:cop" in l) and len(obl_case_not)==0 and len(obl_wrong_upos)==0:
                    self.log(node, '11','subject, predicative, adverbial in even longer simple clauses') # advmod - Lvl 11
                    self.log(node, '13','subject, predicative, adverbial in even longer simple clauses')
                # xcomp adj/noun (+ subject, predicative)
                if deprel == "xcomp" and upos in ["NOUN","ADJ"] and len(xcomp_not)==0 and len(advmod_not)==0 and len(obl_case_not)==0 and ("nsubj:cop" in l or "csubj:cop" in l) and len(obl_wrong_upos)==0:
                    self.log(node, '11','subject, predicative, adverbial in even longer simple clauses') # xcomp (adj/noun) - Lvl 11
                    self.log(node, '13','subject, predicative, adverbial in even longer simple clauses')
                # xcomp sup (+ subject, predicative)
                if deprel == "xcomp" and feats["VerbForm"]=="Sup" and len(xcomp_sup_not)==0 and len(advmod_not)==0 and len(obl_case_not)==0  and len(chdeprels)==0 and ("nsubj:cop" in l or "csubj:cop" in l) and len(obl_wrong_upos)==0:
                    self.log(node, '11','subject, predicative, adverbial in even longer simple clauses') # xcomp (sup) - Lvl 11
                    self.log(node, '13','subject, predicative, adverbial in even longer simple clauses')
                
                
                # LEVEL 12
                # vocative, subject, appos, modifier (subject and appos have to exist both if one of them is asked)
                # appos
                if deprel=="appos" and upos in ["NOUN","PROPN"] and ("nsubj" in l or "nsubj:cop" in l) and len(chdeprels)==0 and l.count("punct") == 1 and l.count("appos")==1:
                    self.log(node, '12','subject or vocative or appos in even longer simple clauses') # appos - Lvl 12
                    self.log(node, '13','subject or vocative or appos in even longer simple clauses')
                # vocative
                if deprel=="vocative" and l.count("punct") < 3 :
                    self.log(node, '12','subject or vocative or appos in even longer simple clauses') # voc - Lvl 12
                    self.log(node, '13','subject or vocative or appos in even longer simple clauses')
                # nsubj - nom, par
                if deprel=="nsubj" and upos in ["NOUN","PRON","PROPN","ADJ","NUM"] and feats["Case"] in ["Nom","Par"] and l.count("punct") == 1 and "appos" in l and "flat" not in chdeprels:
                    self.log(node, '12','subject or vocative or appos in even longer simple clauses') # nsubj - Lvl 12
                    self.log(node, '13','subject or vocative or appos in even longer simple clauses')
                # nsubj:cop - nom, par
                if deprel=="nsubj:cop" and upos in ["NOUN","PRON","PROPN","ADJ","NUM"] and feats["Case"] in ["Nom","Par"] and l.count("punct") == 1 and "appos" in l and "flat" not in chdeprels:
                    self.log(node, '12','subject or vocative or appos in even longer simple clauses') # nsubj:cop - Lvl 12
                    self.log(node, '13','subject or vocative or appos in even longer simple clauses')
                # csubj - inf
                if deprel == "csubj" and feats["VerbForm"]=="Inf" and l.count("punct") == 1 and "appos" in l and "flat" not in chdeprels:
                    self.log(node, '12','subject or vocative or appos in even longer simple clauses') # csubj - Lvl 12
                    self.log(node, '13','subject or vocative or appos in even longer simple clauses')
                # nmod - adverbial attribute (on the right from it's governor)
                if deprel=="nmod" and upos in ["NOUN","PROPN"] and feats["Case"]!="Gen" and len(chdeprels)==0 and node.xpos!="Y" and "amod" not in l and "nummod" not in l and "acl" not in l and l.count("nmod")==1 and "nmod" in [obj.deprel for obj in node.parent.children(following_only=True)]: # only 1 nmod allowed to ignore the possibility of letting wrong nmods in this level
                    self.log(node, '12','nominal modifier in longer simple clauses') # nmod - Lvl 7     
                    self.log(node, '13','nominal modifier in longer simple clauses') 
        
                      
                      
    """   
    def process_tree(self,tree):
        l =[n.deprel for n in tree.descendants]
        r=tree.root
        if l.count("punct") > 1:
            self.log(r,'Not','jama')    
    """    

    def after_process_document(self, document):
        total = 0
        message = 'ud.MarkLevels Overview:'
        for bug, count in sorted(self.stats.items(), key=lambda pair: (pair[1], pair[0])):
            total += count
            message += '\n%20s %10d' % (bug, count)
        message += '\n%20s %10d\n' % ('TOTAL', total)
        logging.warning(message)
        if self.save_stats:
            document.meta["bugs"] = message
        self.stats.clear()
