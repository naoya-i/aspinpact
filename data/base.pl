%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Inference options.
%% use_ner.
%% use_synonym.
%% use_hypernym.
%% use_loose_hypernym.
use_surf.
use_selpef.
use_selpref_svo.
use_esa.

use_gold_mention.


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Lexicon.

% Negator
negatingInf("fail").  negatingInf("reject"). negatingInf("avoid").

negatingMod("less"). negatingMod("rarely"). negatingMod("scarcely").
negatingMod("hardly"). negatingMod("unless").

% Connectives.
rconnEC("because", cause_effect).   rconnEC("since", cause_effect).
rconnEC("although", cause_unexp_effect). rconnEC("though", cause_unexp_effect).
rconnEC("if", cause_effect).        rconnEC("when", cause_effect).
rconnCE("so", cause_effect).

% Linking Verbs.
linkingVerb("appear"). linkingVerb("look"). linkingVerb("sound").
linkingVerb("become"). linkingVerb("seem"). linkingVerb("stay").
linkingVerb("feel"). linkingVerb("remain"). linkingVerb("taste").
linkingVerb("grow"). linkingVerb("smell"). linkingVerb("get").


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% CoreNLP Token related rules.
surf(X, W) :- token(X, W, _, _, _).
lemma(X, L) :- token(X, _, L, _, _).
pos(X, P) :- token(X, _, _, P, _).
ne(X, N) :- token(X, _, _, _, N).

isNoun(X) :- token(X, _, _, "NN", _).
isNoun(X) :- token(X, _, _, "NNS", _).
isNoun(X) :- isProperNoun(X).
isNoun(X) :- isPronoun(X).

isProperNoun(X) :- token(X, _, _, "NNP", _).
isProperNoun(X) :- token(X, _, _, "NNPS", _).

isAdj(X)  :- token(X, _, _, "JJ", _).
isAdj(X)  :- token(X, _, _, "JJR", _).
isAdj(X)  :- token(X, _, _, "JJS", _).

isVerb(X)  :- token(X, _, _, "VB", _).
isVerb(X)  :- token(X, _, _, "VBD", _).
isVerb(X)  :- token(X, _, _, "VBG", _).
isVerb(X)  :- token(X, _, _, "VBN", _).
isVerb(X)  :- token(X, _, _, "VBP", _).
isVerb(X)  :- token(X, _, _, "VBZ", _).

isPronoun(X) :- token(X, _, _, "PRP", _).
isPronoun(X) :- token(X, _, _, "PRP$", _).

isCatenative(V) :- isVerb(V), dep("xcomp", V, V2), dep("mark", V2, T), lemma(T, "to").

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Dependency complementizer.

% did A by X = X did A
dep("nsubj", V, X) :- dep("nmod:agent", V, X).

% he got angry = he was angry
dep("nsubj", J, X) :- dep("nsubj", V, X), dep("xcomp", V, J), lemma(V, LV), linkingVerb(LV).

% he had to watch = nsubj(had, he) + xcomp(had, watch)
dep("nsubj", V, X) :- dep("nsubj", Vcat, X), dep("xcomp", Vcat, V), not pos(V, "VBN").

% he needs to be trained = nsubj(need, he) + xcomp(need, trained)
dep("nsubjpass", V, X) :- dep("nsubj", Vcat, X), dep("xcomp", Vcat, V), pos(V, "VBN").


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Mention.
predicted(mention(N)) :- isNoun(N), not dep("compound", _, N).
pronoun(P) :- isPronoun(P).

number(I, @extfunc(number(L, P))) :- predicted(mention(I)), token(I, _, L, P, _).
number(I, @extfunc(number(L, P))) :- pronoun(I), token(I, _, L, P, _).
gender(I, @extfunc(gender(L, N))) :- predicted(mention(I)), token(I, _, L, _, N).
gender(I, @extfunc(gender(L, N))) :- pronoun(I), token(I, _, L, _, N).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Modifiers.
negated(X) :- dep("neg", X, _).

