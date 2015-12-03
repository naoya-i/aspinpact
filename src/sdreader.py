
import re
import collections

POS   = 0
LEMMA = 1
NER   = 2

POS_PREDICATE = "VB VBD VBG VBN VBP VBZ JJ JJR JJS".split()
POS_NOUN = "NN NNS NNP NNPS PRP PRPS".split()
LINKING_VERB_TOINF = "appear seem".split()

regexRelsDetector = re.compile("root.*?\n\n", re.DOTALL)
regexRelDetector = re.compile("([^(]+)\(.*?-([0-9]+)'*, .*?-([0-9]+)'*\)\n")
regexTokenDetector = re.compile("Text=([^ ]+) .*?PartOfSpeech=([^ ]+) Lemma=([^ ]+) NamedEntityTag=([^\] ]+)")
regexCorefDetector = re.compile("\t\(([0-9]+),([0-9]+),\[([0-9]+),([0-9]+)\]\) -> \(([0-9]+),([0-9]+),\[([0-9]+),([0-9]+)\]\), that is: \"([^\"]+)\" -> \"([^\"]+)\"\n")

class token_t:
	def __init__(self, id, surf, pos, lemma, ne):
		self.id    = id
		self.surf  = surf
		self.pos   = pos
		self.lemma = lemma
		self.ne    = ne

	def __repr__(self):
		return "%s/%s" % (self.lemma, self.pos)


def createTokenFromLXML(x):
	_gettext = lambda e, name: e.xpath("./%s/text()" % name)[0]
	return token_t(int(x.attrib["id"])-1, _gettext(x, "word"), _gettext(x, "POS"), _gettext(x, "lemma"), _gettext(x, "NER"))


class rel_t:
	def __init__(self, rel, tk_from, tk_to, extra = "-"):
		self.rel     = rel
		self.tk_from = tk_from # Governor.
		self.tk_to   = tk_to   # Dependent.
		self.extra   = extra

	def toString(self, doc):
		return "%s(%s,%s)" % (self.rel, doc.tokens[self.tk_from].lemma, doc.tokens[self.tk_to].lemma)


def createRelFromLXML(x):
	_getattrib = lambda e, name, attrib: e.xpath("./%s/@%s" % (name, attrib))[0]
	return rel_t(x.attrib["type"], int(_getattrib(x, "governor", "idx"))-1, int(_getattrib(x, "dependent", "idx"))-1)


class coref_mention_t:
	def __init__(self, head_x, head_y, start, end, surf):
		self.head_x = head_x
		self.head_y = head_y
		self.start  = start
		self.end    = end
		self.surf   = surf

