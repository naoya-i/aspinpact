
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


    def number(self, lemma, pos):
        if "PRP" == pos:
            return "plural" if lemma in ["we", "they", "these", "those"] else "singular"

        return "plural" if pos.endswith("S") else "singular"


    def gender(self, lemma, ne):
        if lemma == "he":  return "male"
        if lemma == "she": return "female"
        if lemma == "it": return "thing"

        if ne == "PERSON":
            return self.gen.getGender(lemma + " !")

        return "neutral"


    def xfDeepSenti(self, tk):
        tk = self.doc.tokens[tk]
        ret = []

        for rel, label in self.ses.getPol("%s-%s" % (tk.lemma, tk.pos[0].lower())):
            ret += ["%s(R, T) :- dep(\"%s\", %s, T), dep(\"%s\", %s, R)." % (label, rel, tk.id, self.ses.getRefRel(rel), tk.id)]

        return "\n".join(ret)


    def senti(self, w):
        s  = self.sen.getAvgPolarity(w)
        t  = 0.1

        if s > t: return "p"
        if s < -t: return "n"

        return "0"


    def xfInvSenti(self, s):
        if "positive" == s: return "negative"
        if "negative" == s: return "positive"

        return "neutral"


    def xfInvRsp(self, r):
        if "yes" == r: return "no"
        return "unknown"


    def xfSlotSenti(self, tk, slot):
        tk = self.doc.tokens[tk]
        slot = slot.replace("nmod:", "prep_")
        return self.ses.calcHurting("%s-%s" % (tk.lemma, tk.pos[0].lower()), slot)


    def xfIsRespected(self, tk, slot):
        tk = self.doc.tokens[tk]
        slot = slot.replace("nmod:", "prep_")
        return self.ses.isRespected("%s-%s" % (tk.lemma, tk.pos[0].lower()), slot)


    def xfShouldBeRemoved(self, tk, slot):
        tk = self.doc.tokens[tk]
        slot = slot.replace("nmod:", "prep_")
        return self.ses.shouldBeRemoved("%s-%s" % (tk.lemma, tk.pos[0].lower()), slot)
