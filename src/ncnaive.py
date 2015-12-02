
import cdb
import collections
import math

import sys
import itertools
import re

def _pmi(_xy, _x, _y):
	if 0 == _x*_y or 0 == _xy: return 0
	return math.log(1.0 * _xy / (_x * _y), 2)

def _npmi(xy, x, y):
	if xy != 0:
		return 0.5*(1+(math.log(1.0 * xy / (x * y), 2) / -math.log(xy, 2)))
	else:
		return 0
	
def _cdbdefget(f, key, de):
	r = f.get(key)
	return r if None != r else de

class ncnaive_t:
	def __init__(self, db1, db2):
		self.cdb = cdb.init(db1)
		self.cdbPreds = cdb.init(db2)
		# self.totalFreqPreds = int(open(db2.replace(".cdb", ".totalfreq.txt")).read())
                self.totalFreqPreds = int(open(db2.replace(".tuples.cdb", ".totalfreq.txt")).read())

	def getFreq(self, pr1, pr2):
		f = self.cdb.get("%s ~ %s" % ((pr1, pr2) if pr1 < pr2 else (pr2, pr1)))
		return int(f) if None != f else 0

        def getFreqPred(self, pr1):
                f = _cdbdefget(self.cdbPreds, pr1, 0)
		# f = self.cdb.get("%s ~ %s" % ((pr1, pr2) if pr1 < pr2 else (pr2, pr1)))
		return int(f) if None != f else 0

	def getPMI(self, pr1, pr2, discount=1.0):
		x, y = float(_cdbdefget(self.cdbPreds, pr1, 0)), float(_cdbdefget(self.cdbPreds, pr2, 0))
		xy = float(_cdbdefget(self.cdb, "%s ~ %s" % ((pr1, pr2) if pr1 < pr2 else (pr2, pr1)), 0))
		
		return _pmi(xy/(self.totalFreqPreds*discount), x/self.totalFreqPreds, y/self.totalFreqPreds)

	def getNPMI(self, pr1, pr2, discount=1.0):
		x, y = float(_cdbdefget(self.cdbPreds, pr1, 0)), float(_cdbdefget(self.cdbPreds, pr2, 0))
		xy   = float(_cdbdefget(self.cdb, "%s ~ %s" % ((pr1, pr2) if pr1 < pr2 else (pr2, pr1)), 0))

                return _npmi(xy/(self.totalFreqPreds * discount), x/self.totalFreqPreds, y/self.totalFreqPreds)

	# def getFreqbit(self, pr1, pr2, bit):
	# 	f = self.cdb.get("%s ~ %s ~ %s" % ((pr1, pr2, bit) if pr1 < pr2 else (pr2, pr1, bit)))
	# 	return int(f) if None != f else 0

	# def getPMIbit(self, pr1, pr2, bit, discount=1.0):
	# 	x, y = float(_cdbdefget(self.cdbPreds, "%s ~ %s" %(pr1, bit), 0)), float(_cdbdefget(self.cdbPreds, "%s ~ %s" %(pr2, bit), 0))
	# 	xy = float(_cdbdefget(self.cdb, "%s ~ %s ~ %s" % ((pr1, pr2, bit) if pr1 < pr2 else (pr2, pr1, bit)), 0))
		
	# 	return _pmi(xy/(self.totalFreqPreds*discount), x/self.totalFreqPreds, y/self.totalFreqPreds)

	# def getNPMIbit(self, pr1, pr2, bit, discount=1.0):
	# 	x, y = float(_cdbdefget(self.cdbPreds, "%s ~ %s" %(pr1, bit), 0)), float(_cdbdefget(self.cdbPreds, "%s ~ %s" %(pr2, bit), 0))
	# 	xy   = float(_cdbdefget(self.cdb, "%s ~ %s ~ %s" % ((pr1, pr2, bit) if pr1 < pr2 else (pr2, pr1, bit)), 0))
		
	# 	return _npmi(xy/(self.totalFreqPreds * discount), x/self.totalFreqPreds, y/self.totalFreqPreds)

                
if "__main__" == __name__:
	nc = ncnaive_t("/work/naoya-i/kb/ncnaive0909.0.cdb", "/work/jun-s/kb/tuples.0909.tuples.cdb")
	print nc.getFreq(sys.argv[1], sys.argv[2])
	print nc.getPMI(sys.argv[1], sys.argv[2])
