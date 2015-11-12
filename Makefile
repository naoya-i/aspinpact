CORENLP=~/src/stanford-corenlp-full-2015-04-20/corenlp.sh
CLINGO=~/tmp/clingo-4.5.3-linux-x86_64/clingo
CORENLP2PL=python src/cc.py

# My precious...
.PRECIOUS: %.eval %.sys.interp %.possible %.pl %.txt.corenlp.xml

%.eval: %.sys.interp
	python src/compareInterp.py $(subst .sys.,.gold.,$<) $< > $@

%.sys.interp: %.pl
	-$(CLINGO) data/theory.pl $< > $@.stdout.clingo 2> $@.stderr.clingo
	python src/extractBestAnswerSet.py $@.stdout.clingo > $@

%.possible: %.pl
	-$(CLINGO) -n 0 --opt-mode=enum data/theory.pl $< > $@.stdout.clingo 2> $@.stderr.clingo
	python src/isInCandidate.py $(subst .pl,.gold.interp,$<) $@.stdout.clingo > $@

%.pl: %.txt.corenlp.xml
	$(CORENLP2PL) $< > $@

%.txt.corenlp.xml: %.txt
	$(CORENLP) -file $< -outputDirectory $(dir $<) -outputExtension .corenlp.xml