% less A, rarely A, scarcely A, hardly A, unless A
negated(X) :- dep("advmod", X, L), lemma(L, LL), negatingMod(LL).
negated(X) :- dep("mark", X, U), lemma(U, LU), negatingMod(LU).

negated(X) :- dep("xcomp", F, X), lemma(F, FL), negatingInf(FL), dep("mark", X, T), lemma(T, "to").

% No longer be a threat. (advmod(threat, longer) + neg(longer, no))
negated(X) :- dep("advmod", X, L), dep("neg", L, _).

% Nobody supports
negated(X) :- dep("nsubj", X, N), token(N, _, "nobody", "NN", _).

%
% Modifier

% He is cute. A cool guy.
modify(J, N) :- isAdj(J), dep("nsubj", J, N).
modify(J, N) :- isAdj(J), dep("amod", N, J).

% He looks sad. (xcomp(look, sad) + nsubj(look, he))
modify(J, N) :- isAdj(J), dep("xcomp", V, J), dep("nsubj", V, N).

% She gets scared. (advmod(get, scared) + nsubj(get, she))
% The dog barked menacingly. (advmod(bark, menacingly) + nsubj(bark, dog))
modify(J, N) :- dep("advmod", V, J), dep("nsubj", V, N).

% He is scared.
modify(J, N) :- dep("nsubjpass", J, N), token(V, _, _, "VBN", _).

% He is being mean.
modify(J, N) :- dep("nsubj", Vbeing, N), dep("xcomp", Vbeing, J).

% A is better than B = nsubj(better, A) + nmod:than(better, B)
compared(X, Y, J) :- dep("nsubj", J, X), dep("nmod:than", J, Y), isAdj(J).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% ISA.

% He is a player. (nsubj(player, he))
isa(X, Xi) :- dep("nsubj", Xi, X), isNoun(Xi).

% He wants to be a friend. (nsubj(want, he) + xcomp(want, friend))
isa(X, Xi) :- dep("nsubj", V, X), dep("xcomp", V, Xi), isNoun(Xi).

% He is perceived as a good artist. (nsubjpass(perceived, he) + nmod:as(perceived, artist))
isa(X, Xi) :- dep("nsubjpass", V, X), dep("nmod:as", V, Xi), isNoun(Xi).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Coherence relation classifier.

% The classifier.
corel(R, VC, VE) :- dep("advcl", VE, VC), dep("mark", VC, B), lemma(B, LB), rconnEC(LB, R).
corel(R, VC, VE) :- dep("advcl", VC, VE), dep("mark", VE, S), lemma(S, LS), rconnCE(LS, R).
corel(R, VC, VE) :- dep("parataxis", VC, VE), dep("advmod", VC, S), lemma(S, LS), rconnCE(LS, R).
corel(R, VC, VE) :- dep("parataxis", VC, VE), dep("dep", VC, S), lemma(S, LS), rconnCE(LS, R).
corel(cause_effect, VC, VE) :- dep("conj:and", VC, VE).
corel(cause_unexp_effect, VC, VE) :- dep("conj:but", VC, VE).

% Inheritance of cause-effects. (X try to put / X get angry).
corel(R, VC, VE) :- corel(R, VC, VEc), dep("xcomp", VEc, VE).
corel(R, VC, VE) :- corel(R, VCc, VE), dep("xcomp", VCc, VC).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Sentiment.

% Lexicon.
sentidb(J, @extfunc(senti(WJ))) :- isAdj(J), lemma(J, WJ).
sentidb(N, @extfunc(senti(WN))) :- isNoun(N), lemma(N, WN).
sentidb(V, @extfunc(senti(WV))) :- isVerb(V), lemma(V, WV).
wi05sentidb(J, @extfunc(wi05senti(WJ))) :- isAdj(J), lemma(J, WJ).
wi05sentidb(N, @extfunc(wi05senti(WN))) :- isNoun(N), lemma(N, WN).
wi05sentidb(V, @extfunc(wi05senti(WV))) :- isVerb(V), lemma(V, WV).
g13ppvsentidb(V, @extfunc(g13ppvsenti(WV))) :- isVerb(V), lemma(V, WV).
c14ewnsentidb(V, @extfunc(c14ewnsenti(WV))) :- isVerb(V), lemma(V, WV).
fgafstsentidb(V, @extfunc(fgafstsenti(WV))) :- isVerb(V), lemma(V, WV).
fgafstsentidb(J, @extfunc(fgafstsenti(WV))) :- isAdj(J), lemma(J, WV).

