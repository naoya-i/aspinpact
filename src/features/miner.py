import os
import re
import subprocess
import collections
import multiprocessing


def mine(fnLP, fnGold, target):
    p = subprocess.Popen(
        "/home/naoya-i/tmp/clingo-4.5.3-linux-x86_64/clingo",
        stdout=subprocess.PIPE,
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


def paraMine(args, testers, chunk=50, parallel=4):
    stat = [[] for i in xrange(len(testers))]

    p = multiprocessing.Pool(parallel)

    processed = 0

    for fns in itertools.izip_longest(*[iter(args)]*chunk):
        print >>sys.stderr, "\r", "[%4d/%4d] Processing..." % (processed, len(args)),
        processed += chunk

        for i, ret in p.map(mine, [(fn[0], fn[1], x[1]) for fn in args if None != fn]):
            stat[int(i)] += 1 # [os.path.basename(fn.split("_")[1][:-3])]

    return stat
