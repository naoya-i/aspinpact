
import sys
sys.path += [".."]

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
                fn="/home/naoya-i/data/dict/ses.tsv",
                fnHurting="/home/naoya-i/data/dict/hurting_verbs.tsv",
                fnHealing="/home/naoya-i/data/dict/healing_verbs.tsv",
                fnRespect="/home/naoya-i/data/dict/respect_verbs.tsv",
                fnRemove="/home/naoya-i/data/dict/removing_verbs.tsv",
            )

        print >>sys.stderr, "Done."


    def setDoc(self, doc):
        self.doc = doc


    def _xfNumber(self, tk):
        tk = self.doc.tokens[tk]

        if "PRP" == tk.pos:
            return "plural" if tk.lemma in ["we", "they", "these", "those"] else "singular"

        return "plural" if tk.pos.endswith("S") else "singular"


    def _xfGender(self, tk):
        tk = self.doc.tokens[tk]

        if tk.lemma == "he":  return "male"
        if tk.lemma == "she": return "female"
        if tk.lemma == "it": return "thing"

        if tk.ne == "PERSON":
            return self.gen.getGender(tk.lemma + " !")

        return "neutral"


    def _xfSenti(self, tk):
        tk = self.doc.tokens[tk]
        s  = self.sen.getAvgPolarity(tk.lemma)
        t  = 0.1

        if s > t: return "positive"
        if s < -t: return "negative"

        return "neutral"


    def _xfInvSenti(self, s):
        if "positive" == s: return "negative"
        if "negative" == s: return "positive"

        return "neutral"


    def _xfInvRsp(self, r):
        if "yes" == r: return "no"
        return "unknown"


    def _xfSlotSenti(self, tk, slot):
        tk = self.doc.tokens[tk]
        slot = slot.replace("nmod:", "prep_")
        return self.ses.calcHurting("%s-%s" % (tk.lemma, tk.pos[0].lower()), slot)


    def _xfIsRespected(self, tk, slot):
        tk = self.doc.tokens[tk]
        slot = slot.replace("nmod:", "prep_")
        return self.ses.isRespected("%s-%s" % (tk.lemma, tk.pos[0].lower()), slot)


    def _xfShouldBeRemoved(self, tk, slot):
        tk = self.doc.tokens[tk]
        slot = slot.replace("nmod:", "prep_")
        return self.ses.shouldBeRemoved("%s-%s" % (tk.lemma, tk.pos[0].lower()), slot)


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
