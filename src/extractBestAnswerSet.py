import sys
import re

def extractBestAnswerSets(target):
    optimalAS = re.search("Optimization : (.*?)\n", target)
    ret       = []

    if None != optimalAS:
        optimumCost = optimalAS.group(1).strip()

        for i, answerset, cost in re.findall("Answer: ([0-9]+)\n(.*?)\nOptimization: (.*?)\n", target):
            if cost == optimumCost:
                ret += [(int(optimumCost), answerset.split(" "))]

    return ret

def extractAnswerSets(target):
    return [(int(m.group(2)), m.group(1).split(" "))
            for m in re.finditer("Answer: [0-9]+\n(.*?)\nOptimization: (.*?)\n", target)
            ]

if "__main__" == __name__:
    target = open(sys.argv[1]).read()

    for ln in extractBestAnswerSet(target):
        print "\n".join(ln)
