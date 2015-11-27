
import sys
import collections
import math

from lxml import etree
from nltk.corpus import wordnet as wn

import nltk

sys.path += ["/home/naoya-i/work/clone/wsc/src"]
import selpref
import ncnaive
import googlengram


def _getNumber(l):
    return "plural" if l in ["we", "they", "these", "those"] else "singular"

def _getGender(l):
    if l == "he":  return "male"
    if l == "she": return "female"
    if l == "it": return "thing"

    return "neutral"

def _getWNpos(p):
    if p == "j": return "a"
    return p

def _sanitize(l):
    return l.replace(".", "_").replace("-", "_")


def collectOntological(sent):
    concepts = []

    for tok in sent.xpath("./tokens/token"):
        word  = tok.xpath("./word/text()")[0]
        lemma = tok.xpath("./lemma/text()")[0]
        pos   = tok.xpath("./POS/text()")[0]
        ner   = tok.xpath("./NER/text()")[0]

        if pos.startswith("NNP"):
            print "%s_n(X) :- %s_n(X), use_ner." % (ner.lower(), _sanitize(lemma.lower()))

            concepts += [("%s_n" % lemma.lower(), word, ner)]
            concepts += [("%s_n" % ner.lower(), ner, "O")]

        elif pos.startswith("NN") or pos.startswith("VB") or pos.startswith("JJ"):

            # if lemma == "be": continue

            concepts += [("%s_%s" % (lemma.lower(), pos[0].lower()), word, ner)]

            try:
                s = wn.synset("%s.%s.01" % (lemma, _getWNpos(pos[0].lower())))

            except nltk.corpus.reader.wordnet.WordNetError:
                continue

            for lms in s.lemmas():
                if lms.name().lower() == lemma.lower(): continue

                print "%s_%s(X) :- %s_%s(X), use_synonym." % (
                    _sanitize(lms.name().lower()), pos[0].lower(),
                    _sanitize(lemma.lower()), pos[0].lower(), )

                concepts += [("%s_%s" % (lms.name().lower(), pos[0].lower()), lms.name(), ner)]

            for sh in s.hypernyms():
                for lmh in sh.lemma_names():
                    print "%s_%s(X) :- %s_%s(X), use_hypernym." % (_sanitize(lmh.lower()), pos[0].lower(), _sanitize(lemma.lower()), pos[0].lower(), )

                    print "{%s_%s(X)} :- %s_%s(X), use_loose_hypernym." % (_sanitize(lmh.lower()), pos[0].lower(), _sanitize(lemma.lower()), pos[0].lower(), )
                    print ":~ %s_%s(X), %s_%s(X), use_loose_hypernym. [f_loose_hyp(-1)@1, X]" % (_sanitize(lmh.lower()), pos[0].lower(), _sanitize(lemma.lower()), pos[0].lower(), )

                    concepts += [("%s_%s" % (lmh.lower(), pos[0].lower()), lmh, ner)]

    return concepts


def collectMentions(sent):
    #
    # Assign constants to nouns and events.
    mention2const = {}

    for tok in sent.xpath("./tokens/token"):
        text = tok.xpath("./word/text()")[0].lower()
        lemma = tok.xpath("./lemma/text()")[0].lower()
        ner  = tok.xpath("./NER/text()")[0].lower()
        pos   = tok.xpath("./POS/text()")[0]

        if pos.startswith("NN"):
            var = "m_%s_%s" % (tok.attrib["id"], _sanitize(text))
            mention2const[tok.attrib["id"]] = "M", var

            print "mention(%s). %s_n(%s). %s(%s). position(%s, %s)." % (
                var,
                _sanitize(lemma), var,
                "plural" if pos.endswith("S") else "singular", var,
                var, tok.attrib["id"],
            )

        if pos.startswith("VB") or pos.startswith("JJ"):
            # if lemma == "be": continue

            var = "e_%s_%s" % (tok.attrib["id"], _sanitize(text))
            mention2const[tok.attrib["id"]] = "E", var

            print "event(%s). %s_%s(%s)." % (var, _sanitize(lemma), pos[0].lower(), var)

    return mention2const


