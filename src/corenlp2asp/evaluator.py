
import sys

from features import gender, sentimentpolarity, selpref, ncnaive, sentieventslot, googlengram

def _convrel(rel):
    if "dobj" == rel:
        return ["dobj", "nsubjpass"]
    elif "nsubj" == rel:
        return ["nsubj", "nmod:agent"]
    else:
        return [rel.replace("prep_", "nmod:")]

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


    #
    # Feature functions.
    def numberMatch(self): return 1
    def genderMatch(self): return 1


    def selpref(self, vp, vp_pos, t, n):
        t = t.replace("nsubjpass", "nsubj_pass").replace("nmod:", "prep_")

        sps = self.sp.calc("%s-%s" % (vp, vp_pos[0].lower(),),
                           t,
                           "%s-n-O" % (n,),
                           )
        return sps[0]


    def esa(self, vn, vn_pos, tn, vp, vp_pos, tp):
        tn = tn.replace("nmod:", "prep_")
        tp = tp.replace("nmod:", "prep_")

        e1, e2 = "%s-%s:%s" % (vp, vp_pos[0].lower(), tp), \
                 "%s-%s:%s" % (vn, vn_pos[0].lower(), tn)

        if e1 > e2: e1, e2 = e2, e1

        ncs = self.nc.getPMI(e1, e2)

        return ncs


    #
    # Dynamic value functions.
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


    def senti(self, w):
        s  = self.sen.getAvgPolarity(w)
        t  = 0.1

        if s > t: return "p"
        if s < -t: return "n"

        return []


    def wi05senti(self, w):
        sc = self.sen.getPolarity(w, self.sen.wi05, None)
        return {1: "p", -1: "n", None: []}.get(sc, [])


    def g13ppvsenti(self, lemma):
        return self.ses.getG13Pol(lemma)


    def c14ewnsenti(self, lemma):
        return self.ses.getC14Pol(lemma)


    def fgafstsenti(self, lemma):
        ret = self.ses.getFineGrainedAS(lemma)

        if len(ret) > 0 and ret[0][1] == "dobj":
            return ret + [(ret[0][0], "nsubjpass")]

        return self.ses.getFineGrainedAS(lemma)


    def dsTargetArg(self, v, v_pos, dst):
        ret = []

        for rel, label in self.ses.getPol("%s-%s" % (v, v_pos[0].lower())):
            if label == dst:
                ret += _convrel(rel)

        if 0 < len(ret):
            return ret

        return "n_a"


    def dsSubArg(self, v, v_pos, dst):
        for rel, label in self.ses.getPol("%s-%s" % (v, v_pos[0].lower())):
            if label == dst:
                return _convrel(self.ses.getRefRel(rel))

        return "n_a"
