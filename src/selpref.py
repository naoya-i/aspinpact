
import sys
import math
import os
import cdb

def _npmi(_xy, _x, _y):
	if 0 == _x*_y or 0 == _xy: return 0
	return 0.5*(1+(math.log(1.0 * _xy / (_x * _y), 2) / -math.log(_xy, 2)))

def _pmi(_xy, _x, _y):
	if 0 == _x*_y or 0 == _xy: return 0
	return math.log(1.0 * _xy / (_x * _y), 2)

def _cdbdefget(f, key, de):
	r = f.get(key)
	return r if None != r else de

class selpref_t:
	def __init__(self, pathKB="/work1/t2g-13IAM/13IAM511/extkb"):
		self.cdbTuples  = cdb.init(os.path.join(pathKB, "tuples.simple.cdb"))
		self.totalFreq = float(open(os.path.join(pathKB, "tuples.simple.totalfreq.txt")).read())

	def calc(self, p, r, a, debug=False):
		"""
		p: predicate (e.g., kill-v)
		r: role (e.g., dobj)
		a: argument (e.g., people-n-O)
		"""
		
		try:
			pxy  = int(_cdbdefget(self.cdbTuples, "%s:%s,%s" % (p, r, a), 0))
			px   = int(_cdbdefget(self.cdbTuples, "%s:%s" % (p, r), 0))
			py   = int(_cdbdefget(self.cdbTuples, "%s" % (a), 0))
		except TypeError:
			return 0.0

		if debug:
			print >>sys.stderr, " n(%s:%s,%s) = %d; \n n(%s:%s) = %d; \n n(%s) = %d" % (p, r, a, pxy, p, r, px, a, py)
			
		return _pmi(pxy/self.totalFreq, px/self.totalFreq, py/self.totalFreq), pxy


if "__main__" == __name__:
	sp = selpref_t(pathKB="/work/jun-s/kb/")
	print sp.calc(sys.argv[1], sys.argv[2], sys.argv[3], debug=True)
