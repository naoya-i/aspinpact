
import sys
import collections

sys.path += ["/home/naoya-i/work/clone/wsc/src"]
import selpref
import ncnaive
import nltk

from lxml import etree
from nltk.corpus import wordnet as wn


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


def collectOntological(sent):
    concepts = []

    for tok in sent.xpath("./tokens/token"):
        word  = tok.xpath("./word/text()")[0]
        lemma = tok.xpath("./lemma/text()")[0]
        pos   = tok.xpath("./POS/text()")[0]
        ner   = tok.xpath("./NER/text()")[0]

        if pos.startswith("NNP"):
            # print "%s_n(X) :- %s_n(X)." % (ner.lower(), lemma.lower())

            concepts += [("%s_n" % lemma.lower(), word, ner)]

            if "O" != ner:
                concepts += [("%s_n" % ner.lower(), ner, "O")]

        elif pos.startswith("NN") or pos.startswith("VB") or pos.startswith("JJ"):

            # if lemma == "be": continue

            concepts += [("%s_%s" % (lemma.lower(), pos[0].lower()), word, ner)]

            try:
                s = wn.synset("%s.%s.01" % (lemma, _getWNpos(pos[0].lower())))

            except nltk.corpus.reader.wordnet.WordNetError:
                continue

            continue

            for sh in s.hypernyms():
                for lmh in sh.lemma_names():
                    print "%s_%s(X) :- %s_%s(X)." % (lmh.lower(), pos[0].lower(), lemma.lower(), pos[0].lower(), )

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
            if tok.getnext().xpath("./POS/text()")[0].startswith("NN"):
                continue
                
            var = "m_%s_%s" % (tok.attrib["id"], text)
            mention2const[tok.attrib["id"]] = "M", var

            print "mention(%s). position(%s, %s). %s_n(%s). %s(%s)." % (
                var,
                var, tok.attrib["id"],
                lemma, var,
                "plural" if pos.endswith("S") else "singular", var,
            )

        if pos.startswith("VB") or pos.startswith("JJ"):
            # if lemma == "be": continue

            var = "e_%s_%s" % (tok.attrib["id"], text)
            mention2const[tok.attrib["id"]] = "E", var

            print "event(%s). %s_%s(%s)." % (var, lemma, pos[0].lower(), var)

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

            print "1 {pronominalized(X, tok_%s_%s): mention(X), position(X, Y), Y<%s} 1." % (de, word.lower(), de)

            try:
                print "3 {%s(X); %s(X); %s(%s, X)} :- pronominalized(X, tok_%s_%s)." % (
                    _getNumber(lemma),
                    _getGender(lemma),
                    dt, mention2const[gov][1],
                    de, word.lower(),
                )
            except KeyError:
                print >>sys.stderr, "Error!", dt, gov, de

        else:
            try:
                print "%s(%s, %s)." % (dt, mention2const[gov][1], mention2const[de][1])

            except KeyError:
                print >>sys.stderr, "Error!", dt, gov, de


def collectFeatures(sent, mention2const, concepts):
    sp = selpref.selpref_t(pathKB="/work/jun-s/kb")
    nc = ncnaive.ncnaive_t(
        "/work/jun-s/kb/corefevents.0901.exact.cdblist.ncnaive.0.cdb",
        "/work/jun-s/kb/corefevents.0901.exact.cdblist.tuples.cdb")

    relations = [
        dt for dt in sent.xpath("./dependencies[@type='collapsed-ccprocessed-dependencies']/dep/@type")
        if dt in "nsubj dobj nsubjpass iobj" or dt.startswith("nmod:")]

    tried_esa = {}

    for dt in relations:
        for cv, cvw, cvner in concepts:
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

                print ":~ %s(E), %s(E, X), %s(X). [%d@1, selpref, %s_x_%s_x_%s, X, E] %% %s, %s, %s" % (
                    cv,
                    dt.replace(":", "_"),
                    cn,
                    int(-1000*sps[0]),
                    cv, dt.replace(":", "_"), cn,
                    v, r, n,
                )

    # Event slot association.
    for dt in relations:
        for cv, cvw, cvner in concepts:
            for dt2 in relations:
                for cv2, cv2w, cv2ner in concepts:
                    if cv == cv2: continue
    
                    if not cv2.endswith("_v") and not cv2.endswith("_j"): continue
    
                    e1, e2 = "%s:%s" % (cv.replace("_", "-"), dt.replace("nmod:", "prep_")), \
                             "%s:%s" % (cv2.replace("_", "-"), dt2.replace("nmod:", "prep_"))
    
                    if e1 > e2: e1, e2 = e2, e1
                    if tried_esa.has_key((e1, e2)): continue
    
                    tried_esa[(e1, e2)] = 1
    
                    # if nc.getFreq(e1, e2) < 10: continue
    
                    ncs = nc.getPMI(e1, e2)
    
                    print ":~ %s(E1), %s(E1, X), %s(E2), %s(E2, X). [%d@1, esa, %s_x_%s_x_%s_x_%s, X, E1, E2]" % (
                        cv, dt.replace(":", "_"),
                        cv2, dt2.replace(":", "_"),
                        int(-1000*ncs),
                        cv, dt.replace(":", "_"), cv2, dt2.replace(":", "_"),
                    )


def main():
    x = etree.parse(sys.argv[1])

    for sent in x.xpath("/root/document/sentences/sentence"):
        print "%"
        print "% Input sentence:"
        print "%  ", " ".join(sent.xpath("tokens/token/word/text()"))
        print
        print "%"
        print "% Logical forms of sentence."

        mention2const = collectMentions(sent)

        print

        collectEventRels(sent, mention2const)

        print
        print "%"
        print "% Relevant knowledge base."
        print
        print "% Ontological."

        concepts = collectOntological(sent)

        print
        print "% World axioms."

        collectFeatures(sent, mention2const, concepts)


if "__main__" == __name__:
    main()
