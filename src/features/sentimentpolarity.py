
import re
import sys
import os

import csv

class sentimentpolarity_t:
    def __init__(self, fn_wilson05=None, fn_sentiwordnet=None, fn_warriner13=None, fn_takamura05=None):
        if None != fn_wilson05: self._readW05(fn_wilson05)
        if None != fn_sentiwordnet: self._readSWN(fn_sentiwordnet)
        if None != fn_warriner13: self._readW13(fn_warriner13)
        if None != fn_takamura05: self._readT05(fn_takamura05)

        
    def _readSWN(self, fn):
        self.swn = {}

        for ln in open(fn):
            if ln.startswith("#"): continue

            entry = ln.strip().split("\t")

            if len(entry) != 6:
                continue
                
            pos, sid, spos, sneg, lemmas, gloss = entry

            for lemma in lemmas.split(" "):
                self.swn[lemma] = float(spos) - float(sneg)
            
        
    def _readW05(self, fn):
        self.wi05 = {}

        for ln in open(fn):
            ln = re.findall("word1=([^ ]+).*?priorpolarity=([^ ]+)\n", ln)

            if 0 < len(ln):
                if "positive" == ln[0][1]:
                    self.wi05[ln[0][0]] = 1
                    
                elif "negative" == ln[0][1]:
                    self.wi05[ln[0][0]] = -1
                    
                elif "neutral" == ln[0][1]:
                    self.wi05[ln[0][0]] = 0
                    


    def _readW13(self, fn):
        self.warriner = {}
        
        for row in csv.reader(open(fn)):
            if "V.Mean.Sum" == row[2]: continue
            
            self.warriner[row[1]] = float(row[2])

        _min = min(self.warriner.values())
        _max = max(self.warriner.values())

        def _norm(s):
            s = (s - _min)/(_max - _min)
            return (s-0.5)*2
            
        self.warriner = dict([(x, _norm(y)) for x, y in self.warriner.iteritems()])
        

    def _readT05(self, fn):
        self.takam = {}

        for ln in open(fn):
            word, pos, score = ln.strip().split(":")

            self.takam[word] = float(score)
            

    def getAvgPolarity(self, word):
        return (self.getPolarity(word, self.wi05, de=0.0) + \
            self.getPolarity(word+"#1", self.swn, de=0.0) + \
            self.getPolarity(word, self.warriner, de=0.0) + \
            self.getPolarity(word, self.takam, de=0.0)) / 4.0
        
            
    def getPolarity(self, word, dic, de=None):
        pol = dic.get(word)

        if None == pol:
            return de
        
        return pol

		
if "__main__" == __name__:
    sp = sentimentpolarity_t(
        fn_wilson05="/home/naoya-i/data/dict/subjclueslen1-HLTEMNLP05.tff",
        fn_sentiwordnet="/home/naoya-i/data/dict/SentiWordNet_3.0.0_20130122.txt",
        fn_warriner13="/home/naoya-i/data/dict/Ratings_Warriner_et_al.csv",
        fn_takamura05="/home/naoya-i/data/dict/pn_en.dic",
        )
    print "Wilson et al. 05:\t", sp.getPolarity(sys.argv[1], sp.wi05)
    print "SentiWordNet 3.0:\t", sp.getPolarity(sys.argv[1] + "#1", sp.swn)
    print "Warriner et al. 13:\t", sp.getPolarity(sys.argv[1], sp.warriner)
    print "Takamura et al. 05:\t", sp.getPolarity(sys.argv[1], sp.takam)
