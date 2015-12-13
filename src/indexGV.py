
from progressbar import progressbar_t

import struct
import sys

gbin			 = open(sys.argv[1], "rb")
ln				 = gbin.readline()
nWords		 = int(ln.split(" ")[0])
nDimension = int(ln.split(" ")[1])
bytesRead  = len(ln)
pb				 = progressbar_t(nWords)

for i in xrange(nWords):
	pb.progress()
	
	# READ THE WORD.
	word = []
	
	while True:
		word += [gbin.read(1)]
		
		if None == word[-1] or " " == word[-1]:
			break

	if None == word[-1]:
		break

	# READ THE BINARY VECTOR.
	vec = gbin.read(4*nDimension)
	
	sys.stdout.write("\t".join(["".join(word[:-1]), struct.pack("QH", bytesRead, len(word)+4*nDimension)]))

	# GO TO NEXT ENTRY
	bytesRead += len(word) + 4*nDimension
	
