import sys
import re

target = open(sys.argv[1]).read()

optimalAS = re.search("Optimization : (.*?)\n", target)

if None != optimalAS:
    optimumCost = optimalAS.group(1).strip()

    for i, answerset, cost in re.findall("Answer: ([0-9]+)\n(.*?)\nOptimization: (.*?)\n", target):

        if cost == optimumCost:
            print answerset.replace(" ", "\n")
            break
