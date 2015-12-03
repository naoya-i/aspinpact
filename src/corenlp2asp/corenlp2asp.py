
import sys
import collections
import math
import sdreader
import cStringIO
import subprocess
import re

import evaluator

from lxml import etree


def _sanitize(l):
    return l.replace(".", "_").replace("-", "_")


class parser_t:
    def __init__(self):
        self.ev = evaluator.evaluator_t()
        

    def parse(self, fn):
        xml   = etree.parse(fn)
        atoms = []
        
        for sent in xml.xpath("/root/document/sentences/sentence"):
            self.ev.setDoc(sdreader.createDocFromLXML(sent))

            atoms += self.evalXfs(
                self.pl2pl(
                    self.xml2pl(sent)
                ),
                self.ev
            )
        
        return self.embedStatistics("\n".join(atoms), self.ev)


    def embedStatistics(self, pl, ev):

        #
        # Embed all possible statistical features.
        regexFeature = re.compile("\[([-0-9])@.*?wf([A-Za-z_]+)(,?)(.*?)\]")
        
        pClingo = subprocess.Popen(
            ["/home/naoya-i/tmp/clingo-4.5.3-linux-x86_64/gringo",
             "--text",
             ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )
        pClingo.stdin.write(open("/home/naoya-i/work/clone/aspinpact/data/theory.pl").read())
        pClingo.stdin.write(pl)
        pClingo.stdin.close()

        out = cStringIO.StringIO()

        #
        # Produce original theory.
        for ln in open("/home/naoya-i/work/clone/aspinpact/data/theory.pl"):
            if None == regexFeature.search(ln):
                print >>out, ln.strip()

        #
        # Expand statistical features.
        def _eval(m):
            fv, fname, cm, fargs = m.groups()
            _fargs, feature_distinction = eval(fargs), ""
            
            if fargs.startswith("("):
                _fargs, feature_distinction = eval(fargs)[1:], "_" + "_".join([str(x) for x in eval(fargs)[0]])
            
            if hasattr(ev, "_wf%s" % fname):
                fv = getattr(ev, "_wf%s" % fname)(*_fargs)
            
            return "[f_%s%s(%s)@1,%s]" % (fname, feature_distinction, fv, ",".join(["\"%s\"" % x for x in _fargs]))
        
        for ln in pClingo.stdout:
            if ln.startswith(":~"):
                m = regexFeature.search(ln)

                if None != m:                        
                    print >>out, regexFeature.sub(_eval, ln.strip())

        # Add given program.
        print >>out, pl
        
        return out.getvalue()

        
    def evalXfs(self, pl, ev):
        
        def _eval(m):
            fname, fargs = m.groups()
            fargs        = fargs.strip("()")
            
            if hasattr(ev, "_xf%s" % fname):
                return getattr(ev, "_xf%s" % fname)(*[eval(a) for a in fargs.split(",")])
                
            return "%s_is_unknown_xf" % fname

            
        return [re.sub("xf([A-Za-z0-9_]+)\(([^)]+)\)",
                       _eval, a)
                for a in pl]
        

    def pl2pl(self, pl):

        #
        # Perform deduction.
        pClingo = subprocess.Popen(
            ["/home/naoya-i/tmp/clingo-4.5.3-linux-x86_64/clingo",
             "-n 0",
             "--opt-mode=enum",
             ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )
        pClingo.stdin.write(open("/home/naoya-i/work/clone/aspinpact/data/base.pl").read())
        pClingo.stdin.write(pl)
        pClingo.stdin.close()

        clingoret = pClingo.stdout.read()
        clingoerr = pClingo.stderr.read()

        m = re.search("Answer: 1\n(.*?)\n", clingoret)
        assert(None != m)
        
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
                
        return out.getvalue()


if "__main__" == __name__:
    main(sys.args)
