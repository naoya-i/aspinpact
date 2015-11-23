
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

from lxml import etree
from ranker import *
from extractBestAnswerSet import *

def main(options, args):
    myranker = answerset_ranker_t(
        rescaling=True,
        normalization=True,
        )

    print >>sys.stderr, "Loading %s..." % options.model
    myranker.load(options.model, options.use_epoch)

    print >>sys.stderr, "%d weights are loaded." % len(myranker.features.keys())
    
    # Intepret the input.
    xmRoot = etree.Element("root")
    xmBasic = etree.Element("settings", model=options.model)
    xmRoot.append(xmBasic)
    
    try:
        _interpret(xmRoot, options, args, myranker)

    except KeyboardInterrupt:
        print >>sys.stderr, "Aborted."

    _output(options.output, xmRoot)

    
def _output(out, xmRoot):
    fsOut = sys.stdout

    if None != out:
        print >>sys.stderr, "Writing to %s..." % out
        fsOut = open(out, "w")
        
    print >>fsOut, etree.tostring(xmRoot, pretty_print=True)
    
    
def _interpret(xmRoot, options, args, myranker):
    ranked = 0
    acc    = 0
    times  = []

    for j, fn in enumerate(args):
        if j%50 == 0: print >>sys.stderr, ".",

        aspfiles  = [fn] if options.preamble != None else [fn, options.preamble]
        goldAtoms = readGoldAtoms(fn.replace(".pl", ".gold.interp"))

        # Just predict!
        ret = myranker.predict(aspfiles, eco=True)
        times += [myranker.lastInferenceTime]

        xmPredict = etree.Element("predict",
                                  time="%.2f" % myranker.lastInferenceTime,
                                  goldAtoms=" ".join(goldAtoms),
                                  numAnswers="%d" % len(ret),
        )
        xmRoot.append(xmPredict)

        xmASS = etree.Element("answersets")
        xmRoot.append(xmASS)
        
        if 0 < len(ret):
            ranked += 1
            numCorrect = 0
            
            for a in ret:
                xmResult = etree.Element("answerset",
                                         score="%f" % a.score,
                                         result="0",
                )
                xmResult.text = "\n".join(a.answerset)
                xmASS.append(xmResult)

                if set(goldAtoms).issubset(set(a.answerset)):
                    xmResult.attrib["result"] = "1"
                    numCorrect += 1
                    
            acc += min(1, numCorrect)

            
    # Write the current accuracy.
    xmAccuracy = _writePerformance(acc, ranked, len(args), times)
    xmRoot.append(xmAccuracy)

    print >>sys.stderr, \
        "acc.  =", xmAccuracy.attrib["accuracy"], \
        "prec. =", xmAccuracy.attrib["prec"]

    
def _writePerformance(acc, ranked, len_args, times):
    return etree.Element("performance",
                         accuracy="%.1f" % (100.0*acc/len_args),
                         prec="%.1f" % (100.0*acc/ranked),
                         correct="%d" % acc,
                         total="%d" % len_args,
                         ranked="%d" % ranked,
                         time="%.2f" % (sum(times) / len(times)),
                     )

    
if "__main__" == __name__:
    cmdparser = optparse.OptionParser(description="INPACT interpreter.")
    cmdparser.add_option("--preamble", help="")
    cmdparser.add_option("--model", help="")
    cmdparser.add_option("--use-epoch", type=int, default=-1, help="")
    cmdparser.add_option("--output", help="")
    cmdparser.add_option("--debug", action="store_true")

    main(*cmdparser.parse_args())
