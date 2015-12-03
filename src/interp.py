
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

    return xmRoot


def _parPredict(args):
    myranker, lp = args
    goldAtoms    = readGoldAtoms(lp.replace(".pl", ".gold.interp"))
    a            = myranker.predict([lp], eco=True)
    
    return lp, myranker.lastInferenceTime, goldAtoms, a
    

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
    processed = 0

    p = multiprocessing.Pool(options.parallel)
    
    for fns in itertools.izip_longest(*[iter(args)]*options.chunk):
        print >>sys.stderr, "\r", "[%4d/%4d] Processing..." % (processed, len(args)),

        processed += options.chunk
        
        for fn, tim, goldAtoms, ret in p.map(_parPredict, [(myranker, fn) for fn in fns if None != fn]):
            xmPredict = etree.Element("predict",
                                      filename=fn,
                                      time="%.2f" % tim,
                                      goldAtoms=" ".join(goldAtoms),
                                      numAnswers="%d" % len(ret),
                                      result="0",
                                      score="0",
            )
            xmRoot.append(xmPredict)

            times += [tim]
            
            xmASS = etree.Element("answersets")
            xmPredict.append(xmASS)

            if 0 < len(ret):
                numCorrect, numWrong = 0, 0
                xmPredict.attrib["score"] = "%f" % ret[0].score

                for a in ret:
                    xmResult = etree.Element("answerset",
                                             score="%f" % a.score,
                                             result="0",
                    )
                    xmResult.text = "\n".join(a.answerset)
                    xmASS.append(xmResult)

                    if set(goldAtoms).issubset(set(a.answerset)):
                        numCorrect += 1
                    else:
                        numWrong += 1

                if numCorrect > 0 and numWrong == 0:
                    xmResult.attrib["result"] = "1"
                    xmPredict.attrib["result"] = "1"
                    acc += 1

                elif numCorrect == 0 and numWrong > 0:
                    xmResult.attrib["result"] = "-1"
                    xmPredict.attrib["result"] = "-1"

                if numCorrect == 0 or numWrong == 0:
                    ranked += 1


    print >>sys.stderr, "Done."

    # Write the current accuracy.
    xmAccuracy = _writePerformance(acc, ranked, len(args), times)
    xmRoot.append(xmAccuracy)

    print >>sys.stderr, \
        "acc.  = %s (%s/%s)" % (xmAccuracy.attrib["accuracy"], xmAccuracy.attrib["correct"], xmAccuracy.attrib["total"]), \
        "prec. = %s (%s/%s)" % (xmAccuracy.attrib["prec"], xmAccuracy.attrib["correct"], xmAccuracy.attrib["ranked"]), \
        "no dec. = %s" % (xmAccuracy.attrib["no_dec"])

def _writePerformance(acc, ranked, len_args, times):
    return etree.Element("performance",
                         accuracy="%.1f" % (100.0*acc/len_args),
                         prec="%.1f" % (100.0*acc/ranked),
                         correct="%d" % acc,
                         wrong="%d" % (ranked - acc),
                         no_dec="%d" % (len_args - ranked),
                         ranked="%d" % ranked,
                         total="%d" % len_args,
                         time="%.2f" % (sum(times) / len(times)),
                     )


if "__main__" == __name__:
    cmdparser = optparse.OptionParser(description="INPACT interpreter.")
    cmdparser.add_option("--preamble", help="")
    cmdparser.add_option("--parallel", type=int, default=1, help="The number of parallel processes.")
    cmdparser.add_option("--chunk", type=int, default=50, help="Chunk size of parallel processing.")
    cmdparser.add_option("--model", help="")
    cmdparser.add_option("--use-epoch", type=int, default=-1, help="")
    cmdparser.add_option("--output", help="")
    cmdparser.add_option("--debug", action="store_true")

    main(*cmdparser.parse_args())
