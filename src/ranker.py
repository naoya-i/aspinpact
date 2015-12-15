import hashlib
import random
import math
import numpy as np
import subprocess
import collections
import os
import cStringIO

from sklearn.feature_extraction import DictVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import accuracy_score
from sklearn import cross_validation

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

    def __init__(self, eta=0.01, C = 0.0001, epsilon=0.01,
                 alg="latperc", rescaling=True, normalization=True,
                 pairwise=False, report_cv=False, ignore_features=None,
    ):
        self.dv = DictVectorizer()
        self.coef_ = None
        self.coef_avg_ = []
        self.C = C
        self.eta = eta
        self.epsilon = epsilon
        self.rescaling = rescaling
        self.normalization = normalization
        self.algo = alg
        self.weightInitializer = _myinit
        self.lastInferenceTime = 0
        self.myhash = hashlib.sha1(str(random.random())).hexdigest()
        self.features = {}
        self.minmax = {}
        self.trainingExamples = []
        self.trainingLabels = []
        self.trainingHash = {}
        self.nPrevTrainingEx = 0
        self.pairwise = pairwise
        self.report_cv = report_cv

        if None != ignore_features:
            self.ignore_features = re.compile(ignore_features)
        else:
            self.ignore_features = None


    def load(self, xml, epoch = -1):
        x = etree.parse(xml)

        r = x.xpath("/root/ranker")[0]
        w = x.xpath("/root/ranker/weight/text()")[0] if -1 == epoch else x.xpath("/root/epoch/weight/text()")[epoch]
        m = x.xpath("/root/ranker/minmax/text()")[0]

        self.normalization = eval(r.attrib["normalization"])
        self.rescaling = eval(r.attrib["rescaling"])
        self.features = eval(w)
        self.minmax   = eval(m)
        self.setupFeatures()
        self.coef_    = self.dv.transform(self.features).toarray()[0]


    def serialize(self):
        xmRanker = etree.Element("ranker",
                                 normalization="%s" % self.normalization,
                                 rescaling="%s" % self.rescaling,
        )

        xmMinmax = etree.Element("minmax")
        xmRanker.append(xmMinmax)
        xmMinmax.text = repr(self.minmax)

        xmWeight = etree.Element("weight")
        xmRanker.append(xmWeight)
        xmWeight.text = repr(self.dv.inverse_transform(self.coef_)[0])

        return xmRanker


    def setupFeatures(self):
        self.dv.fit([self.features])
        dvfns = self.dv.get_feature_names()
        self.coef_ = np.array([0.0]*len(self.features.keys()))

        for i in xrange(self.coef_.shape[0]):
            self.coef_[i] = 1 # self.weightInitializer(i)

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


    def predict(self, lpfiles, cache_file, goldAtoms=[], weight=None, lossAugmented=False,
                exclude=False, enum=False, eco=False, maximize=True, generationOnly=False):
        assert(isinstance(lpfiles, list))

        if weight is None:
            weight = self.coef_ if maximize else -self.coef_

        args = ["/home/naoya-i/tmp/gringo-4.5.3-source/build/release/clingo",
        "-n 0",
        "--opt-mode=optN" if not enum else "--opt-mode=enum",
        ]

        if generationOnly:
            args = ["/home/naoya-i/tmp/gringo-4.5.3-source/build/release/gringo",
            "-t",
            ]

        args += ["-c mode=\"predict\"", "-c cache=\"%s\"" % cache_file,
        "/home/naoya-i/work/clone/aspinpact/src/corenlp2asp/grimod.py",
        ] + lpfiles

        pClingo = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )

        pClingo.stdin.close()

        clingoret = pClingo.stdout.read()
        clingoerr = pClingo.stderr.read()

        if generationOnly:
            print >>sys.stderr, clingoerr
            return clingoret.split("\n")

        print >>sys.stderr, clingoret

        # Generate feature-weighted answer set program.
        # tmpf = cStringIO.StringIO()
        #
        # for fn in lpfiles:
        #     for ln in open(fn):
        #         m = regexWeakConstraint.search(ln)
        #
        #         if None == m:
        #             print >>tmpf, ln.strip()
        #             continue
        #
        #         # To record feature vector.
        #         constraint, fname, fvalue, binder = m.group(1).strip(), \
        #                                             m.group(2).strip(), \
        #                                             float(m.group(3).strip()), \
        #                                             ",".join(m.group(4).split(",")[1:]).strip()
        #
        #         if not self.dv.vocabulary_.has_key(fname) or \
        #             (None != self.ignore_features and None != self.ignore_features.search(fname)):
        #
        #             print >>tmpf, "%% LOST: %s" % (ln.strip())
        #
        #         else:
        #             fidx = self.dv.vocabulary_[fname]
        #             fvalue = self.rescale(fname, fvalue)
        #
        #             print >>tmpf, "%% %.3f x %f" % (weight[fidx], fvalue)
        #
        #             if not eco:
        #                 print >>tmpf, "f_%s(%s, %s) :- %s" % (fname, _sanitize(fvalue), binder, constraint)
        #                 print >>tmpf, ":~ f_%s(%s, %s). [%d@1, f_%s, %s]" % (
        #                     fname, _sanitize(fvalue), binder,
        #                     int(-RESOLUTION*weight[fidx]*fvalue), fname, binder)
        #
        #             else:
        #                 # If we do not have to recover the feature vector, then.
        #                 print >>tmpf, ":~ %s [%d@1, f_%s, %s]" % (
        #                     constraint,
        #                     int(-RESOLUTION*weight[fidx]*fvalue), fname, binder)
        #
        #
        # # Constrain the answer set space to one including gold atoms.
        # if len(goldAtoms) > 0:
        #     if lossAugmented:
        #         for a in goldAtoms:
        #             print >>tmpf, ":~ not %s. [-1@1, lossaug_%s]" % (a, re.sub("[\(\),]", "_", a))
        #
        #     else:
        #         print >>tmpf, "correct :- %s." % (", ".join([a for a in goldAtoms]))
        #
        #         if exclude: print >>tmpf, ":- correct."
        #         else:       print >>tmpf, ":- not correct."
        #
        # print >>tmpf, "dummy_always_ensures_optimization."
        # print >>tmpf, ":~ dummy_always_ensures_optimization. [0@1]"
        #
        # if generationOnly:
        #     print tmpf.getvalue()
        #     return []
        #
        # # Use clingo to get the prediction. The constructed ASP is given by a standard input.
        # pClingo = subprocess.Popen(
        #     ["/home/naoya-i/tmp/clingo-4.5.3-linux-x86_64/clingo",
        #      "-n 0",
        #      "--opt-mode=optN" if not enum else "--opt-mode=enum",
        #      ],
        #     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        #     stdin=subprocess.PIPE,
        # )
        # pClingo.stdin.write(os.popen("grep -v ':~.*\[.*wf.*\]' /home/naoya-i/work/clone/aspinpact/data/theory.pl").read())
        # pClingo.stdin.write(tmpf.getvalue())
        # pClingo.stdin.close()
        #
        # clingoret = pClingo.stdout.read()
        # clingoerr = pClingo.stderr.read()
        #
        # m = re.findall("Time         : ([0-9.]+)", clingoret)
        #
        # if len(m) > 0:
        #     self.lastInferenceTime = float(m[0])

        if enum:
            return [answer_set_t(-1.0*c/RESOLUTION, a) for c, a in extractAnswerSets(clingoret)]

        return [answer_set_t(-1.0*c/RESOLUTION, a) for c, a in extractBestAnswerSets(clingoret)]


    def fit(self):
        if self.algo in ["batch", "iterative"]:
            if self.nPrevTrainingEx == len(self.trainingExamples):
                return True

            self.nPrevTrainingEx = len(self.trainingExamples)

            m = LinearSVC(C=self.C, max_iter=100000, fit_intercept=True, verbose=True)

            if self.report_cv:
                cvs = cross_validation.cross_val_score(m, self.trainingExamples, self.trainingLabels, cv=5)
                print >>sys.stderr, "CV:", sum(cvs) / len(cvs)

            m.fit(self.trainingExamples, self.trainingLabels)
            self.coef_ = m.coef_[0]
            self.m = m

            print >>sys.stderr, "Closed discriminative power (acc.):", accuracy_score(self.trainingLabels, m.predict(self.trainingExamples))

            if "batch" == self.algo:
                return True

            return False

        self.coef_avg_ += [self.coef_.copy()]
        self.coef_ = self.getAveragedWeight()
        return False


    def feed(self, x, y):
        h = hashlib.sha1(repr(x)).hexdigest()

        if self.trainingHash.has_key(h):
            return

        self.trainingExamples += [x]
        self.trainingLabels += [y]
        self.trainingHash[h] = None


    def poke(self, aspfiles, goldAtoms):

        _enum  = self.algo == "batch"
        sp, sn = -99999, -99999
        ret    = []

        if self.pairwise:
            for posi in self.predict(aspfiles, goldAtoms, exclude=False, maximize=True, enum=_enum):
                for nega in self.predict(aspfiles, goldAtoms, exclude=True,  maximize=True, enum=_enum):
                    ret += [(self.getFeatureVector(posi.answerset).toarray()[0] - self.getFeatureVector(nega.answerset).toarray()[0], 1)]
                    ret += [(self.getFeatureVector(nega.answerset).toarray()[0] - self.getFeatureVector(posi.answerset).toarray()[0], -1)]
                    sp = max(sp, posi.score)
                    sn = max(sn, nega.score)

        else:
            for posi in self.predict(aspfiles, goldAtoms, exclude=False, maximize=True, enum=_enum):
                ret += [(self.getFeatureVector(posi.answerset).toarray()[0], 1)]
                sp = max(sp, posi.score)
                self.lastPosi = posi

            for nega in self.predict(aspfiles, goldAtoms, exclude=True,  maximize=True, enum=_enum):
                ret += [(self.getFeatureVector(nega.answerset).toarray()[0], -1)]
                sn = max(sn, nega.score)
                self.lastNega = nega

        if sp == -99999 or sn == -99999:
            return answerset_ranker_t.NO_LVC, 0.0, ret

        return answerset_ranker_t.UPDATED, max(0, sn-sp), ret


#
# Helper functions.
def _sanitize(f):
    return "v_%s" % (str(f).replace(".", "D").replace("-", "M"))

def _drink(f):
    return f.replace("D", ".").replace("M", "-")[2:]

def _myinit(fidx):
    return 1
    random.seed(fidx)
    return 0.001*random.random()
