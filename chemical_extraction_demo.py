# -*- coding: utf-8 -*-
import sys
import codecs
import operator
import itertools
from ddlite import *
from datasets import *
from utils import unescape_penn_treebank
from lexicons import RuleTokenizedDictionaryMatch

def rule_tokenizer(s):
    s = re.sub("([,?!:;] )",r" \1",s)
    s = re.sub("([.]$)",r" .",s)
    return s.split()

DICT_ROOT = "datasets/dictionaries/"
CORPUS_ROOT = "datasets/chemdner_corpus/"

parser = SentenceParser()
corpus = ChemdnerCorpus(CORPUS_ROOT, parser=parser, 
                        cache_path="/users/fries/desktop/cache/")

# ChemNDER has pre-defined cross-validation folds
dev_set = sorted(corpus.cv["training"].keys())
documents, gold_entities = zip(*[(corpus[pmid]["sentences"],corpus[pmid]["tags"]) for pmid in dev_set])

# summary statistics
gold_entity_n = len(list(itertools.chain.from_iterable(gold_entities)))
word_n = sum([len(sent.words) for sent in list(itertools.chain.from_iterable(documents))])
print("%d PubMed abstracts" % len(documents))
print("%d ChemNDER gold entities" % gold_entity_n)
print("%d tokens" % word_n)

print len(documents)
print len(gold_entities)
sys.exit()

for i,sentences in enumerate(documents):
    entities = gold_entities[i]
    
    for sent,labels in zip(sentences,entities):
        print " ".join(sent.words)
        print labels
        print
    print "---------"

sys.exit()



# ---------------------------------------------------------------------
#
# II. Build Matchers
#
# ---------------------------------------------------------------------
# dictionaries from tmChem & the UMLS

dict_fnames = ["%s/chemdner/mention_chemical.txt",
              "%s/chemdner/chebi.txt",
              "%s/chemdner/addition.txt",
              "%s/umls/substance-sab-all.txt",
              "%s/chemdner/train.chemdner.vocab.txt"]
dict_fnames = [s % DICT_ROOT for s in dict_fnames]

chemicals = []
for fname in dict_fnames:
    chemicals += [line.strip().split("\t")[0] for line in open(fname,"rU").readlines()]
chemicals = {term:1 for term in chemicals}

# create matchers and extract candidates
extr1 = DictionaryMatch('C', chemicals, ignore_case=True)
extr2 = RuleTokenizedDictionaryMatch('C', chemicals, ignore_case=True, tokenizer=rule_tokenizer)
extr3 = RegexMatch('C', "[αβΓγΔδεϝζηΘθικΛλμνΞξοΠπρΣστυΦφχΨψΩω]+[-]+[A-Za-z]+", ignore_case=True)
extr4 = RegexMatch('C', "([-]*(\d[,]*)+[-])", ignore_case=True)
extr5 = RegexMatch('C', "([-]*(\d[,]*)+[-])", ignore_case=True)
matcher = MultiMatcher(extr1,extr2,extr3,extr4,extr5)

# ---------------------------------------------------------------------
#
# III. Extract Candidates
#
# ---------------------------------------------------------------------
candidates = Entities(sentences, matcher)


'''
# Crude recall estimate (ignores actual span match and tokenization problems)
mentions = [" ".join(unescape_penn_treebank([e.words[i] for i in e.idxs])) for e in candidates]
gold_mentions = list(zip(*itertools.chain.from_iterable(gold_entities))[0])

for m in mentions:
    if m in gold_mentions:
        gold_mentions.remove(m)
tp = gold_entity_n - len(gold_mentions)

print("Found %d candidate entities" % len(candidates))
print("Candidates: %.2f%% of all tokens" % (len(candidates)/float(word_n) * 100) )
print("Annotations %.2f%% of all tokens" % (gold_entity_n/float(word_n) * 100) )
print("~recall: %.2f (%d/%d)" % (float(tp) / gold_entity_n, tp, gold_entity_n))

#candidates.dump_candidates("cache/candidates.pkl")
'''
sys.exit()

# ---------------------------------------------------------------------
#
# IV. Error Analysis
#
# ---------------------------------------------------------------------

# What are we missing due to tokenization errors?
regexes = [re.compile("[αβΓγΔδεϝζηΘθικΛλμνΞξοΠπρΣστυΦφχΨψΩω]+[-]+[A-Za-z]+")]
regexes += [re.compile("([-]*(\d[,]*)+[-])")]

def regex_match(t):
    for regex in regexes:
        if regex.search(t):
            return True
    return False

tokenization_errors = [term for term in gold_mentions if term in chemicals or regex_match(term)]
tokenization_errors = {term:tokenization_errors.count(term) for term in tokenization_errors}
oov_errors = [term for term in gold_mentions if term not in tokenization_errors]
oov_errors = {term:oov_errors.count(term) for term in oov_errors}

print("Tokenization Errors: %d" % (sum(tokenization_errors.values())))
print("Out-of-vocabulary Errors: %d" % (sum(oov_errors.values())))

for term in sorted(oov_errors.items(),key=operator.itemgetter(1),reverse=1):
    print("%s: %d" % (term[0], oov_errors[term[0]]))
