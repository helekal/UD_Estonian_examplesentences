"""Block MarkLevels for dividing sentences into classes depending on their syntactic complexity.

Usage:
udapy -s ud.MarkRootLevels < in.conllu > marked.conllu 2> log.txt

"""
import collections
import logging
import re

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

class MarkRootLevels(Block):
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
            
        
    # pylint: disable=too-many-branches, too-many-statements
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
                    
    def after_process_document(self, document):
        total = 0
        message = 'ud.MarkRootLevels Overview:'
        for bug, count in sorted(self.stats.items(), key=lambda pair: (pair[1], pair[0])):
            total += count
            message += '\n%20s %10d' % (bug, count)
        message += '\n%20s %10d\n' % ('TOTAL', total)
        logging.warning(message)
        if self.save_stats:
            document.meta["bugs"] = message
        self.stats.clear()
