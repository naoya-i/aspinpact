
import sys

from lxml import etree

def collectMentions(sent):
    #
    # Assign constants to nouns.
    mention2const = {}

    for tok in sent.xpath("./tokens/token"):
        if tok.xpath("./POS/text()")[0].startswith("NN"):
            mention2const[tok.attrib["id"]] = tok.xpath("./word/text()")[0].lower(), tok.xpath("./NER/text()")[0].lower()

    return mention2const


def collectEventRels(sent, mention2const):
    event_rels = []
    on_the_fly = []

    for dep in sent.xpath("./dependencies[@type='collapsed-ccprocessed-dependencies']/dep"):
        if dep.attrib["type"] in "nsubj dobj nsubjpass iobj" or dep.attrib["type"].startswith("prep_"):
            gov, de = dep.xpath("./governor/@idx")[0], dep.xpath("./dependent/@idx")[0]

            if sent.xpath("./tokens/token[@id=%s]/POS/text()" % de)[0] == "PRP":
                verb = sent.xpath("./tokens/token[@id=%s]/lemma/text()" % gov)[0]
                event_rels += ["1 {%s_%s(X): mention(X)} 1." % (verb, dep.attrib["type"])]

                for mv, mner in mention2const.values():
                    on_the_fly += [":~ %s_%s(%s). [1@1, selpref_%s]" % (verb, dep.attrib["type"], mv, mv)]
                    on_the_fly += [":~ %s_%s(%s). [1@1, selpref_%s]" % (verb, dep.attrib["type"], mv, mv)]

            else:
                event_rels += ["%s_%s(%s)." % (sent.xpath("./tokens/token[@id=%s]/lemma/text()" % gov)[0], dep.attrib["type"], mention2const[de][0])]

    return event_rels, on_the_fly


def main():
    x = etree.parse(sys.argv[1])

    for sent in x.xpath("/root/document/sentences/sentence"):
        mention2const = collectMentions(sent)
        event_rels, on_the_fly = collectEventRels(sent, mention2const)

        #
        # Print them.
        print "%"
        print "% Input sentence:"
        print "%  ", " ".join(sent.xpath("tokens/token/word/text()"))
        print
        print "%"
        print "% Mentions."
        for mv, mner in mention2const.values(): print "mention(%s). %s(%s). %s(%s)." % (mv, mv, mv, mner if mner != "o" else "generic-noun", mv)
        print
        print "%"
        print "% Logical forms of sentence."
        for e in event_rels: print e
        print
        print "%"
        print "% On-the-fly constraints."
        for c in on_the_fly: print c

if "__main__" == __name__:
    main()