def collectEventRels(sent, mention2const):
    for dep in sent.xpath("./dependencies[@type='collapsed-ccprocessed-dependencies']/dep"):
        if dep.attrib["type"] not in "nsubj dobj nsubjpass iobj" and not dep.attrib["type"].startswith("nmod:"):
            continue

        dt      = dep.attrib["type"].replace(":", "_")
        gov, de = dep.xpath("./governor/@idx")[0], dep.xpath("./dependent/@idx")[0]

        if sent.xpath("./tokens/token[@id=%s]/POS/text()" % de)[0].startswith("PRP"):
            lemma = sent.xpath("./tokens/token[@id=%s]/lemma/text()" % de)[0]
            word = sent.xpath("./tokens/token[@id=%s]/word/text()" % de)[0]

            if not mention2const.has_key(gov):
                print >>sys.stderr, "Uncaught Error:", "Pronoun is not in mention predicates."
                continue

            print "pronoun(tok_%s_%s)." % (de, word.lower())
            print "position(tok_%s_%s, %s)." % (de, word.lower(), de)
            print "1 {pronominalized(X, tok_%s_%s): mention(X)} 1." % (de, word.lower())
            print "3 {%s(X); %s(X); %s(%s, X)} :- pronominalized(X, tok_%s_%s)." % (
                _getNumber(lemma),
                _getGender(lemma),
                dt, mention2const[gov][1],
                de, word.lower(),
                )

        else:
            if not mention2const.has_key(gov) or not mention2const.has_key(de):
                print >>sys.stderr, "Uncaught Error:", "Elements are not in mention predicates."
                continue

            print "%s(%s, %s)." % (dt, mention2const[gov][1], mention2const[de][1])


