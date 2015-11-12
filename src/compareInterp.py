import sys

goldAtoms = [x.strip() for x in open(sys.argv[1])]
sysAtoms  = [x.strip() for x in open(sys.argv[2])]

for atom in goldAtoms:
    if atom in sysAtoms:
        print "OK",
    else:
        print "NG",

    print atom
