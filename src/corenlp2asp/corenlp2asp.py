
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
        pass


    def parse(self, fn):
        xml   = etree.parse(fn)
        atoms = []
        
        for sent in xml.xpath("/root/document/sentences/sentence"):
            ev  = evaluator.evaluator_t(sdreader.createDocFromLXML(sent))

            atoms += self.pl2pl(
                self.xml2pl(sent)
            )

        return self.evalXfs(atoms, ev)


    def evalXfs(self, pl, ev):
        
        def _eval(m):
            packed = ev
            return str(eval("packed._xf%s(%s)" % m.groups()))
        
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
