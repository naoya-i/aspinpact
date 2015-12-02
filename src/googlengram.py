
import sys
import cdb
import os

class googlengram_t:
	TOTAL = 1024908267229
	
	def __init__(self, path = "/work/jun-s/kb/ngrams"):
		self.path   = path

		self.idx  = {}
		self.idx[2] = map(lambda x: x.strip().split("\t"), open(os.path.join(path, "2gm.idx")))
		self.idx[3] = map(lambda x: x.strip().split("\t"), open(os.path.join(path, "3gm.idx")))
		self.idx[4] = map(lambda x: x.strip().split("\t"), open(os.path.join(path, "4gm.idx")))

	def getFile(self, ngram):
		"""
		ngram: ["a", "movie"]; the length of list should be less than 5.
		"""
		assert(isinstance(ngram, list))
		assert(len(ngram) < 5)
		
		if 1 >= len(ngram):
			return "1gm.cdb"

		else:
			for archive, pat in reversed(self.idx[len(ngram)]):
				if pat <= " ".join(ngram):
					return archive

	def search(self, ngram):
		"""
		ngram:
		"""
		assert(isinstance(ngram, list))
		assert(len(ngram) < 5)

		db = cdb.init(os.path.join(self.path, self.getFile(ngram).replace(".gz", ".cdb")))

		try:
			return int(db.get(" ".join(ngram)))

		except TypeError:
			return 0

	def getProb(self, ngram):
		return 1.0 * self.search(ngram) / googlengram_t.TOTAL
		
if "__main__" == __name__:
	ng = googlengram_t()

	print ng.getFile(sys.argv[1:])
	print ng.getProb(sys.argv[1:])
	
