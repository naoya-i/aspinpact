
import os
import csv
import sys

class gender_t:
    def __init__(self, fn_genderdb = None):
        self.db = {}
        self.dbProb = {}

        if None != fn_genderdb:
            for row in csv.reader(os.popen("zcat %s" % fn_genderdb), delimiter="\t"):
                masc, fem, neu, pl = [int(x) for x in row[1].split(" ")]                

                gen = "neutral"
                
                if masc == max(masc, fem, neu): gen = "male"
                if fem  == max(masc, fem, neu): gen = "female"
                if neu  == max(masc, fem, neu): gen = "neutral"
                
                self.db[row[0]] = gen
                self.dbProb[row[0]] = masc, fem, neu


    def diet(self, fn_genderdb, fn_to, freq = 1):
        with open(fn_to, "w") as out:
            for row in csv.reader(os.popen("zcat %s" % fn_genderdb), delimiter="\t"):
                if sum([int(x) for x in row[1].split(" ")]) >= freq:
                    print >>out, "\t".join(row)

                    
    def getGender(self, n):
        return self.db.get(n.lower(), "neutral")

        
    def getGenderProb(self, n):
        return self.dbProb.get(n.lower(), (0, 0, 0))
        

