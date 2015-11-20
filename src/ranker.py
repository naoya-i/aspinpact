
import random
import math
import numpy as np
import subprocess
import collections

from sklearn.feature_extraction import DictVectorizer
from extractBestAnswerSet import *
from scipy.sparse import dok_matrix, csr_matrix
from autograd import grad

class answerset_ranker_t:
    def __init__(self, C = 1.0, l2reg = 0.01, alg = "PA-II"):
        self.dv = DictVectorizer()
        self.coef_ = None
        self.C = C
        self.l2reg = l2reg
        self.updateAlg = alg
        self.lastInferenceTime = 0


    def set_features(self, features):
        self.dv.fit([features])
        self.coef_ = dok_matrix((1, len(features.keys())))
        self.batch_sumFeatureVector = dok_matrix(self.coef_.shape)


    def predict(self, lpfiles, goldAtoms=[], bad=False, lossAugmented=False):
        regexWeakConstraint = re.compile(":~(.*?)\[f_(.*?)\(([-0-9.e]+)\)@(.*?)\]")

        # Generate feature-weighted answer set program.
        fnTmp = "/work/naoya-i/tmp/aspinpact.pl"
        tmpf = open(fnTmp, "w")

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
                        
                        self.coef_[0, fidx] = 1 # (random.random()-0.5)*2.0

                    print >>tmpf, "%% %.3f x %f" % (self.coef_[0, fidx], fvalue)
                    print >>tmpf, "f_%s(%s, %s) :- %s" % (fname, _sanitize(fvalue), binder, constraint)
                    print >>tmpf, ":~ f_%s(%s, %s). [%d@1, %s]" % (
                        fname, _sanitize(fvalue), binder,
                        int(-10000*self.coef_[0, fidx]*fvalue), binder)

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
             fnTmp],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

        clingoret = pClingo.stdout.read()
        clingoerr = pClingo.stderr.read()

        # print clingoerr

        m = re.findall("Time         : ([0-9.]+)", clingoret)

        if len(m) > 0:
            self.lastInferenceTime = float(m[0])

        cost, answerset = extractBestAnswerSet(clingoret)
        
        return -cost, answerset


    def fit(self):
        if "batch" != self.updateAlg: return

        self.coef_ = 0.01 * (self.coef_ - self.batch_sumFeatureVector)
        self.batch_sumFeatureVector = dok_matrix(self.coef_.shape)
        
        
    def feed(self, aspfiles, goldAtoms):

        # First, guess what.
        pCurCost, pCurrent = self.predict(aspfiles) #, goldAtoms, lossAugmented=True)
        vCurrent = _getFeatureVector(pCurrent)

        # Is the guess correct?
        if set(goldAtoms) & set(pCurrent) == set(goldAtoms):
            return 0.0, None

        # Guess correct label.
        pGoalCost, pGoal = self.predict(aspfiles, goldAtoms)
        vGoal = _getFeatureVector(pGoal)

        # If it is not inferred, then give up.
        if set(goldAtoms) & set(pGoal) != set(goldAtoms):
            return 0.0, None

        if pCurCost == pGoalCost:
            return 0.0, None

        npCurrent, npGoal = self.dv.transform([vCurrent, vGoal])
        myloss, diff = 0.0, np.array([0.0]*self.coef_)
        
        if "batch" == self.updateAlg:
            self.batch_sumFeatureVector = self.batch_sumFeatureVector + (npCurrent - npGoal)
            myloss = pCurCost - pGoalCost
            
        elif "structperc" == self.updateAlg:
            def loss(w, c, g):
                prior  = 0.5*np.dot(w, w)
                likeli = np.dot(w, c) - np.dot(w, g) + math.sqrt(len(set(goldAtoms) - set(pCurrent)))
                return prior + likeli

            diff   = 0.01*grad(loss)(self.coef_.toarray()[0], npCurrent.toarray()[0], npGoal.toarray()[0])
            myloss = loss(self.coef_.toarray()[0], npCurrent.toarray()[0], npGoal.toarray()[0])

            # Update the weight vector.
            for i, v_i in enumerate(diff):
                self.coef_[0, i] -= v_i

        elif self.updateAlg in ["PA-I", "PA-II"]:
            # See Crammer et al. 2006 for more details.
            myloss = pCurCost - pGoalCost + math.sqrt(len(set(goldAtoms) - set(pCurrent)))
            norm2 = np.linalg.norm((npGoal - npCurrent).toarray()[0]) ** 2

            if norm2 == 0.0:
                return myloss # Cannot update.

            if "PA-I" == self.updateAlg:
                tau = min(self.C, myloss / norm2)

            elif "PA-II" == self.updateAlg:
                tau = myloss / (norm2 + 1.0/(2*self.C))

            # Update the weight.
            self.coef_ = self.coef_ + tau * (npGoal - npCurrent)

        return myloss, diff

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
