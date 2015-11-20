import sys
import re

def extractBestAnswerSet(target):
    optimalAS = re.search("Optimization : (.*?)\n", target)

    if None != optimalAS:
        optimumCost = optimalAS.group(1).strip()

        for i, answerset, cost in re.findall("Answer: ([0-9]+)\n(.*?)\nOptimization: (.*?)\n", target):
            if cost == optimumCost:
                return int(optimumCost), answerset.split(" ")

def extractAnswerSets(target):
    return [(int(m.group(2)), m.group(1).split(" "))
            for m in re.finditer("Answer: [0-9]+\n(.*?)\nOptimization: (.*?)\n", target)
            ]
                
if "__main__" == __name__:
    target = open(sys.argv[1]).read()

    for ln in extractBestAnswerSet(target):
        print "\n".join(ln)
