
import os
import re
import sys
import csv
import optparse
import collections
import itertools

import numpy as np
import scipy.sparse as ss
import scipy.linalg as sl

from ranker import *
from extractBestAnswerSet import *

# Usage: weightlearn.py [--preamble] [program files]

def main(options, args):
    features = {}
    ranker   = answerset_ranker_t(C=0.001)

    print >>sys.stderr, "Collecting feature information..."

    if None != options.preamble:
        _collectFeatures(features, options.preamble)
        
    for qid, fn in enumerate(args):
        _collectFeatures(features, fn)

    print >>sys.stderr, "Features:", " ".join(features.keys())
    
    ranker.set_features(features)
    noUpdate = False
    
    for i in xrange(options.iter):
        print >>sys.stderr, "Iteration:", 1+i
        
        acc   = 0
        times = []
        
        for qid, fn in enumerate(args):
            aspfiles = [fn]

            if options.preamble != None:
                aspfiles += [options.preamble]
                
            goldAtoms  = _readGoldAtoms(fn.replace(".pl", ".gold.interp"))
            
            # Sample k-best good/bad answer sets.
            if noUpdate:
                pCurrent = ranker.predict(aspfiles)
                times   += [ranker.lastInferenceTime]
                
                if set(goldAtoms) & set(pCurrent) == set(goldAtoms):
                    acc += 1

            else:
                ranker.update(aspfiles, goldAtoms)
                

        if not noUpdate:            
            print ranker.coef_
            
        else:
            print >>sys.stderr, "Accuracy: %.2f (%d/%d)" % (100.0*acc/len(args), acc, len(args))
            print >>sys.stderr, "Time: %.2f" % (sum(times) / len(times))

        noUpdate = not noUpdate

            
def _collectFeatures(outdict, fn):
    for ln in open(fn):
        m = re.search("f_(.*?)\([-0-9e.]+\)@", ln)

        if None != m:
            outdict[m.group(1)] = 0
            
    
def _readGoldAtoms(fn):
    return [x.strip() for x in open(fn)]

    
def _readWeight(fn):
    return eval(open(fn).read())
    
if "__main__" == __name__:
    cmdparser = optparse.OptionParser(description="Weight Learner for ASP.")
    cmdparser.add_option("--preamble", help="")
    cmdparser.add_option("--iter", type=int, default=5, help="The number of iterations.")
    cmdparser.add_option("--epsilon", type=float, default=0.001, help="The number of iterations.")
    
    main(*cmdparser.parse_args())
