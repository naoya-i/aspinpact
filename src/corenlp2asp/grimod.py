
#script (python)

import sys
sys.path += ["%s" % "/home/naoya-i/work/clone/aspinpact/src"]

import cPickle

def _floatToInt(x): return int(10000*x) if isinstance(x, float) else x

class grimod_t:
    Cache = "cache"
    Predict = "predict"

    def __init__(self, mode=Cache):
        self.cache = {}
        self.mode  = mode


    def extfunc(self, fun):
        if grimod_t.Cache == self.mode:
            self.cache[(fun.name(), tuple(fun.args()))] = 0

        if grimod_t.Predict == self.mode:
            return self.cache.get((fun.name(), tuple(fun.args())), [])

        return []


    def featfunc(self, fun):
        if grimod_t.Cache == self.mode:
            self.cache[(fun.name(), tuple(fun.args()))] = 0

        if grimod_t.Predict == self.mode:
            return _floatToInt(self.cache.get((fun.name(), tuple(fun.args())), 0))

        return 0

#
# For gringo main entry point.
g_app = None

def main(prg):
    mode, cache = prg.get_const("mode"), prg.get_const("cache")

    print >>sys.stderr, "INPACT Grounder."
    print >>sys.stderr, "  mode: %s" % mode
    print >>sys.stderr, "  cache: %s" % cache

    global g_app
    g_app = grimod_t(mode)

    if "predict" == mode:
        g_app.cache = cPickle.load(open(cache))

    prg.ground([("base", [])])

    if "cache" == mode:

        # Output the call history as a cache.
        sys.stdout.write("RESULT: " + cPickle.dumps(g_app.cache, protocol=1))

    if "predict" == mode:
        prg.solve()


def extfunc(fun):
    return g_app.extfunc(fun)

def featfunc(fun):
    return g_app.featfunc(fun)

def invsenti(fun):
    if "p" == fun: return "n"
    if "n" == fun: return "p"

    return "0"

#end.
