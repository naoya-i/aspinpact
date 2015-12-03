
import os
import re
import sys
import csv
import optparse
import collections
import itertools
import multiprocessing

import numpy as np
import scipy.sparse as ss
import scipy.linalg as sl

from lxml import etree
from ranker import *
from extractBestAnswerSet import *

def main(options, args):
    myranker = answerset_ranker_t(
        rescaling=not options.no_rescaling,
        normalization=not options.no_normalization,
        C=options.C,
        eta=options.eta,
        epsilon=options.epsilon,
        pairwise=options.pairwise,
        alg=options.algo)

    # Collect all possible features
    print >>sys.stderr, "Collecting feature information..."

    if None != options.preamble:
        myranker.collectFeatures(options.preamble)

    for qid, fn in enumerate(args):
        myranker.collectFeatures(fn)

    print >>sys.stderr, "Features: %d features were detected." % len(myranker.features.keys())
    print >>sys.stderr, "Training examples: %d files." % len(args)

    myranker.setupFeatures()

    # Start learning.
    xmRoot = etree.Element("root")

    try:
        print >>sys.stderr, "Start learning process..."
        _learn(xmRoot, options, args, myranker)

    except KeyboardInterrupt:
        print >>sys.stderr, "Aborted."

    xmRoot.append(myranker.serialize())
    _output(options.output, xmRoot)


def _output(out, xmRoot):
    fsOut = sys.stdout

    if None != out:
        print >>sys.stderr, "Writing to %s..." % out
        fsOut = open(out, "w")

    print >>fsOut, etree.tostring(xmRoot, pretty_print=True)


def _parPredict(args):
    myranker, lp = args
    goldAtoms    = readGoldAtoms(lp.replace(".pl", ".gold.interp"))
    
    return myranker.poke([lp], goldAtoms)

    
def _learn(xmRoot, options, args, myranker):
    xmRoot.append(_writeParams(options))

    isConverged = False

    p = multiprocessing.Pool(options.parallel)
    
    for i in xrange(options.iter):
        print >>sys.stderr, "Epoch:", 1+i
        xmEpoch = etree.Element("epoch", id="%d" % (1+i))
        xmRoot.append(xmEpoch)

        stat        = [0]*5
        loss, times = [], []
        processed   = 0
        
        for fns in itertools.izip_longest(*[iter(args)]*options.chunk):
            print >>sys.stderr, "\r", "[%4d/%4d] Processing..." % (processed, len(args)),
            
            for status, myloss, examples in p.map(_parPredict, [(myranker, fn) for fn in fns if None != fn]):
                if options.debug:
                    xmProblemwise = etree.Element("problemwise",
                                                  statusCode="%d" % status,
                                                  loss="%.2f" % myloss,
                                                  filename=fn,
                    )

                    xmEpoch.append(xmProblemwise)

                stat[status] += 1
                loss += [myloss]

                for ex in examples:
                    myranker.feed(ex[0], ex[1])

            processed += options.chunk
                
        print >>sys.stderr, "Done."

        # Write the current loss.
        xmLoss = _writeLoss(stat, loss)
        xmEpoch.append(xmLoss)

        print >>sys.stderr, "loss =", xmLoss.attrib["loss"]
        print >>sys.stderr, "Fitting...",
        print >>sys.stderr, "# examples = %d (+:%d/-:%d)" % (
            len(myranker.trainingExamples),
            len(filter(lambda x: x==1, myranker.trainingLabels)),
            len(filter(lambda x: x==-1, myranker.trainingLabels)),
            )


        isConverged = myranker.fit()

        # Write the current vector.
        xmEpoch.append(_writeWeightVector(myranker.dv.inverse_transform(myranker.coef_)[0]))

        if isConverged:
            print >>sys.stderr, "Converged."
            break

        print >>sys.stderr, "Ok."
            

def _writeLoss(stat, loss):
    return etree.Element("loss",
                           no_lvc="%d" % stat[answerset_ranker_t.NO_LVC],
                           no_predictions="%d" % stat[answerset_ranker_t.CANNOT_PREDICT],
                           learnable="%d" % stat[answerset_ranker_t.UPDATED],
                           indistinguishable="%d" % stat[answerset_ranker_t.INDISTINGUISHABLE],
                           correct="%d" % stat[answerset_ranker_t.CORRECT],
                           loss="%.2f" % (sum(loss))
    )

    
def _writeWeightVector(v):
    e = etree.Element("weight")
    e.text = repr(v)
    return e

    
def _writeParams(options):
    xmParams     = etree.Element("params")
    dictoptions = sorted(vars(options).iteritems(), key=lambda x: x[0])

    for k, v in dictoptions:
        xmParams.attrib[k] = str(v)

    def _tostr(k, v):
        k = k.replace("_", "-")
        
        if isinstance(v, bool):
            if v:
                return "--%s" % k
            else:
                return ""

        if isinstance(v, int) or isinstance(v, float) or \
           (isinstance(v, str) and " " not in v):
            return "--%s %s" % (k, v)

        return "--%s '%s'" % (k, v)

    xmParams.text = " ".join([_tostr(k, v) for k, v in dictoptions])

    return xmParams

if "__main__" == __name__:
    cmdparser = optparse.OptionParser(description="Weight Learner for ASP.")
    cmdparser.add_option("--preamble", help="")
    cmdparser.add_option("--output", help="")
    cmdparser.add_option("--pairwise", action="store_true", help="")
    cmdparser.add_option("--algo", default="latperc", help="")
    cmdparser.add_option("--parallel", type=int, default=1, help="The number of parallel processes.")
    cmdparser.add_option("--chunk", type=int, default=50, help="Chunk size of parallel processing.")
    cmdparser.add_option("--iter", type=int, default=5, help="The number of iterations.")
    cmdparser.add_option("--C", type=float, default=0.01)
    cmdparser.add_option("--eta", type=float, default=0.1)
    cmdparser.add_option("--no-rescaling", action="store_true")
    cmdparser.add_option("--no-normalization", action="store_true")
    cmdparser.add_option("--epsilon", type=float, default=0.001, help="The number of iterations.")
    cmdparser.add_option("--debug", action="store_true")

    main(*cmdparser.parse_args())