invSenti("p", "n").
invSenti("n", "p").

%%%
% Goyal et al. 13's affect projection rules

% R1: Mary laughed.
g13r1(Xsb, S, V) :- g13ppvsentidb(V, S), dep("nsubj", V, Xsb), not dep("dobj", V, _).
g13ppvsenti(Xsb, S) :- g13r1(Xsb, S, V), not negated(V).
g13ppvsenti(Xsb, Si) :- g13r1(Xsb, S, V), negated(V), invSenti(S, Si).

% R2: John was rewarded.
g13r2(Xob, S, V) :- g13ppvsentidb(V, S), dep("nsubjpass", V, Xob).
g13ppvsenti(Xob, S) :- g13r2(Xob, S, V), not negated(V).
g13ppvsenti(Xob, Si) :- g13r2(Xob, S, V), negated(V), invSenti(S, Si).

% R3: Policeman arrested John.
g13r3(Xob, S, V) :- g13ppvsentidb(V, S), dep("nsubj", V, X), dep("dobj", V, Xob).
g13ppvsenti(Xob, S) :- g13r3(Xob, S, V), not negated(V).
g13ppvsenti(Xob, Si) :- g13r3(Xob, S, V), negated(V), invSenti(S, Si).

% R4: Bo decided to kill Bob:
% There is no special axiom because the xcomp propagation rule lets R3 applied.

%%%
% C14 Lex + Goyal et al. 13's affect projection rules

% R1: Mary laughed.
g13c14r1(Xsb, S, V) :- c14ewnsentidb(V, S), dep("nsubj", V, Xsb), not dep("dobj", V, _).
g13c14ppvsenti(Xsb, S) :- g13c14r1(Xsb, S, V), not negated(V).
g13c14ppvsenti(Xsb, Si) :- g13c14r1(Xsb, S, V), negated(V), invSenti(S, Si).

% R2: John was rewarded.
g13c14r2(Xob, S, V) :- c14ewnsentidb(V, S), dep("nsubjpass", V, Xob).
g13c14ppvsenti(Xob, S) :- g13c14r2(Xob, S, V), not negated(V).
g13c14ppvsenti(Xob, Si) :- g13c14r2(Xob, S, V), negated(V), invSenti(S, Si).

% R3: Policeman arrested John.
g13c14r3(Xob, S, V) :- c14ewnsentidb(V, S), dep("nsubj", V, X), dep("dobj", V, Xob).
g13c14ppvsenti(Xob, S) :- g13c14r3(Xob, S, V), not negated(V).
g13c14ppvsenti(Xob, Si) :- g13c14r3(Xob, S, V), negated(V), invSenti(S, Si).

%%%
% Rahman & Ng 12's affect projection rules
rn12flippableEnv(V) :- negated(V).
rn12flippableEnv(V) :- dep("mark", V, M), lemma(M, "though").
rn12flippableEnv(V) :- dep("mark", V, M), lemma(M, "although").
rn12flippableEnv(V) :- dep("conj:but", Vgov, V).

% Verb projection: man killed
rn12r1(Xsb, S, V) :- dep("nsubj", V, Xsb), isVerb(V), wi05sentidb(V, S).
rn12senti(Xsb, S) :- rn12r1(Xsb, S, V), not rn12flippableEnv(V).
rn12senti(Xsb, Si) :- rn12r1(Xsb, S, V), rn12flippableEnv(V), invSenti(S, Si).

% Adjective projection: cute girl
rn12senti(Xt, S) :- modify(J, Xt), wi05sentidb(J, S), not rn12flippableEnv(J).
rn12senti(Xt, Si) :- modify(J, Xt), wi05sentidb(J, S), rn12flippableEnv(J), invSenti(S, Si).

