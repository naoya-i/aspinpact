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
        self.lastInferenceTime = 0
        self.myhash = hashlib.sha1(str(random.random())).hexdigest()

        
    def set_features(self, features):
        self.dv.fit([features])
        self.coef_ = np.array([0.0]*len(features.keys()))
        self.adagrad = np.array([0.0]*self.coef_.shape[0])
        self.batch_sumFeatureVector = np.array([0.0]*self.coef_.shape[0])

        self.initGurobi()
        

    def initGurobi(self):
        self.grbopt = gp.Model("mipl")
        self.grbopt.params.OutputFlag = 0
        
        self.grbvars = []
        self.grbvarSlack = self.grbopt.addVar(0.0, gp.GRB.INFINITY, 0.0, gp.GRB.CONTINUOUS, "slack")
        
        for i in xrange(self.coef_.shape[0]):
            self.grbvars += [self.grbopt.addVar(-gp.GRB.INFINITY, gp.GRB.INFINITY, 0.0, gp.GRB.CONTINUOUS, "w_%d" % i)]
            
        self.grbopt.update()

        #
        # Construct objective function.
        obj = gp.QuadExpr()
        for i, w_i in enumerate(self.coef_):
            obj += 0.5*self.grbvars[i]*self.grbvars[i]
        obj += self.C*self.grbvarSlack

        self.grbopt.setObjective(obj)
            
        self.grbconstr = gp.LinExpr()
        self.grbloss = 0
        self.numFedExamples = 0
        self.accumulatedLoss = 0
        
            
    def predict(self, lpfiles, goldAtoms=[], bad=False, lossAugmented=False, enum=False):
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

                    # # Initialization.
                    if 0.0 == self.coef_[fidx]:
                        self.coef_[fidx] = 1 # random.random()*0.1 # *2.0

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

                # print >>tmpf, "correct :- %s." % (", ".join([a for a in goldAtoms]))
                # print >>tmpf, ":- correct."
                    
            else:
                print >>tmpf, "correct :- %s." % (", ".join([a for a in goldAtoms]))

                if bad:
                    pass #print >>tmpf, ":~ correct. [9999999999@1]"
                    #print >>tmpf, ":~ correct. [9999999999@1]"

                else:
                    #print >>tmpf, ":~ not correct. [9999999999@1]"
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
        if not self.updateAlg.startswith("batch"): return

        if "batch" == self.updateAlg:
            self.grbconstr += self.numFedExamples*self.grbvarSlack
            self.grbopt.addConstr(self.grbconstr >= self.grbloss, "margin")
            self.grbopt.update()

            # print >>sys.stderr, self.grbconstr
            print >>sys.stderr, self.grbopt.getConstrs()
            
            self.grbopt.reset()
            self.grbopt.optimize()
            
            bfcoef = self.coef_.copy()
            
            for i, v_i in enumerate(self.grbvars):
                self.coef_[i] = v_i.x

            print >>sys.stderr, "VAL:", self.grbconstr.getValue(), "SLACK:", self.grbvarSlack.x, "COEF:", self.coef_
            
            isConverged = np.array_equal(bfcoef, self.coef_)

            ## Needs to be checked after the update.
            ## (self.accumulatedLoss >= self.grbloss - self.numFedExamples*(self.grbvarSlack.x-self.epsilon))
            
            self.grbconstr = gp.LinExpr()
            self.grbloss   = 0
            self.numFedExamples = 0
            self.accumulatedLoss = 0
            
            return isConverged
        
        for i, v_i in enumerate(self.batch_sumFeatureVector):
            self.adagrad[i] += v_i*v_i
            
            if self.coef_[i] - self.eta/math.sqrt(1+self.adagrad[i])*v_i > 0:
                self.coef_[i] -= self.eta/math.sqrt(1+self.adagrad[i])*v_i
            
        self.batch_sumFeatureVector = np.array([0.0] * self.coef_.shape[0])

        print >>sys.stderr, "COEF:", self.coef_

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

        def loss(w, c, g):
            prior  = 0.5*np.dot(w, w)**2
            likeli = np.dot(w, c) - np.dot(w, g) + math.sqrt(len(set(goldAtoms) - set(pCurrent)))
            return max(0, prior + likeli)
        
        if self.updateAlg.startswith("batch"):
            self.numFedExamples += 1

            myloss = 0
            
            for i, v_i in enumerate(self.coef_):
                self.grbconstr += self.grbvars[i]*(vGoal[0, i] - vCurrent[0, i])
                myloss += v_i*(vCurrent[0, i] - vGoal[0, i])
                
            self.grbloss += len(set(goldAtoms) - set(pCurrent))

            # myloss = math.sqrt(len(set(goldAtoms) - set(pCurrent)))

        elif "structperc" == self.updateAlg:
            diff   = grad(loss)(self.coef_, vCurrent.toarray()[0], vGoal.toarray()[0])
            myloss = loss(self.coef_, vCurrent.toarray()[0], vGoal.toarray()[0])

            # Update the weight vector.
            for i, v_i in enumerate(diff):
                self.adagrad[i] += v_i*v_i

                if self.coef_[i] - self.eta/math.sqrt(1+self.adagrad[i])*v_i > 0:
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

            # Update the weight.
            self.coef_ = self.coef_ + tau * (g - c)

            # Make sure that the difference.
            # print >>sys.stderr, "DIFF", np.dot(self.coef_.toarray()[0], vGoal.toarray()[0]) - np.dot(self.coef_.toarray()[0], vCurrent.toarray()[0])
            # print >>sys.stderr, "LOSS", math.sqrt(len(set(goldAtoms) - set(pCurrent)))

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
