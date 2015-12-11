
import readline
import subprocess

import math
import os

import cdb
import mmap
import struct

import sys

def _getCosineSimilarity(v1, v2):
	sim = 0.0
	toV1, toV2 = 0, 0

	assert(len(v1) == len(v2))

	for i in xrange(len(v1)):
		sim += v1[i] * v2[i]
		toV1 += v1[i]**2
		toV2 += v2[i]**2

	if 0.0 == toV1 or 0.0 == toV2:
		return -1
		
	sim /= math.sqrt(toV1)*math.sqrt(toV2)

	return sim

class synonym_finder_t:
	def __init__(self, path = "/work/naoya-i/kb"):
		self.procServer = subprocess.Popen(
			"%s -k %s -w %s" % (
				os.path.join(os.path.join(os.path.dirname(sys.argv[0]), "../bin"), "word2vec_simsearch"),
				path,
				"./data/wnentries.txt",
			),
			shell = True,
			stdin = subprocess.PIPE, stdout = subprocess.PIPE,
			)

		assert("200 OK" == self.procServer.stdout.readline().strip())

	def getSynonyms(self, word, K = 10):
		print >>self.procServer.stdin, "K", K
		print >>self.procServer.stdin, word

		numResults = int(self.procServer.stdout.readline())

		print numResults
		
		for i in xrange(numResults):
			yield self.procServer.stdout.readline().strip().split("\t")
		
class word2vecsim_t:
	DIMENSION = 300
	
	def __init__(self, path = "/work/naoya-i/kb/"):
		self.w2vi = cdb.init(os.path.join(path, "GoogleNews-vectors-negative300.index.cdb"))
		self.w2vf = open(os.path.join(path, "GoogleNews-vectors-negative300.bin"), "rb")
		self.w2vdb = mmap.mmap(self.w2vf.fileno(), 0, prot=mmap.PROT_READ)

	def getWordVector(self, ent):
		ret = self.w2vi.get(ent)

		if None == ret: return [0.0]*word2vecsim_t.DIMENSION
		
		iStart, iLen = ret.split("\t")
		binVec       = self.w2vdb[int(iStart):int(iStart)+int(iLen)]

		try:
			return struct.unpack("f"*word2vecsim_t.DIMENSION, binVec[len(ent)+1:])
		except struct.error:
			return [0.0]*word2vecsim_t.DIMENSION
	
	def calc(self, w1, w2):
		if w1 == w2:
			return 1
			
		v1, v2 = self.getWordVector(w1), self.getWordVector(w2)
		return 0.5*(1+_getCosineSimilarity(v1, v2))

if "__main__" == __name__:
	
	synonymFinder = None, 
	
	while True:
		x = raw_input("? ")
	
	for word in sim.getSynonyms(sys.argv[1]):
		print word
	
	sim = word2vecsim_t()
	print sim.calc(sys.argv[1], sys.argv[2])
