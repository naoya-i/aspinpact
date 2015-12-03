
import sys
sys.path += [".."]

from features import gender, sentimentpolarity


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

        
    def _xfSlotSenti(self, tk, slot):
        return "A"
        
        
