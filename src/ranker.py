import hashlib
import random
import math
import numpy as np
import subprocess
import collections
import os
import gurobipy as gp

from sklearn.feature_extraction import DictVectorizer
from extractBestAnswerSet import *
from scipy.sparse import dok_matrix, csr_matrix
from autograd import grad

RESOLUTION = 10000

class answerset_ranker_t:
    CORRECT = 0
    NO_LVC  = 1
    UPDATED = 2
    INDISTINGUISHABLE = 3
    CANNOT_PREDICT = 4

    def __init__(self, eta=0.01, C = 0.0001, epsilon=0.01, alg = "PA-II"):
        self.dv = DictVectorizer()
        self.coef_ = None
        self.C = C
        self.eta = eta
        self.epsilon = epsilon
        self.updateAlg = alg
        self.weightInitializer = lambda fidx: 0
        self.lastInferenceTime = 0
        self.myhash = hashlib.sha1(str(random.random())).hexdigest()

        
    def set_features(self, features):
        self.dv.fit([features])
        self.coef_ = np.array([0.0]*len(features.keys()))
        self.adagrad = np.array([0.0]*self.coef_.shape[0])

        for i in xrange(self.coef_.shape[0]):
            self.coef_[i] = self.weightInitializer(i)

            
    def predict(self, lpfiles, goldAtoms=[], lossAugmented=False, enum=False):
        regexWeakConstraint = re.compile(":~(.*?)\[f_(.*?)\(([-0-9.e]+)\)@(.*?)\]")

        # Generate feature-weighted answer set program.
        fnTmp = "/work/naoya-i/tmp/aspinpact_%s.pl" % self.myhash
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

                    print >>tmpf, "%% %.3f x %f" % (self.coef_[fidx], fvalue)
                    print >>tmpf, "f_%s(%s, %s) :- %s" % (fname, _sanitize(fvalue), binder, constraint)
                    print >>tmpf, ":~ f_%s(%s, %s). [%d@1, %s]" % (
                        fname, _sanitize(fvalue), binder,
                        int(-RESOLUTION*self.coef_[fidx]*fvalue), binder)

                else:
                    print >>tmpf, ln.strip()

        # Constrain the answer set space to one including gold atoms.
        if len(goldAtoms) > 0:
            if lossAugmented:
                for a in goldAtoms:
                    print >>tmpf, ":~ not %s. [-1@1, lossaug_%s]" % (a, re.sub("[\(\),]", "_", a))
                    
            else:
                print >>tmpf, "correct :- %s." % (", ".join([a for a in goldAtoms]))
                print >>tmpf, ":- not correct."

        tmpf.close()

        # Use clingo to get the prediction.
        pClingo = subprocess.Popen(
            ["/home/naoya-i/tmp/clingo-4.5.3-linux-x86_64/clingo",
             "-n 0",
             "--opt-mode=opt" if not enum else "--opt-mode=enum",
             fnTmp],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

        clingoret = pClingo.stdout.read()
        clingoerr = pClingo.stderr.read()

        m = re.findall("Time         : ([0-9.]+)", clingoret)

        if len(m) > 0:
            self.lastInferenceTime = float(m[0])

        os.system("rm %s" % fnTmp)

        if enum:
            return [(-1.0*c/RESOLUTION, a) for c, a in extractAnswerSets(clingoret)]
        
        return [(-1.0*c/RESOLUTION, a) for c, a in extractBestAnswerSets(clingoret)]


    def fit(self):
        return False
        

    def feed(self, aspfiles, goldAtoms):

        myloss, diff = 0.0, np.array([0.0] * self.coef_.shape[0])

        # First, guess what.
        predictions = self.predict(aspfiles, goldAtoms, lossAugmented=True)

        if 0 == len(predictions):
            return answerset_ranker_t.CANNOT_PREDICT, 0.0, None

        pCurCost, pCurrent = predictions[0]
        vCurrent = _getFeatureVector(pCurrent, self.dv)
        vCurrent /= np.linalg.norm(vCurrent.toarray()[0])
        
        # Is the guess correct?
        if set(goldAtoms).issubset(set(pCurrent)):
            return answerset_ranker_t.CORRECT, 0.0, None

        # Guess correct label.
        goals = self.predict(aspfiles, goldAtoms)

        # Find answer set containing gold atoms.
        pGoal = None

        for c, a in goals:
            if set(goldAtoms).issubset(set(a)):
                pGoalCost, pGoal = c, a
                vGoal = _getFeatureVector(pGoal, self.dv)
                vGoal /= np.linalg.norm(vGoal.toarray()[0])
                break

        if None == pGoal:
            return answerset_ranker_t.NO_LVC, 0.0, None

        # If it is not inferred, then give up.
        assert(not set(goldAtoms).issubset(set(pCurrent)))
        assert(set(goldAtoms).issubset(set(pGoal)))

        myloss, diff = 0.0, np.array([0.0]*self.coef_)
       
        if "structperc" == self.updateAlg:
            def loss(w, c, g):
                prior  = 0.5*np.dot(w, w)**2
                likeli = np.dot(w, c) - np.dot(w, g) + math.sqrt(len(set(goldAtoms) - set(pCurrent)))
                return max(0, prior + likeli)
            
            diff   = grad(loss)(self.coef_, vCurrent.toarray()[0], vGoal.toarray()[0])
            myloss = loss(self.coef_, vCurrent.toarray()[0], vGoal.toarray()[0])

            # Update the weights.
            for i, v_i in enumerate(diff):
                self.adagrad[i] += v_i*v_i
                self.coef_[i] -= self.eta/math.sqrt(1+self.adagrad[i])*v_i

                    
        elif self.updateAlg in ["PA-I", "PA-II"]:
            # See Crammer et al. 2006 for more details.
            w, c, g = self.coef_, vCurrent.toarray()[0], vGoal.toarray()[0]
            myloss = np.dot(w, c) - np.dot(w, g) + math.sqrt(len(set(goldAtoms) - set(pCurrent)))
            norm2 = np.linalg.norm(g - c) ** 2

            if norm2 == 0.0:
                return answerset_ranker_t.INDISTINGUISHABLE, 0.0, diff # Cannot update.

            if "PA-I" == self.updateAlg:
                tau = min(self.C, myloss / norm2)

            elif "PA-II" == self.updateAlg:
                tau = myloss / (norm2 + 1.0/(2*self.C))

            # Update the weights.
            self.coef_ = self.coef_ + tau * (g - c)


        else:
            raise "Unsupported algorithm: %s" % self.updateAlg

        return answerset_ranker_t.UPDATED, myloss, diff

#
# Helper functions.
def _getFeatureVector(answerset, dv):
    vec = collections.defaultdict(float)
    regexWeakConstraint = re.compile("f_(.*?)\((.*?),")

    for a in answerset:
        m = regexWeakConstraint.search(a)

        if None != m:
            fname, fvalue = m.group(1), float(_drink(m.group(2)))
            vec[fname] += 1.0 * fvalue

    return dv.transform(vec)


def _sanitize(f):
    return "v_%s" % (str(f).replace(".", "D").replace("-", "M"))


def _drink(f):
    return f.replace("D", ".").replace("M", "-")[2:]
