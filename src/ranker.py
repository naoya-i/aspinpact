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
from lxml import etree

RESOLUTION = 10000

#
# External helper functions.
def readGoldAtoms(fn):
    return [x.strip() for x in open(fn)]

    
class answer_set_t:
    def __init__(self, score, answerset):
        self.score = score
        self.answerset = answerset

        
class answerset_ranker_t:
    CORRECT = 0
    NO_LVC  = 1
    UPDATED = 2
    INDISTINGUISHABLE = 3
    CANNOT_PREDICT = 4

    def __init__(self, eta=0.01, C = 0.0001, epsilon=0.01, alg="latperc", rescaling=True,
                 normalization=True,
    ):
        self.dv = DictVectorizer()
        self.coef_ = None
        self.coef_avg_ = []
        self.C = C
        self.eta = eta
        self.epsilon = epsilon
        self.rescaling = rescaling
        self.normalization = normalization
        self.updateAlg = alg
        self.weightInitializer = _myinit
        self.lastInferenceTime = 0
        self.myhash = hashlib.sha1(str(random.random())).hexdigest()
        self.features = {}
        self.minmax = {}
        

    def load(self, xml, epoch = -1):
        x = etree.parse(xml)

        w = x.xpath("/root/ranker/weight/text()")[0] if -1 == epoch else x.xpath("/root/epoch/weight/text()")[epoch]
        m = x.xpath("/root/ranker/minmax/text()")[0]
        
        self.features = eval(w)
        self.minmax   = eval(m)
        self.setupFeatures()
        self.coef_    = self.dv.transform(self.features).toarray()[0]
        

    def serialize(self):
        xmRanker = etree.Element("ranker")

        xmMinmax = etree.Element("minmax")
        xmRanker.append(xmMinmax)
        xmMinmax.text = repr(self.minmax)

        xmWeight = etree.Element("weight")
        xmRanker.append(xmWeight)
        xmWeight.text = repr(self.dv.inverse_transform(self.coef_)[0])
        
        return xmRanker
        
        
    def setupFeatures(self):
        self.dv.fit([self.features])
        self.coef_ = np.array([0.0]*len(self.features.keys()))

        for i in xrange(self.coef_.shape[0]):
            self.coef_[i] = self.weightInitializer(i)

        self.coef_avg_ += [self.coef_.copy()]


    def collectFeatures(self, fn):
        for ln in open(fn):
            m = re.search("\[f_(.*?)\(([-0-9e.]+)\)@", ln)

            if None != m:
                self.features[m.group(1)] = 0
                self.minmax[(m.group(1), "max")] = max(self.minmax.get((m.group(1), "max"), 0), float(m.group(2)))
                self.minmax[(m.group(1), "min")] = min(self.minmax.get((m.group(1), "min"), 0), float(m.group(2)))

                
    def rescale(self, fname, fvalue):
        if not self.rescaling:
            return fvalue
            
        return 1.0 * \
            (fvalue - self.minmax[(fname, "min")]) / \
            (self.minmax[(fname, "max")] - self.minmax[(fname, "min")])


    def normalize(self, v):
        if not self.normalization:
            return v

        return v / np.linalg.norm(v.toarray()[0])

        
    def getAveragedWeight(self):
        avgWeight = np.array([0.0]*self.coef_.shape[0])

        for w_t in self.coef_avg_:
            avgWeight += w_t

        return avgWeight/len(self.coef_avg_)
        
                
    def getFeatureVector(self, answerset):
        vec = collections.defaultdict(float)
        regexWeakConstraint = re.compile("f_(.*?)\((.*?),")

        for a in answerset:
            m = regexWeakConstraint.search(a)

            if None != m:
                fname, fvalue = m.group(1), self.rescale(m.group(1), float(_drink(m.group(2))))
                vec[fname] += 1.0 * fvalue

        vec = self.dv.transform(vec)
        
        return self.normalize(vec)

        
    def predict(self, lpfiles, goldAtoms=[], weight=None, lossAugmented=False, exclude=False, enum=False, eco=False):
        regexWeakConstraint = re.compile(":~(.*?)\[f_(.*?)\(([-0-9.e]+)\)@(.*?)\]")

        if weight is None: weight = self.coef_
        
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

                    if not self.dv.vocabulary_.has_key(fname):
                        print >>tmpf, "%% LOST: %s" % (ln.strip())

                    else:
                        fidx = self.dv.vocabulary_[fname]
                        fvalue = self.rescale(fname, fvalue)

                        print >>tmpf, "%% %.3f x %f" % (weight[fidx], fvalue)

                        if not eco:
                            print >>tmpf, "f_%s(%s, %s) :- %s" % (fname, _sanitize(fvalue), binder, constraint)
                            print >>tmpf, ":~ f_%s(%s, %s). [%d@1, %s]" % (
                                fname, _sanitize(fvalue), binder,
                                int(-RESOLUTION*weight[fidx]*fvalue), binder)

                        else:
                            # If we do not have to recover the feature vector, then.
                            print >>tmpf, ":~ %s [%d@1, %s]" % (
                                constraint,
                                int(-RESOLUTION*weight[fidx]*fvalue), binder)
                        
                else:
                    print >>tmpf, ln.strip()

        # Constrain the answer set space to one including gold atoms.
        if len(goldAtoms) > 0:
            if lossAugmented:
                for a in goldAtoms:
                    print >>tmpf, ":~ not %s. [-1@1, lossaug_%s]" % (a, re.sub("[\(\),]", "_", a))
                    
            else:
                print >>tmpf, "correct :- %s." % (", ".join([a for a in goldAtoms]))

                if exclude: print >>tmpf, ":- correct."
                else:       print >>tmpf, ":- not correct."

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
            return [answer_set_t(-1.0*c/RESOLUTION, a) for c, a in extractAnswerSets(clingoret)]
        
        return [answer_set_t(-1.0*c/RESOLUTION, a) for c, a in extractBestAnswerSets(clingoret)]


    def fit(self):
        self.coef_avg_ += [self.coef_.copy()]
        self.coef_ = self.getAveragedWeight()
        return False
        

    def feed(self, aspfiles, goldAtoms):

        # First, guess what.
        predictions = self.predict(aspfiles)

        if 0 == len(predictions):
            return answerset_ranker_t.CANNOT_PREDICT, 0.0

        pcur = predictions[0]
        
        # Is the guess correct?
        if set(goldAtoms).issubset(set(pcur.answerset)):
            return answerset_ranker_t.CORRECT, 0.0

        # Guess correct label.
        goals = self.predict(aspfiles, goldAtoms)

        # Find answer set containing gold atoms.
        if 0 == len(goals):
            return answerset_ranker_t.NO_LVC, 0.0

        pgoal = goals[0]

        # If it is not inferred, then give up.
        assert(not set(goldAtoms).issubset(set(pcur.answerset)))
        assert(set(goldAtoms).issubset(set(pgoal.answerset)))

        return self._updateWeights(pcur.answerset, pgoal.answerset, goldAtoms)

        
    def _updateWeights(self, pCurrent, pGoal, goldAtoms):
        vCurrent, vGoal = self.getFeatureVector(pCurrent), self.getFeatureVector(pGoal)
        
        if "latperc" == self.updateAlg:
            self.coef_ += (vGoal - vCurrent).toarray()[0]

            return answerset_ranker_t.UPDATED, len(set(goldAtoms) - set(pCurrent))
            
        elif self.updateAlg in ["PA-I", "PA-II"]:
            w, c, g = self.coef_, vCurrent.toarray()[0], vGoal.toarray()[0]
            diff    = g - c
            loss = np.dot(w, c) - np.dot(w, g) + math.sqrt(len(set(goldAtoms) - set(pCurrent)))
            norm2 = np.linalg.norm(diff) ** 2

            if norm2 == 0.0:
                return answerset_ranker_t.INDISTINGUISHABLE, 0.0 # Cannot update.

            if "PA-I" == self.updateAlg:    tau = min(self.C, loss / norm2)
            elif "PA-II" == self.updateAlg: tau = loss / (norm2 + 1.0/(2*self.C))

            # Update the weights.
            self.coef_ = self.coef_ + tau * diff

            return answerset_ranker_t.UPDATED, loss

        raise "Unsupported algorithm: %s" % self.updateAlg

#
# Helper functions.
def _sanitize(f):
    return "v_%s" % (str(f).replace(".", "D").replace("-", "M"))

def _drink(f):
    return f.replace("D", ".").replace("M", "-")[2:]

def _myinit(fidx):
    random.seed(fidx)
    return 0.001*random.random()

    