% is good companion.
% rn12senti(Xt, S) :- isa(Xt, N), modify(J, N), wi05sentidb(J, S), not rn12flippableEnv(J).
% rn12senti(Xt, Si) :- isa(Xt, N), modify(J, N), wi05sentidb(J, S), rn12flippableEnv(J), invSenti(S, Si).

% Than projection: better than John.
rn12senti(Xt, Si) :- dep("nmod:than", J, Xt), wi05sentidb(J, S), invSenti(S, Si).

%%%
% Peng & Roth 15's affect projection rules
pr15flippableEnv(V) :- negated(V).
pr15flippableEnv(V) :- dep("mark", V, M), lemma(M, "though").
pr15flippableEnv(V) :- dep("mark", V, M), lemma(M, "although").
pr15flippableEnv(V) :- dep("conj:but", Vgov, V).

% Verb projection: man killed
pr15r1(Xsb, S, V) :- dep("nsubj", V, Xsb), isVerb(V), wi05sentidb(V, S).
pr15r1(Xob, Si, V) :- dep("dobj", V, Xob), isVerb(V), wi05sentidb(V, S), invSenti(S, Si).
pr15r1(Xob, Si, V) :- dep("nsubjpass", V, Xob), isVerb(V), wi05sentidb(V, S), invSenti(S, Si).
pr15senti(Xsb, S) :- pr15r1(Xsb, S, V), not pr15flippableEnv(V).
pr15senti(Xsb, Si) :- pr15r1(Xsb, S, V), pr15flippableEnv(V), invSenti(S, Si).

% Adjective projection: cute girl
pr15senti(Xt, S) :- modify(J, Xt), wi05sentidb(J, S), not flippableEnv(J).
pr15senti(Xt, Si) :- modify(J, Xt), wi05sentidb(J, S), flippableEnv(J), invSenti(S, Si).

%%%
% Choi14 Lexicon + Rahman & Ng 12's affect projection rules
% Verb projection: man killed
rn12c14r1(Xsb, S, V) :- dep("nsubj", V, Xsb), isVerb(V), c14ewnsentidb(V, S).
rn12c14senti(Xsb, S) :- rn12c14r1(Xsb, S, V), not rn12flippableEnv(V).
rn12c14senti(Xsb, Si) :- rn12c14r1(Xsb, S, V), rn12flippableEnv(V), invSenti(S, Si).

% Adjective projection: cute girl
rn12c14senti(Xt, S) :- modify(J, Xt), wi05sentidb(J, S), not rn12flippableEnv(J).
rn12c14senti(Xt, Si) :- modify(J, Xt), wi05sentidb(J, S), rn12flippableEnv(J), invSenti(S, Si).

%%%
% Choi14 Lexicon + Rahman & Ng 12's affect projection rules
% Verb projection: man killed
rn12g13r1(Xsb, S, V) :- dep("nsubj", V, Xsb), isVerb(V), g13ppvsentidb(V, S).
rn12g13senti(Xsb, S) :- rn12g13r1(Xsb, S, V), not rn12flippableEnv(V).
rn12g13senti(Xsb, Si) :- rn12g13r1(Xsb, S, V), rn12flippableEnv(V), invSenti(S, Si).

% Adjective projection: cute girl
rn12g13senti(Xt, S) :- modify(J, Xt), wi05sentidb(J, S), not rn12flippableEnv(J).
rn12g13senti(Xt, Si) :- modify(J, Xt), wi05sentidb(J, S), rn12flippableEnv(J), invSenti(S, Si).

% Plan projection.
% mentalVerb("want"). mentalVerb("try").
% mentalVerb("feel"). mentalVerb("need").
%
% ino16mental(V) :- lemma(V, L), mentalVerb(L), leadsToInfinitive(V).
% ino16afst(X, "m") :- ino16mental(V), dep("nsubj", V, X).
% ino16afst(X, "p") :- dep("nsubj", V, X), not ino16mental(V), isVerb(V), V!=V2, not dep("nsubj", V2, X), isVerb(V2), ino16mental(V2).
% ino16afst(X, "p") :- dep("nsubj", V, X), not ino16mental(V), isVerb(V), V!=V2, token(V2, _, _, _, _), not ino16mental(V2).

