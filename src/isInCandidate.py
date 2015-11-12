import sys
import re

target    = open(sys.argv[2]).read()
goldAtoms = [x.strip() for x in open(sys.argv[1])]

for atom in goldAtoms:
    for i, answerset, cost in re.findall("Answer: ([0-9]+)\n(.*?)\nOptimization: (.*?)\n", target):
        if atom in answerset.split(" "):
            print "OK",
            break

    else:
        print "NG",

    print atom
