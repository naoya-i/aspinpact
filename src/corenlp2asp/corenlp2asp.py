
import sys
sys.path += ["/home/naoya-i/work/clone/aspinpact/src/"]

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
    def __init__(self):
        pass


    def parse(self, fn, fnGoldMention, f_pl2pl=True, f_evalxfs=True):
        xml   = etree.parse(fn)
        atoms = []

        for sent in xml.xpath("/root/document/sentences/sentence"):
            self.ev.setDoc(sdreader.createDocFromLXML(sent))

            pl = self.xml2pl(sent)

            if f_pl2pl: pl = self.pl2pl(pl)
            if f_evalxfs: pl = self.evalXfs(pl)

            atoms += pl

        return self.embedStatistics("\n".join(atoms), fnGoldMention)


    def embedStatistics(self, pl, fnGoldMention):

        fn_preamble = "/home/naoya-i/work/clone/aspinpact/data/theory.pl"

        #
        # Embed all possible statistical features.
        regexFeature = re.compile("\[([-0-9])@.*?wf([A-Za-z_]+)(.*?)\]")

        pClingo = subprocess.Popen(
            ["/home/naoya-i/tmp/clingo-4.5.3-linux-x86_64/gringo",
             "--text",
             ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )
        pClingo.stdin.write(open(fn_preamble).read())

        for ln in open(fnGoldMention):
            print >>pClingo.stdin, "gold(%s)." % ln.strip()

        pClingo.stdin.write(pl)
        pClingo.stdin.close()

        out = cStringIO.StringIO()

        #
        # Produce original theory.
        # for ln in open(fn_preamble):
        #     if None == regexFeature.search(ln):
        #         print >>out, ln.strip()

        # Add given program.
        print >>out, "%%%%%%%%%%%%%%%%%%%%%%"
        print >>out, "% Observations. "
        print >>out, pl

        #
        # Expand statistical features.
        print >>out, ""
        print >>out, "%%%%%%%%%%%%%%%%%%%%%%"
        print >>out, "% Expanded features."

        def _eval(m):
            fv, fname, fargs = m.groups()
            fargs1, fargs2   = _decomposeArgs(fargs)

            if hasattr(ev, "_wf%s" % fname):
                fv = getattr(ev, "_wf%s" % fname)(*(fargs1+fargs2))

            # fargs2 affects the feature name.
            if 0 < len(fargs):
                fname += "_" + "_".join(fargs2)

            return "[f_%s(%s)@1%s]" % (fname, fv, fargs)

        for ln in pClingo.stdout:
            if ln.startswith(":~"):
                m = regexFeature.search(ln)

                if None != m:
                    print >>out, regexFeature.sub(_eval, ln.strip())

        #
        # Write gold mentions.
        print >>out, ""
        print >>out, "%%%%%%%%%%%%%%%%%%%%%%"
        print >>out, "% Gold mentions."

        for ln in open(fnGoldMention):
            print >>out, "gold(%s)." % ln.strip()

        return out.getvalue()


    def evalXfs(self, pl, ):

        def _eval(fname, fargs):
            if hasattr(ev, "_xf%s" % fname):
                return getattr(ev, "_xf%s" % fname)(*[int(a) if re.match("[-0-9]+", a) else a.strip("\"") for a in fargs.split(",")])

            print >>sys.stderr, "Warning: Not implemented:", fname

            return "%s_is_unknown_xf" % fname


        # Ok, recursively replace the external functions.
        new_pl = []

        for a in pl:
            while True:
                toReplaces = re.findall("xf([A-Za-z0-9_]+)\(([^()]+)\)", a)

                if 0 == len(toReplaces): break

                for fname, fargs in toReplaces:
                    a = a.replace(
                        "xf%s(%s)" % (fname, fargs),
                        _eval(fname, fargs))

            new_a = a.rstrip(".") + "."

            if new_a == ".":
                continue

            new_pl += [new_a]

        return new_pl


    def pl2pl(self, pl):

        #
        # Perform deduction.
        pClingo = subprocess.Popen(
            ["/home/naoya-i/tmp/gringo-4.5.3-source/build/release/clingo",
             "-n 0",
             "--opt-mode=enum",
             ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )

        print >>pClingo.stdin, "#script (python)"
        print >>pClingo.stdin, "import sys; sys.path += [\"%s\"]" % "/home/naoya-i/work/clone/aspinpact/src"
        pClingo.stdin.write(open("/home/naoya-i/work/clone/aspinpact/src/corenlp2asp/evaluator.py").read())
        print >>pClingo.stdin, "#end."

        pClingo.stdin.write(open("/home/naoya-i/work/clone/aspinpact/data/base.pl").read())
        pClingo.stdin.write("\n".join(pl))
        pClingo.stdin.close()

        clingoret = pClingo.stdout.read()
        clingoerr = pClingo.stderr.read()

        m = re.search("Answer: 1\n(.*?)\n", clingoret)

        if None == m:
            print >>sys.stderr, clingoret, clingoerr
            raise Exception("Fatal error occurred in Clingo.")

        return [x + "." for x in m.group(1).split(" ")]


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
    with open(fn.replace(".txt.corenlp.xml", ".pl"), "w") as out:
        print >>out, g_parser.parse(fn, fnGoldMention = fn.replace(".txt.corenlp.xml", ".gold.mentions"))


def main(options, args):
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

    g_parser = parser_t()

    main(*cmdparser.parse_args())
