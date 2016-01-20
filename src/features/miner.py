import os
import re
import subprocess
import collections
import multiprocessing

import pandas
import itertools
import sys


def mine(fnLP, fnGold, target, verbose=False):
    args = ["/home/naoya-i/tmp/gringo-4.5.3-source/build/release/clingo",
    "-n 1",
    "-c mode=\"predict\"",
    "-c cache=\"%s\"" % fnLP.replace(".pl", ".pl.pickle"),
    ]

    p = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,)

    # Inject gold literal.
    for ln in open(fnGold):
        print >>p.stdin, "gold(%s)." % ln.strip()

    # Inject hooker.
    assert(isinstance(target, list))

    for i, t in enumerate(target):
        lf, var = t
        print >>p.stdin, "hook%s(%s) :- %s." % (
            i, var, lf,
        )

    p.stdin.write(open("/home/naoya-i/work/clone/aspinpact/data/base.pl").read())
    p.stdin.write(open("/home/naoya-i/work/clone/aspinpact/src/corenlp2asp/grimod.py").read())
    p.stdin.write(open(fnLP).read())
    p.stdin.close()

    clingoret = p.stdout.read()

    if verbose:
        print >>sys.stderr, p.stderr.read()
        print >>sys.stderr, clingoret

    return [(m.group(1), tuple(m.group(2).split(","))) for m in re.finditer("hook([0-9]+)\(([^)]+)\)", clingoret)]


def _wrapedMine(args):
    fnLP, fnGold, target = args
    return fnLP, mine(fnLP, fnGold, target) #, verbose=True)


def paraMine(args, testers, chunk=50, parallel=4):
    stat, rows = [], []
    processed = 0

    p = multiprocessing.Pool(parallel)

    for fns in itertools.izip_longest(*[iter(args)]*chunk):
        print >>sys.stderr, "\r", "[%4d/%4d] Processing..." % (processed, len(args)),
        processed += chunk

        for fn, ret in p.map(_wrapedMine, [(fn, fn.replace(".pl", ".gold.interp"), [x[1] for x in testers]) for fn in fns if None != fn]):

            dist = [""] * (1+len(testers))
            cell = collections.defaultdict(list)

            for j, instances in ret:
                cell[1+int(j)] += [",".join(instances)]

            for j in cell:
                dist[j] = "/".join(cell[j])

            dist[0] = open(fn.replace(".pl", ".txt")).read().strip()

            stat += [dist]
            rows += [os.path.basename(fn)]

    return rows, stat

if "__main__" == __name__:
    testers = eval(sys.stdin.read())
    rows, stat = paraMine(sys.argv[1:], testers)
    pf = pandas.DataFrame(
        stat,
        rows,
        ["Sentence"] + [x[0] for x in testers])
    pandas.set_option("max_colwidth", -1)
    pf.to_html(sys.stdout)
