
import sys
sys.path += ["/home/naoya-i/work/clone/aspinpact/src/"]

import cPickle
import collections
import math
import sdreader
import cStringIO
import subprocess
import re

import multiprocessing
import optparse
import itertools

import evaluator

from lxml import etree


def _sanitize(l):
    return l.replace(".", "_").replace("-", "_")


def _decomposeArgs(a):
    r1, r2 = [], []
    r      = r1

    for x in a.strip(",").split(","):
        x = x.strip()

        if "i" == x:
            r = r2
            continue

        if re.match("[-0-9]+", x):
            r += [int(x)]

        else:
            r += [str(x.strip("\""))]

    return r1, r2


class parser_t:
    def __init__(self, verbose=False):
        self.ev = evaluator.evaluator_t()
        self.verbose = verbose


    def parse(self, fn, fnGoldMention, picklizeCache=True):
        xml   = etree.parse(fn)
        atoms = []

        for sent in xml.xpath("/root/document/sentences/sentence"):
            atoms += self.xml2pl(sent)

        atoms += self.gold2pl(fnGoldMention)
        cache  = self.cache(atoms)

        return "\n".join(atoms), cPickle.dumps(cache, protocol=1)


    def cache(self, pl):

        #
        # Ground them.
        pClingo = subprocess.Popen(
            ["/home/naoya-i/tmp/gringo-4.5.3-source/build/release/gringo",
             "-t",
             "-c mode=\"cache\"",
             ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )

        pClingo.stdin.write(open("/home/naoya-i/work/clone/aspinpact/src/corenlp2asp/grimod.py").read())
        pClingo.stdin.write(open("/home/naoya-i/work/clone/aspinpact/data/base.pl").read())
        pClingo.stdin.write("\n".join(pl))
        pClingo.stdin.close()

        #
        # Gringo returns a dictionary which represents "to be grounded" facts.
        clingoret = pClingo.stdout.read()
        clingoerr = pClingo.stderr.read()

        try:
            data      = re.findall("RESULT: (.*)", clingoret, flags=re.DOTALL)[0]

        except IndexError:
            print >>sys.stderr, clingoret
            print >>sys.stderr, clingoerr

            raise Exception("Oh, Gringo!")

        if self.verbose:
            print >>sys.stderr, clingoerr

        #
        # Calculate each value.
        cache = {}

        for f, args in cPickle.loads(data):
            val              = getattr(self.ev, f)(*args)
            cache[(f, args)] = val

            if self.verbose:
                print >>sys.stderr, "Cached:", f, args, "=", val

        return cache


    def gold2pl(self, fnGoldMention):
        out = cStringIO.StringIO()

        print >>out, "%%%%%%%%%%%%%%%%%%%%%%"
        print >>out, "% Gold mentions."

        for ln in open(fnGoldMention):
            print >>out, "gold(%s)." % ln.strip()

        return out.getvalue().split("\n")


    def xml2pl(self, sent):
        out = cStringIO.StringIO()

        print >>out, "%"
        print >>out, "% Input sentence:"
        print >>out, "%  ", " ".join(sent.xpath("tokens/token/word/text()"))
        print >>out, ""
        print >>out, "%"
        print >>out, "% Logical forms of sentence."

        #
        # Convert tokens.
        for tok in sent.xpath("./tokens/token"):
            tok = sdreader.createTokenFromLXML(tok)
            print >>out, "token(%s,\"%s\",\"%s\",\"%s\",\"%s\")." % (tok.id, tok.surf, tok.lemma, tok.pos, tok.ne)

        print >>out, ""

        #
        # Convert rels.
        for dep in sent.xpath("./dependencies[@type='collapsed-ccprocessed-dependencies']/dep"):
            dep = sdreader.createRelFromLXML(dep)

            print >>out, "dep(\"%s\",%s,%s)." % (dep.rel, dep.tk_from, dep.tk_to)

        return out.getvalue().split("\n")


def _convert(fn):
    with open(fn.replace(".txt.corenlp.xml", ".pl"), "w") as out_pl:
        with open(fn.replace(".txt.corenlp.xml", ".pl.pickle"), "w") as out_ch:
            pl, ch = g_parser.parse(fn, fnGoldMention = fn.replace(".txt.corenlp.xml", ".gold.mentions"))

            out_pl.write(pl)
            out_ch.write(ch)


g_parser = None

def main(options, args):
    global g_parser

    g_parser = parser_t(verbose=options.verbose)

    p = multiprocessing.Pool(options.parallel)
    processed = 0

    for fns in itertools.izip_longest(*[iter(args)]*options.chunk):
        print >>sys.stderr, "\r", "[%4d/%4d] Processing..." % (processed, len(args)),

        processed += options.chunk
        p.map(_convert, [fn for fn in fns if None != fn])

    print >>sys.stderr, "Done."


if "__main__" == __name__:
    cmdparser = optparse.OptionParser(description="Weight Learner for ASP.")
    cmdparser.add_option("--parallel", type=int, default=8, help="The number of parallel processes.")
    cmdparser.add_option("--chunk", type=int, default=50, help="Chunk size of parallel processing.")
    cmdparser.add_option("--verbose", action="store_true", default=False)

    main(*cmdparser.parse_args())