def collectFeatures(sent, mention2const, concepts):
    sp = selpref.selpref_t(pathKB="/work/naoya-i/kb")
    nc = ncnaive.ncnaive_t(
        "/work/naoya-i/kb/ncnaive0909.0.cdb",
        "/work/naoya-i/kb/tuples.0909.tuples.cdb")
    gn = googlengram.googlengram_t("/work/jun-s/kb/ngrams")

    relations = [
        dt for dt in sent.xpath("./dependencies[@type='collapsed-ccprocessed-dependencies']/dep/@type")
        if dt in "nsubj dobj nsubjpass iobj" or dt.startswith("nmod:")]

    tried_esa = {}

    # Surface features.
    for tok in sent.xpath("./tokens/token[./POS/text()='PRP']"):
        for m in mention2const:
            if mention2const[m][0] != "M": continue

            myatom = "pronominalized(%s, tok_%s_%s)" % (
                mention2const[m][1],
                tok.attrib["id"], tok.xpath("./word/text()")[0],
                )

            print ":~ %s. [f_surf_%s_%s(1)@1, tok_%s, m_%s] " % (
                myatom,
                mention2const[m][1].split("_")[-1], tok.xpath("./word/text()")[0],
                tok.attrib["id"],
                m,
                )

            print ":~ %s. [f_surf_%s(1)@1, tok_%s, m_%s] " % (
                myatom,
                mention2const[m][1].split("_")[-1],
                tok.attrib["id"],
                m,
                )

            print ":~ %s. [f_surf_%s(1)@1, tok_%s, m_%s] " % (
                myatom,
                tok.xpath("./word/text()")[0],
                tok.attrib["id"],
                m,
                )
            
            tokMen = sent.xpath("./tokens/token[@id='%s']" % m)[0]

            # Look at the predicate of this pronoun.
            for gov in sent.xpath("./dependencies[@type='collapsed-ccprocessed-dependencies']/dep[@type='nsubj' and ./dependent/@idx='%s']/governor/@idx" % tok.attrib["id"]):
                tokGov = sent.xpath("./tokens/token[@id='%s']" % gov)[0]
                freqx, freqy, freq = 0, 0, 0
                qtype  = ""

                if "JJ" == tokGov.xpath("./POS/text()")[0]:
                    q1, q2 = tokGov.xpath("./lemma/text()")[0], tokMen.xpath("./lemma/text()")[0]
                    qtype  = "JJNN"

                elif tokGov.xpath("./POS/text()")[0].startswith("VB"):
                    q1, q2 = tokMen.xpath("./word/text()")[0], tokGov.xpath("./word/text()")[0]
                    qtype  = "NNVB"

                if "" != qtype:
                    freqx, freqy, freq = gn.search([q1]), gn.search([q2]), gn.search([q1, q2])

                if 0 < freq:
                    print ":~ %s. [f_google_%s(%f)@1, tok_%s, m_%s] %% %s, %s" % (
                        myatom,
                        qtype,
                        math.log(1.0*freq/((1.0*freqx/gn.TOTAL)*freqy)),
                        tok.attrib["id"],
                        m,
                        q1, q2,
                        )


    for dt in relations:
        for cv, cvw, cvner in concepts:
            if "be_v" == cv: continue
            if not cv.endswith("_v") and not cv.endswith("_j"): continue

            # Selectional preference of slot.
            for cn, cnw, cnner in concepts:
                if not cn.endswith("_n"): continue

                if tried_esa.has_key((cv, dt, cn)): continue

                tried_esa[(cv, dt, cn)] = 1

                v, r, n = \
                    cv.replace("_", "-"), dt.replace("nsubjpass", "nsubj_pass").replace("nmod:", "prep_"), (cn[:-2] + "-n-O") if "O" == cnner else (cnw + "-n-%s" % cnner.upper())

                sps = sp.calc(v, r, n)

                if sps[1] < 1: continue

                print ":~ %s(E), %s(E, X), %s(X). [f_selpref(%f)@1, %s_x_%s_x_%s, X, E] %% %s, %s, %s" % (
                    _sanitize(cv),
                    dt.replace(":", "_"),
                    _sanitize(cn),
                    1.0*sps[0],
                    _sanitize(cv), dt.replace(":", "_"), _sanitize(cn),
                    v, r, n,
                )

    # Event slot association.
    for dt in relations:
        for cv, cvw, cvner in concepts:
            for dt2 in relations:
                for cv2, cv2w, cv2ner in concepts:
                    if cv == cv2: continue

                    if "be_v" == cv or "be_v" == cv2: continue
                    if not cv.endswith("_v") and not cv.endswith("_j"): continue
                    if not cv2.endswith("_v") and not cv2.endswith("_j"): continue

                    e1, e2 = "%s:%s" % (cv.replace("_", "-"), dt.replace("nmod:", "prep_")), \
                             "%s:%s" % (cv2.replace("_", "-"), dt2.replace("nmod:", "prep_"))

                    if e1 > e2: e1, e2 = e2, e1
                    if tried_esa.has_key((e1, e2)): continue

                    tried_esa[(e1, e2)] = 1

                    if nc.getFreq(e1, e2) < 1: continue

                    ncs = nc.getPMI(e1, e2)

                    print ":~ %s(E1), %s(E1, X), %s(E2), %s(E2, X). [f_esa(%f)@1, %s_x_%s_x_%s_x_%s, X, E1, E2]" % (
                        _sanitize(cv), dt.replace(":", "_"),
                        _sanitize(cv2), dt2.replace(":", "_"),
                        1.0*ncs,
                        _sanitize(cv), dt.replace(":", "_"), _sanitize(cv2), dt2.replace(":", "_"),
                    )


def main(args):
    x = etree.parse(args[0])

    for sent in x.xpath("/root/document/sentences/sentence"):
        print "%"
        print "% Input sentence:"
        print "%  ", " ".join(sent.xpath("tokens/token/word/text()"))
        print
        print "%"
        print "% Logical forms of sentence."

        m2c = collectMentions(sent)

        print

        collectEventRels(sent, m2c)

        print
        print "%"
        print "% Relevant knowledge base."
        print
        print "% Ontological knowledge."

        concepts = collectOntological(sent)

        print
        print "% World rules."

        collectFeatures(sent, m2c, concepts)


if "__main__" == __name__:
    main(sys.args)