% Fine-grained Sentiments.
invFgsRel("nsubj", "dobj").
invFgsRel("nsubj", "nmod:against").
invFgsRel("nsubj", "nmod:to").
invFgsRel("nsubj", "nmod:at").
invFgsRel("nsubj", "nmod:from").
invFgsRel("nsubj", "nmod:in").
invFgsRel("nsubj", "nmod:for").
invFgsRel("nsubj", "-").
invFgsRel(X, Y) :- invFgsRel(Y, X).

invFgs("heal", "hit").
invFgs("heal", "hit").
invFgs("respect", "disrespect").
invFgs(X, Y) :- invFgs(Y, X).

% Affect state projection.
fgsdep(V, T, "focus", X) :- fgafstsentidb(V, (T, R_focus)), dep(R_focus, V, X), not isCatenative(V), not negated(V).
fgsdep(V, Ti, "focus", X) :- fgafstsentidb(V, (T, R_focus)), dep(R_focus, V, X), not isCatenative(V), negated(V), invFgs(T, Ti).
fgsdep(V, T, "ref", X) :- fgafstsentidb(V, (T, R_focus)), invFgsRel(R_focus, R_ref), dep(R_ref, V, X), not isCatenative(V), not negated(V).
fgsdep(V, Ti, "ref", X) :- fgafstsentidb(V, (T, R_focus)), invFgsRel(R_focus, R_ref), dep(R_ref, V, X), not isCatenative(V), negated(V), invFgs(T, Ti).

%
% Causal relation between affect states.

% X attack => attack X/arrest X/hate X/angry at X
fgstie(X, Y) :- fgsdep(VC, "hit", "ref", X), fgsdep(VE, "hit", "focus", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "hit", "ref", X), fgsdep(VE, "punish", "focus", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "hit", "ref", X), fgsdep(VE, "disrespect", "focus", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "hit", "ref", X), fgsdep(VE, "anger", "focus", Y), corel(cause_effect, VC, VE).

% not-support X/attack X => X fire/X attack/cure X/beat X/X is angry
fgstie(X, Y) :- fgsdep(VC, "hit", "focus", X), fgsdep(VE, "punish", "ref", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "hit", "focus", X), fgsdep(VE, "hit", "ref", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "hit", "focus", X), fgsdep(VE, "heal", "focus", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "hit", "focus", X), fgsdep(VE, "disrespect", "focus", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "hit", "focus", X), fgsdep(VE, "weak", "focus", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "hit", "focus", X), fgsdep(VE, "anger", "ref", Y), corel(cause_effect, VC, VE).

% X improve => need X
fgstie(X, Y) :- fgsdep(VC, "heal", "ref", X), fgsdep(VE, "respect", "focus", Y), corel(cause_effect, VC, VE).

% support X => X win/master
fgstie(X, Y) :- fgsdep(VC, "heal", "focus", X), fgsdep(VE, "weak", "ref", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "heal", "focus", X), fgsdep(VE, "suppression", "ref", Y), corel(cause_effect, VC, VE).

% X punish => hit X
fgstie(X, Y) :- fgsdep(VC, "punish", "ref", X), fgsdep(VE, "hit", "focus", Y), corel(cause_effect, VC, VE).

% like X => support X
fgstie(X, Y) :- fgsdep(VC, "respect", "focus", X), fgsdep(VE, "heal", "focus", Y), corel(cause_effect, VC, VE).

% X like => X like/support X
fgstie(X, Y) :- fgsdep(VC, "respect", "ref", X), fgsdep(VE, "respect", "ref", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "respect", "ref", X), fgsdep(VE, "heal", "focus", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "respect", "ref", X), fgsdep(VE, "heal", "ref", Y), corel(cause_effect, VC, VE).

