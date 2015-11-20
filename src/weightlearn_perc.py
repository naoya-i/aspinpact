
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
    ranker   = answerset_ranker_t(C=0.001, alg=options.algo)

    print >>sys.stderr, "Collecting feature information..."

    if None != options.preamble:
        _collectFeatures(features, options.preamble)

    for qid, fn in enumerate(args):
        _collectFeatures(features, fn)

    print >>sys.stderr, "Features:", " ".join(features.keys())

    ranker.set_features(features)

    xmRet = _learn(options, args, ranker)

    print etree.tostring(xmRet, pretty_print=True)


def _learn(options, args, ranker):
    xmRoot = etree.Element("root")

    try:
        for i in xrange(options.iter*2):
            if i%2 == 0:
                print >>sys.stderr, "Iteration:", 1+i/2
                xmEpoch = etree.Element("epoch", id="%d" % (1+i/2))
                xmRoot.append(xmEpoch)

            acc   = 0
            loss  = 0
            diff  = ss.dok_matrix(ranker.coef_.shape)
            times = []

            for j, fn in enumerate(args):
                if j%50 == 0: print >>sys.stderr, ".",

                aspfiles = [fn]

                if options.preamble != None:
                    aspfiles += [options.preamble]

                goldAtoms  = _readGoldAtoms(fn.replace(".pl", ".gold.interp"))

                # Sample k-best good/bad answer sets.
                if i%2 == 0:
                    myloss, mydiff = ranker.feed(aspfiles, goldAtoms)
                    loss += myloss

                    if myloss > 0.0: diff = diff + mydiff
                    
                else:
                    pCurCost, pCurrent = ranker.predict(aspfiles)
                    times   += [ranker.lastInferenceTime]
                    
                    if set(goldAtoms) & set(pCurrent) == set(goldAtoms):
                        acc += 1

            ranker.fit()
            
            if i%2 == 0:
                xmWeight = etree.Element("weight", loss="%.2f" % (loss/len(args)))
                xmEpoch.append(xmWeight)

                # Write the current vector.
                xmWeight.text = str(ranker.dv.inverse_transform(ranker.coef_)[0])

                print >>sys.stderr, xmWeight.attrib["loss"], diff

            else:

                # Write the current accuracy.
                xmAccuracy = etree.Element("performance", percentage="%.2f" % (100.0*acc/len(args)),
                correct="%d" % acc,
                total="%d" % len(args),
                time="%.2f" % (sum(times) / len(times)),
                )
                xmEpoch.append(xmAccuracy)

                print >>sys.stderr, xmAccuracy.attrib["percentage"]

    except KeyboardInterrupt:
        print >>sys.stderr, "Aborted."

    return xmRoot


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
    cmdparser.add_option("--epsilon", type=float, default=0.001, help="The number of iterations.")

    main(*cmdparser.parse_args())
