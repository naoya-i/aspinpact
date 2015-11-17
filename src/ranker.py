
import math
import numpy as np
import subprocess
import collections

from sklearn.feature_extraction import DictVectorizer
from extractBestAnswerSet import *
from scipy.sparse import dok_matrix

class answerset_ranker_t:
    def __init__(self, C = 1.0, alg = "PA-II"):
        self.dv = DictVectorizer()
        self.coef_ = None
        self.C = C
        self.updateAlg = alg
        self.lastInferenceTime = 0
        

    def set_features(self, features):
        self.dv.fit([features])
        self.coef_ = dok_matrix((1, len(features.keys())))

        
    def predict(self, lpfiles, goldAtoms=[], bad=False, lossAugmented=False):
        regexWeakConstraint = re.compile(":~(.*?)\[f_(.*?)\(([-0-9.e]+)\)@(.*?)\]")

        # Generate feature-weighted answer set program.
        tmpf = open("./tmp.pl", "w")

        for fn in lpfiles:
            for ln in open(fn):
                m = regexWeakConstraint.search(ln)

                # To record feature vector.
                if None != m:
                    constraint, fname, fvalue, binder = m.groups()
                    constraint, fname, fvalue, binder = constraint.strip(), \
                                                        fname.strip(), \
                                                        float(fvalue.strip()), \
                                                        ",".join(binder.split(",")[1:]).strip()
                    fidx = self.dv.vocabulary_[fname]

                    if 0.0==self.coef_[0, fidx]:
                        self.coef_[0, fidx] = 1
                        
                    print >>tmpf, "%% %.3f x %f" % (self.coef_[0, fidx], fvalue)
                    print >>tmpf, "f_%s(%s, %s) :- %s" % (fname, _sanitize(fvalue), binder, constraint)
                    print >>tmpf, ":~ f_%s(%s, %s). [%d@1, %s]" % (
                        fname, _sanitize(fvalue), binder,
                        int(10000*self.coef_[0, fidx]*fvalue), binder)

                else:
                    print >>tmpf, ln.strip()

        # Constrain the answer set space to one including gold atoms.
        if len(goldAtoms) > 0:
            if lossAugmented:
                for a in goldAtoms:
                    print >>tmpf, ":~ not %s. [-1@1, lossaug_%s]" % (a, re.sub("[\(\),]", "_", a))
                
            else:
                print >>tmpf, "correct :- %s." % (", ".join([a for a in goldAtoms]))
                
                if bad:
                    print >>tmpf, ":~ correct. [999999@1]"

                else:
                    print >>tmpf, ":~ not correct. [999999@1]"

        tmpf.close()

        # Use clingo to get the prediction.
        pClingo = subprocess.Popen(
            ["/home/naoya-i/tmp/clingo-4.5.3-linux-x86_64/clingo",
             "-n 0",
             "--opt-mode=opt",
             "./tmp.pl"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

        clingoret = pClingo.stdout.read()
        clingoerr = pClingo.stderr.read()

        m = re.findall("Time         : ([0-9.]+)", clingoret)

        if len(m) > 0:
            self.lastInferenceTime = float(m[0])
        
        return extractBestAnswerSet(clingoret)

        
    def update(self, aspfiles, goldAtoms):

        # First, guess what.
        pCurrent = self.predict(aspfiles, goldAtoms, lossAugmented=True)
        vCurrent = _getFeatureVector(pCurrent)

        # Is the guess correct?
        if set(goldAtoms) & set(pCurrent) == set(goldAtoms):
            return 0.0
            
        # Guess correct label.
        pGoal = self.predict(aspfiles, goldAtoms)
        vGoal = _getFeatureVector(pGoal)

        npCurrent, npGoal = self.dv.transform([vCurrent, vGoal])
        npCurrent, npGoal = -npCurrent, -npGoal

        # See Crammer et al. 2006 for more details.
        loss = (self.coef_.T*npCurrent)[0, 0] - \
               (self.coef_.T*npGoal)[0, 0] + \
               (len(set(goldAtoms) - set(pCurrent)))
        norm2 = np.linalg.norm((npGoal - npCurrent).toarray()[0]) ** 2

        if norm2 == 0.0: return loss # Cannot update.
            
        if "PA-I" == self.updateAlg:
            tau = min(self.C, loss / norm2)
            
        elif "PA-II" == self.updateAlg:
            tau = loss / (norm2 + 1.0/(2*self.C))

        # Update the weight.
        self.coef_ = self.coef_ + tau * (npGoal - npCurrent)

        return loss

#        
# Helper functions.                
def _getFeatureVector(answerset):
    vec = collections.defaultdict(float)
    regexWeakConstraint = re.compile("f_(.*?)\((.*?),")

    for a in answerset:
        m = regexWeakConstraint.search(a)
        
        if None != m:
            fname, fvalue = m.group(1), float(_drink(m.group(2)))
            vec[fname] += 1.0 * fvalue
            
    return vec

    
def _sanitize(f):
    return "v_%s" % (str(f).replace(".", "D").replace("-", "M"))
                     

def _drink(f):
    return f.replace("D", ".").replace("M", "-")[2:]
