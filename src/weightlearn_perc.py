
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

# Usage: weightlearn.py [--preamble] [program files]

def main(options, args):
    features = {}
    ranker   = answerset_ranker_t(
        C=options.C,
        eta=options.eta,
        epsilon=options.epsilon,
        alg=options.algo)

    # Collect all possible features
    print >>sys.stderr, "Collecting feature information..."

    if None != options.preamble:
        _collectFeatures(features, options.preamble)

    for qid, fn in enumerate(args):
        _collectFeatures(features, fn)

    print >>sys.stderr, "Features:", " ".join(features.keys())

    ranker.set_features(features)

    # Start learning.
    try:
        xmRet = _learn(options, args, ranker)

    except KeyboardInterrupt:
        print >>sys.stderr, "Aborted."
    
    print etree.tostring(xmRet, pretty_print=True)


def _learn(options, args, ranker):
    xmRoot = etree.Element("root")

    xmParams = etree.Element("params", C=str(ranker.C), eta=str(ranker.eta), algo=ranker.updateAlg)
    xmRoot.append(xmParams)

    isConverged = False

    for i in xrange(options.iter*2):
        if i%2 == 0:
            print >>sys.stderr, "Iteration:", 1+i/2
            xmEpoch = etree.Element("epoch", id="%d" % (1+i/2))
            xmRoot.append(xmEpoch)

        acc         = 0
        stat        = [0]*5
        loss, times = [], []
        isUpdating  = i%2 == 1

        for j, fn in enumerate(args):
            if j%50 == 0: print >>sys.stderr, ".",

            aspfiles  = [fn] if options.preamble != None else [fn, options.preamble]
            goldAtoms = _readGoldAtoms(fn.replace(".pl", ".gold.interp"))

            if isUpdating:
                
                # Feed the example to the learner.
                ret, myloss, mydiff = ranker.feed(aspfiles, goldAtoms)

                if options.debug:
                    xmProblemwise = etree.Element("problemwise", loss="%.2f" % myloss)
                    xmEpoch.append(xmProblemwise)

                stat[ret] += 1
                loss += [myloss]

            else:
                # Just predict!
                times   += [ranker.lastInferenceTime]

                for pCurCost, pCurrent in ranker.predict(aspfiles):
                    if set(goldAtoms).issubset(set(pCurrent)):
                        acc += 1
                        break

        #
        # Write the current status.
        if isUpdating:

            # Write the current loss.
            xmLoss = _writeLoss(stat, loss)
            xmEpoch.append(xmLoss)
            
            print >>sys.stderr, "loss =", xmLoss.attrib["loss"]
            print >>sys.stderr, "Learning...",
            
            isConverged = ranker.fit()
            
            # Write the current vector.
            xmEpoch.append(_writeWeightVector(ranker.dv.inverse_transform(ranker.coef_)[0]))

            if isConverged:
                print >>sys.stderr, "Converged."
                break
                
            print >>sys.stderr, "Ok."
            
        else:

            # Write the current accuracy.
            xmAccuracy = _writePerformance(acc, len(args), times)
            xmEpoch.append(xmAccuracy)

            print >>sys.stderr, "acc. =", xmAccuracy.attrib["accuracy"]
                    
    return xmRoot


def _writeLoss(stat, loss):
    return etree.Element("loss",
                           no_lvc="%d" % stat[answerset_ranker_t.NO_LVC],
                           no_predictions="%d" % stat[answerset_ranker_t.CANNOT_PREDICT],
                           learnable="%d" % stat[answerset_ranker_t.UPDATED],
                           indistinguishable="%d" % stat[answerset_ranker_t.INDISTINGUISHABLE],
                           correct="%d" % stat[answerset_ranker_t.CORRECT],
                           loss="%.2f" % (sum(loss))
    )

def _writePerformance(acc, len_args, times):
    return etree.Element("performance",
                         accuracy="%.2f" % (100.0*acc/len_args),
                         correct="%d" % acc,
                         total="%d" % len_args,
                         time="%.2f" % (sum(times) / len(times)),
                     )

def _writeWeightVector(v):
    e = etree.Element("weight")
    e.text = str(v)
    return e
    
def _collectFeatures(outdict, fn):
    for ln in open(fn):
        m = re.search("\[f_(.*?)\([-0-9e.]+\)@", ln)

        if None != m:
            outdict[m.group(1)] = 0


def _readGoldAtoms(fn):
    return [x.strip() for x in open(fn)]


def _readWeight(fn):
    return eval(open(fn).read())

if "__main__" == __name__:
    cmdparser = optparse.OptionParser(description="Weight Learner for ASP.")
    cmdparser.add_option("--preamble", help="")
    cmdparser.add_option("--algo", default="batch", help="")
    cmdparser.add_option("--iter", type=int, default=5, help="The number of iterations.")
    cmdparser.add_option("--C", type=float, default=0.01)
    cmdparser.add_option("--eta", type=float, default=0.1)
    cmdparser.add_option("--epsilon", type=float, default=0.001, help="The number of iterations.")
    cmdparser.add_option("--debug", action="store_true")

    main(*cmdparser.parse_args())