% X hate => punish X/X hit
fgstie(X, Y) :- fgsdep(VC, "disrespect", "ref", X), fgsdep(VE, "punish", "focus", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "disrespect", "ref", X), fgsdep(VE, "hit", "ref", Y), corel(cause_effect, VC, VE).

% X did not win/dislike => beat X/X hit
fgstie(X, Y) :- fgsdep(VC, "weak", "ref", X), fgsdep(VE, "hit", "ref", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "weak", "ref", X), fgsdep(VE, "weak", "focus", Y), corel(cause_unexp_effect, VC, VE).

% hate X => X attack
fgstie(X, Y) :- fgsdep(VC, "suppression", "focus", X), fgsdep(VE, "hit", "ref", Y), corel(cause_effect, VC, VE).

% X is angry/mischeivous => X hit/hunt
fgstie(X, Y) :- fgsdep(VC, "anger", "ref", X), fgsdep(VE, "hit", "ref", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "ethically-bad", "ref", X), fgsdep(VE, "hit", "ref", Y), corel(cause_effect, VC, VE).

% X is hungry => X hit/cook for X
fgstie(X, Y) :- fgsdep(VC, "health-bad", "ref", X), fgsdep(VE, "hit", "ref", Y), corel(cause_effect, VC, VE).
fgstie(X, Y) :- fgsdep(VC, "health-bad", "ref", X), fgsdep(VE, "heal", "focus", Y), corel(cause_effect, VC, VE).

% X is good => like X
fgstie(X, Y) :- senti(X, "p"), fgsdep(VE, "respect", "focus", Y), corel(cause_effect, _, VE).

% X <T> => X <T>
fgstie(X, Y) :- fgsdep(VC, T, R, X), fgsdep(VE, T, R, Y), corel(cause_effect, VC, VE).

% X is bad => remove/punish X
% fgstie(X, Y) :- senti(X, "n"), fgsdep(VE, "hit", "focus", Y), corel(cause_effect, VC, VE).
% fgstie(X, Y) :- senti(X, "n"), fgsdep(VE, "punish", "focus", Y), corel(cause_effect, VC, VE).

% Reflexivity of fgstie/2.
fgstie(X, Y) :- fgstie(Y, X).

%
% Original sentiment.

% threat
senti(X, S) :- isNoun(X), sentidb(X, S).

% better candidate, he is cute
senti(X, S) :- isNoun(X), not negated(J), modify(J, X), not too(J), sentidb(J, S).

% he is not cute.
senti(X, S) :- isNoun(X), negated(J), modify(J, X), not too(J), sentidb(J, Si), invSenti(S, Si).

% he is too shy.
senti(X, "n") :- isNoun(X), not negated(J), modify(J, X), too(J).

% he is a threat.
senti(X, S) :- isNoun(X), isa(X, Xi), not negated(Xi), senti(Xi, S).

% he is not a threat.
senti(X, S) :- isNoun(X), isa(X, Xi), negated(Xi), senti(Xi, Si), invSenti(S, Si).

% it has a virus.
senti(X, S) :- isNoun(X), has(X, Xi, V), not negated(V), senti(Xi, S).

% it does not have a virus.
senti(X, S) :- isNoun(X), has(X, Xi, V), negated(V), senti(Xi, S).

% B: it is better than B
senti(X, S) :- isNoun(X), compared(Xfoc, X, _), senti(Xfoc, Si), invSenti(S, Si).

% entitySentimentByEventSlot(X, positive) :- canDo(X).
% entitySentimentByEventSlot(X, negative) :- cantDo(X).
% entitySentimentByEventSlot(X, negative) :- hasTooMuch(X).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Linguistic rules.

% X have Y
has(X, Y, VH) :- token(VH, _, "have", _, _), dep("nsubj", VH, X), dep("dobj", VH, Y).

% X have lots of Y
has(X, Y, VH) :- token(VH, _, "have", _, _), dep("nsubj", VH, X), dep("dobj", VH, L), token(L, _, "lot", _, _), dep("nmod:of", L, Y).

% X have too many absences = nsubj(have, X) + dobj(have, absences) + amod(absences, many) + advmod(many, too).
hasTooMuch(X) :- has(X, O), dep("amod", O, J), dep("advmod", J, T), token(T, _, "too", _, _).

