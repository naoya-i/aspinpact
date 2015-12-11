import os
import re
import subprocess
import collections
import multiprocessing

import pandas
import itertools
import sys


def mine(fnLP, fnGold, target):
    p = subprocess.Popen(
        "/home/naoya-i/tmp/clingo-4.5.3-linux-x86_64/clingo",
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
        p.stdin.write("hook%s(%s) :- %s." % (
            i, var, lf
        ))

    # The logic program.
    for ln in open(fnLP):
        if "[f_" not in ln:
            p.stdin.write(ln)

    p.stdin.close()

    return [(m.group(1), tuple(m.group(2).split(","))) for m in re.finditer("hook([0-9]+)\(([^)]+)\)", p.stdout.read())]


def _wrapedMine(args):
    fnLP, fnGold, target = args
    return fnLP, mine(fnLP, fnGold, target)


def paraMine(args, testers, chunk=50, parallel=4):
    stat, rows = [], []
    processed = 0

    p = multiprocessing.Pool(parallel)

    for fns in itertools.izip_longest(*[iter(args)]*chunk):
        print >>sys.stderr, "\r", "[%4d/%4d] Processing..." % (processed, len(args)),
        processed += chunk

        for fn, ret in p.map(_wrapedMine, [(fn, fn.replace(".pl", ".gold.interp"), [x[1] for x in testers]) for fn in fns if None != fn]):

            dist = [""] * (1+len(testers))

            for j, instances in ret:
                dist[1+int(j)] = ",".join(instances)

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
