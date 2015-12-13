
import sys

from features import gender, sentimentpolarity, selpref, ncnaive, sentieventslot, googlengram

class evaluator_t:
    def __init__(self):
        print >>sys.stderr, "Loading resources..."

        self.gen = gender.gender_t("/home/naoya-i/data/dict/gender.data.cut10.gz")
        self.sen = sentimentpolarity.sentimentpolarity_t(
            fn_wilson05="/home/naoya-i/data/dict/subjclueslen1-HLTEMNLP05.tff",
            fn_sentiwordnet="/home/naoya-i/data/dict/SentiWordNet_3.0.0_20130122.txt",
            fn_warriner13="/home/naoya-i/data/dict/Ratings_Warriner_et_al.csv",
            fn_takamura05="/home/naoya-i/data/dict/pn_en.dic",
        )
        self.sp = selpref.selpref_t(pathKB="/work/naoya-i/kb")
        self.nc = ncnaive.ncnaive_t(
            "/work/naoya-i/kb/ncnaive0909.0.cdb",
            "/work/naoya-i/kb/tuples.0909.tuples.cdb")
        self.ses = sentieventslot.sentieventslot_t(
                fn="/home/naoya-i/data/dict/pnverbs.tsv",
            )

        print >>sys.stderr, "Done."


    def setDoc(self, doc):
        self.doc = doc


    def _wfSelpref(self, n, p, vp, t):
        t = t.replace("nsubjpass", "nsubj_pass").replace("nmod:", "prep_")

        if "O" != self.doc.tokens[n].ne:
            return 0

        sps = self.sp.calc("%s-%s" % (self.doc.tokens[vp].lemma, self.doc.tokens[vp].pos[0].lower()),
                           t,
                           "%s-%s-%s" % (self.doc.tokens[n].lemma, self.doc.tokens[n].pos[0].lower(), self.doc.tokens[n].ne),
                           )
        return sps[0]


    def _wfESA(self, n, p, vn, tn, vp, tp):
        tn = tn.replace("nmod:", "prep_")
        tp = tp.replace("nmod:", "prep_")

        e1, e2 = "%s-%s:%s" % (self.doc.tokens[vp].lemma, self.doc.tokens[vp].pos[0].lower(), tp), \
                 "%s-%s:%s" % (self.doc.tokens[vn].lemma, self.doc.tokens[vn].pos[0].lower(), tn)

        if e1 > e2: e1, e2 = e2, e1

        ncs = self.nc.getPMI(e1, e2)

        return ncs

print >>sys.stderr,  "HELLO, MY WORLD!!!!"

ev = evaluator_t()

def setDoc(doc):
    ev.setDoc(doc)


def xfNumber(tk):
    tk = ev.doc.tokens[tk]

    if "PRP" == tk.pos:
        return "plural" if tk.lemma in ["we", "they", "these", "those"] else "singular"

    return "plural" if tk.pos.endswith("S") else "singular"


def xfGender(tk):
    tk = ev.doc.tokens[tk]

    if tk.lemma == "he":  return "male"
    if tk.lemma == "she": return "female"
    if tk.lemma == "it": return "thing"

    if tk.ne == "PERSON":
        return ev.gen.getGender(tk.lemma + " !")

    return "neutral"


def xfDeepSenti(tk):
    tk = ev.doc.tokens[tk]
    ret = []

    for rel, label in ev.ses.getPol("%s-%s" % (tk.lemma, tk.pos[0].lower())):
        ret += ["%s(R, T) :- dep(\"%s\", %s, T), dep(\"%s\", %s, R)." % (label, rel, tk.id, ev.ses.getRefRel(rel), tk.id)]

    return "\n".join(ret)


def xfSenti(w):
    s  = ev.sen.getAvgPolarity(w)
    t  = 0.1

    if s > t: return "p"
    if s < -t: return "n"

    return "0"


def xfInvSenti(s):
    if "positive" == s: return "negative"
    if "negative" == s: return "positive"

    return "neutral"


def xfInvRsp(r):
    if "yes" == r: return "no"
    return "unknown"


def xfSlotSenti(tk, slot):
    tk = ev.doc.tokens[tk]
    slot = slot.replace("nmod:", "prep_")
    return ev.ses.calcHurting("%s-%s" % (tk.lemma, tk.pos[0].lower()), slot)


def xfIsRespected(tk, slot):
    tk = ev.doc.tokens[tk]
    slot = slot.replace("nmod:", "prep_")
    return ev.ses.isRespected("%s-%s" % (tk.lemma, tk.pos[0].lower()), slot)


def xfShouldBeRemoved(tk, slot):
    tk = ev.doc.tokens[tk]
    slot = slot.replace("nmod:", "prep_")
    return ev.ses.shouldBeRemoved("%s-%s" % (tk.lemma, tk.pos[0].lower()), slot)
