
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
        rescaling=not options.no_rescaling,
        normalization=not options.no_normalization,
        C=options.C,
        eta=options.eta,
        epsilon=options.epsilon,
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


def _learn(xmRoot, options, args, myranker):
    xmRoot.append(_writeParams(options))

    isConverged = False

    for i in xrange(options.iter*2):
        if i%2 == 0:
            print >>sys.stderr, "Iteration:", 1+i/2
            xmEpoch = etree.Element("epoch", id="%d" % (1+i/2))
            xmRoot.append(xmEpoch)

        ranked      = 0
        tie         = 0
        acc         = 0
        stat        = [0]*5
        loss, times = [], []
        isUpdating  = i%2 == 1

        if not isUpdating and not options.report_perf:
            continue

        for j, fn in enumerate(args):
            print >>sys.stderr, "\r", "[%4d/%4d] Processing %s..." % (1+j, len(args), fn),

            aspfiles  = [fn] if options.preamble != None else [fn, options.preamble]
            goldAtoms = readGoldAtoms(fn.replace(".pl", ".gold.interp"))

            if isUpdating:

                # Feed the example to the learner.
                ret, myloss = myranker.feed(aspfiles, goldAtoms)

                if options.debug:
                    xmProblemwise = etree.Element("problemwise",
                                                  statusCode="%d" % ret,
                                                  loss="%.2f" % myloss,
                                                  time="%.2f" % myranker.lastInferenceTime,
                                                  filename=fn,
                    )
                    xmEpoch.append(xmProblemwise)

                stat[ret] += 1
                loss += [myloss]

            else:
                # Just predict!
                correctPredictions = myranker.predict(aspfiles, goldAtoms, exclude=False)
                wrongPredictions = myranker.predict(aspfiles, goldAtoms, exclude=True)

                times += [myranker.lastInferenceTime]

                if 0 < len(correctPredictions) and 0 < len(wrongPredictions):
                    ranked += 1

                    if correctPredictions[0].score == wrongPredictions[0].score:
                        tie += 1

                    elif correctPredictions[0].score > wrongPredictions[0].score:
                        acc += 1

        print >>sys.stderr, "Done."

        #
        # Write the current status.
        if isUpdating:

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

        else:

            # Write the current accuracy.
            xmAccuracy = _writePerformance(acc, tie, ranked, len(args), times)
            xmEpoch.append(xmAccuracy)

            print >>sys.stderr, \
                "acc.  =", xmAccuracy.attrib["accuracy"], \
                "prec. =", xmAccuracy.attrib["prec"], \
                "tie   =", xmAccuracy.attrib["tie"], \
                "correct =", xmAccuracy.attrib["correct"], \
                "ranked =", xmAccuracy.attrib["ranked"]

            

def _writeLoss(stat, loss):
    return etree.Element("loss",
                           no_lvc="%d" % stat[answerset_ranker_t.NO_LVC],
                           no_predictions="%d" % stat[answerset_ranker_t.CANNOT_PREDICT],
                           learnable="%d" % stat[answerset_ranker_t.UPDATED],
                           indistinguishable="%d" % stat[answerset_ranker_t.INDISTINGUISHABLE],
                           correct="%d" % stat[answerset_ranker_t.CORRECT],
                           loss="%.2f" % (sum(loss))
    )

def _writePerformance(acc, tie, ranked, len_args, times):
    return etree.Element("performance",
                         accuracy="%.1f" % (100.0*acc/len_args),
                         prec="%.1f" % (100.0*acc/ranked),
                         correct="%d" % acc,
                         tie="%d" % tie,
                         ranked="%d" % ranked,
                         total="%d" % len_args,
                         time="%.2f" % (sum(times) / len(times)),
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
    cmdparser.add_option("--algo", default="latperc", help="")
    cmdparser.add_option("--iter", type=int, default=5, help="The number of iterations.")
    cmdparser.add_option("--C", type=float, default=0.01)
    cmdparser.add_option("--eta", type=float, default=0.1)
    cmdparser.add_option("--no-rescaling", action="store_true")
    cmdparser.add_option("--no-normalization", action="store_true")
    cmdparser.add_option("--report-perf", action="store_true")
    cmdparser.add_option("--epsilon", type=float, default=0.001, help="The number of iterations.")
    cmdparser.add_option("--debug", action="store_true")

    main(*cmdparser.parse_args())