% X couldn't do
cantDo(X) :- dep("nsubj", VM, X), negated(VM), dep("aux", VM, VC), token(VC, _, "could", _, _).

% X could do
canDo(X) :- dep("nsubj", VM, X), not negated(VM), dep("aux", VM, VC), token(VC, _, "could", _, _).

% too strict = advmod(strict, too)
too(J) :- dep("advmod", J, T), token(T, _, "too", "RB", _).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Basic theory.
1 {pronominalized(N, P): mention(N)} 1 :- pronoun(P).

% dep(T, V, N) :- pronominalized(N, P), dep(T, V, P).

% Left link.
N<P :- pronominalized(N, P).

% mention(N) :- predictedMention(N).
mention(N) :- use_gold_mention, gold(mention(N)).
mention(N) :- not use_gold_mention, predicted(mention(N)).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Regular coreference features.

% Surface feature.
% :~ pronominalized(N, P), token(N, _, WN, _, _), token(P, _, WP, _, _). [1@1, wfSurf, N, P, i, WN, WP]

% Syntactic feature.
:~ pronominalized(N, P),
  dep(R1, E, N), dep(R2, E, P),
  R1 != R2.
  [1@1, wfDiffPred, N, P]

% Semantic features.
:~ pronominalized(N, P),
  number(N, NUM), number(P, NUM).
  [@featfunc(numberMatch)@1, numberMatch, N, P]

:~ pronominalized(N, P),
  gender(N, G), gender(P, G),
  G != neutral.
  [@featfunc(genderMatch)@1, genderMatch, N, P]

% :~ pronominalized(N, P), S != neutral, entitySentimentByEventSlot(N, S), entitySentimentByModifier(P, S). [1@1, wfSentimentGuessMatch_ESM, N, P]
% :~ pronominalized(N, P), S != neutral, entitySentimentByModifier(N, S), entitySentimentByEventSlot(P, S). [1@1, wfSentimentGuessMatch_ESM, N, P]
% :~ pronominalized(N, P), S != neutral, entitySentimentByEventSlot(N, S), entitySentimentByEventSlot(P, S). [1@1, wfSentimentGuessMatch_ES, N, P]
% :~ pronominalized(N, P), S != neutral, entitySentimentByModifier(N, S), entitySentimentByModifier(P, S). [1@1, wfSentimentGuessMatch_M, N, P]
% :~ pronominalized(N, P), respected(N, yes), entitySentimentByModifier(P, positive). [1@1, wfRespectSomethingPositive, N, P]
% :~ pronominalized(N, P), respected(N, yes), entitySentimentByEventSlot(P, positive). [1@1, wfRespectSomethingPositive, N, P]
% :~ pronominalized(N, P), removed(N, yes), entitySentimentByModifier(P, negative). [1@1, wfRemoveSomethingNegative, N, P]
% :~ pronominalized(N, P), removed(N, yes), entitySentimentByEventSlot(P, negative). [1@1, wfRemoveSomethingNegative, N, P]
% :~ pronominalized(N, P), entitySentimentByEventSlot(N, S), entitySentimentByEventSlot(P, S), S != neutral. [1@1, wfSentimentFromESmatch, N, P]

% Selectional preference.
:~ pronominalized(N, P),
  dep(T, V_P, P),
  token(N, _, W_N, _, "O"),
  token(V_P, _, W_VP, P_VP, _).
  [@featfunc(selpref(W_VP, P_VP, T, W_N))@1, selpref, N, P]

% Event slot assoc.
:~ pronominalized(N, P),
  dep(T_N, V_N, N), V_N!=V_P, dep(T_P, V_P, P),
  token(V_N, _, W_VN, P_VN, _),
  token(V_P, _, W_VP, P_VP, _).
  [@featfunc(esa(W_VN, P_VN, T_N, W_VP, P_VP, T_P))@1, esa, N, P]

%:~ pronominalized(N, P), modify(J, P). [1@1, wfGoogle, N, P, J]