class doc_t:
	def __init__(self, id, rawtext, tokens, rels, corefs):
		self.id      = id
		self.rawtext = rawtext
		self.tokens  = tokens
		self.rels    = rels
		self.corefs  = corefs

	def hasRel(self, r, tk_from, tk_to):
		for rel in self.rels:
			if None != re.match(r, rel.rel) and rel.tk_from == tk_from and rel.tk_to == tk_to:
				return True

		return False

	def hasRelWith(self, r, tk_from, tk_to_lemma = "*"):
		for rel in self.rels:
			if (r == "*" or None != re.match(r, rel.rel)) and rel.tk_from == tk_from and (tk_to_lemma == "*" or self.tokens[rel.tk_to].lemma == tk_to_lemma):
				return True

		return False

	def findRels(self, r, tk_from, tk_to):
		for rel in self.rels:
			if None != re.match(r, rel.rel) and (-1 == tk_from or rel.tk_from == tk_from) and (-1 == tk_to or rel.tk_to == tk_to):
				yield rel

	def getRelationIndex(self, rel, tk):
	    if "VBN" == tk.pos and "pass" not in rel and "prep" in rel:

	        #
	        # Case like: It is based on X. auxpass(base, be)
	        for beverb in self.findRels("auxpass", tk.id, -1):
	            if self.tokens[beverb.tk_to].lemma == "be":
	                rel += "_pass"
	                break

	        else:
	            # Case like: I bought a camera made in X. vmod(camera, made)
	            for modifiedNoun in self.findRels("vmod", -1, tk.id):
	                if self.tokens[modifiedNoun.tk_from].pos.startswith("NN"):
	                    rel += "_pass"
	                    break

	    if "agent" == rel: rel = "nsubj"

	    return rel

	def getEventIndex(self, tk, lv):
	    if tk.pos in POS_PREDICATE:

	        # Phrase-based indexing.
	        if tk.lemma == "be":
	            # "X is from..." => be_from
	            for rel in self.findRels("prepc?_.*", tk.id, -1):
	                return "be_%s" % rel.rel[rel.rel.index("_")+1:]

	        else:
	            # A phrase identified by SCNLP.
	            # put on => put_on
	            ret = [tk.lemma]

	            for rel in self.findRels("prt", tk.id, -1):
	                ret += [self.tokens[rel.tk_to].lemma]

	            return "_".join(ret)

	        # Linking verbs-based indexing.
	        if lv.isLinkingVerb(tk.lemma):

	            # She seems bad. xcomp(seem,bad)
	            for rel in self.findRels("xcomp", tk.id, -1):

	                # Some special patterns.
	                if tk.lemma in LINKING_VERB_TOINF and self.tokens[tk.id+1].lemma == "to":
	                    if self.tokens[tk.id+2].lemma == "be":
	                        # It seems to be an important thing.
	                        template = "%s_to_be_%s"

	                    else:
	                        # It seems to accomplish.
	                        template = "%s_to_%s"

	                    return template % (tk.lemma, self.tokens[rel.tk_to].lemma)

	                else:
	                    # Make sure there is no "to".
	                    # e.g., they get a chance to develop.
	                    if not self.hasRelWith(".*", rel.tk_to, "to"):
	                        return "%s_%s" % (tk.lemma, self.tokens[rel.tk_to].lemma if self.tokens[rel.tk_to].pos.startswith("NN") else self.tokens[rel.tk_to].surf)

	        return tk.lemma

	    if tk.pos in POS_NOUN and self.hasRelWith("cop", tk.id):
	        return tk.lemma

	    return tk.lemma

def createDocFromLXML(x):
	tokens = [createTokenFromLXML(tk) for tk in x.xpath("./tokens/token")]
	rels   = [createRelFromLXML(rel) for rel in x.xpath("./dependencies[@type='collapsed-ccprocessed-dependencies']/dep")
	          if "root" != rel.attrib["type"]]

	return doc_t("?", " ".join([tk.surf for tk in tokens]), tokens, rels, {})


class sdreader_t:
	def __init__(self):
		self.buff  = []
		self.docid = 0
		self.numReadLines = 0

	def feed(self, stream):
		"""
		stream: Stream object of the parsed data.
		return: set of tokens-rels tuples.
		"""
		for ln in stream:
			if "Sentence #" in ln:
				if len(self.buff) > 0:
					yield self.pop()

				self.buff = []

			else:
				self.buff += [ln]

		if len(self.buff) > 0:
			yield self.pop()

	def feed_cw12(self, stream):
		"""
		stream: Stream object of the CW12 parsed data.
		return: set of tokens-rels tuples.
		"""

		for ln in stream:
			self.numReadLines += 1

			if "XML_BEGIN" in ln:
				self.buff = []
				self.docid = self.numReadLines

			self.buff += [ln]

			if "XML_END" in ln:
				yield self.pop()

	def pop(self):
		text     = "".join(self.buff)
		textRels = regexRelsDetector.findall(text)
		textRels = textRels[0] if len(textRels) > 0 else ""
		tokens   = [token_t(i, *x) for i, x in enumerate(regexTokenDetector.findall(text))]
		textCorefs = text.split("Coreference set:\n")
		corefs = collections.defaultdict(list)

		if len(textCorefs) > 1:
			for i, textcoref in enumerate(textCorefs[1:]):
				for x in regexCorefDetector.findall(textcoref):
					corefs[(int(x[0]), int(x[1])-1)] += [i]
					corefs[(int(x[4]), int(x[5])-1)] += [i]

		rels = [rel_t(x.group(1), int(x.group(2))-1, int(x.group(3))-1)
				for x in regexRelDetector.finditer(textRels) if "root" != x.group(1)]

		return doc_t(self.docid, self.buff[2].strip(), tokens, rels, corefs)
