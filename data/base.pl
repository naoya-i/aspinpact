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

% less A
negated(X) :- dep("advmod", X, L), token(L, _, "less", "RBR", _).

% no longer be a threat. (advmod(threat, longer) + neg(longer, no))
negated(X) :- dep("advmod", X, L), dep("neg", L, _).

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


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% ISA.

% He is a player. (nsubj(player, he))
isa(X, Xi) :- dep("nsubj", Xi, X), isNoun(Xi).

% He wants to be a friend. (nsubj(want, he) + xcomp(want, friend))
isa(X, Xi) :- dep("nsubj", V, X), dep("xcomp", V, Xi), isNoun(Xi).

% He is perceived as a good artist. (nsubjpass(perceived, he) + nmod:as(perceived, artist))
isa(X, Xi) :- dep("nsubjpass", V, X), dep("nmod:as", V, Xi), isNoun(Xi).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Sentiment.
% senti(J, @extfunc(senti(W))) : isAdj(J), surf(J, W).

deepSentiType("punish").
deepSentiType("hit").
deepSentiType("heal").
deepSentiType("respect").
deepSentiType("disrespect").

deepsenti(DST, "focus", V, X) :-
  isVerb(V), isNoun(X),
  token(V, _, W_V, P_V, _),
  dep(@extfunc(dsTargetArg(W_V, P_V, DST)), V, X),
  deepSentiType(DST).

deepsenti(DST, "reference", V, X) :-
  isVerb(V), isNoun(X),
  token(V, _, W_V, P_V, _),
  dep(@extfunc(dsSubArg(W_V, P_V, DST)), V, X),
  deepSentiType(DST).

senti(X, @extfunc(senti(WN))) :- isa(X, N), not negated(N), lemma(N, WN).
senti(X, @extfunc(invsenti(WN))) :- isa(X, N), negated(N), lemma(N, WN).
senti(X, @extfunc(senti(WJ))) :- modify(J, X), not negated(J), lemma(J, WJ).
senti(X, @extfunc(invsenti(WJ))) :- modify(J, X), negated(J), lemma(J, WJ).

% senti(X, S) :- isa(X, Xi), not negated(Xi), senti(Xi, S).
% senti(X, @invsenti(S)) :- isa(X, Xi), negated(Xi), senti(Xi, S).


% entitySentimentByEventSlot(X, positive) :- canDo(X).
% entitySentimentByEventSlot(X, negative) :- cantDo(X).
% entitySentimentByEventSlot(X, negative) :- hasTooMuch(X).
% entitySentimentByEventSlot(X, xfSenti(Y)) :- has(X, Y).
% entitySentimentByEventSlot(X, xfSlotSenti(V, T)) :- isVerb(V), dep(T, V, X), not negated(V).
% entitySentimentByEventSlot(X, xfInvSenti(xfSlotSenti(V, T))) :- isVerb(V), dep(T, V, X), negated(V).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Linguistic rules.

% X have Y
has(X, Y) :- token(VH, _, "have", _, _), dep("nsubj", VH, X), dep("dobj", VH, Y).

% X have lots of Y
has(X, Y) :- token(VH, _, "have", _, _), dep("nsubj", VH, X), dep("dobj", VH, L), token(L, _, "lot", _, _), dep("nmod:of", L, Y).

% X have too many absences = nsubj(have, X) + dobj(have, absences) + amod(absences, many) + advmod(many, too).
hasTooMuch(X) :- has(X, O), dep("amod", O, J), dep("advmod", J, T), token(T, _, "too", _, _).

% X couldn't do
cantDo(X) :- dep("nsubj", VM, X), negated(VM), dep("aux", VM, VC), token(VC, _, "could", _, _).

% X could do
canDo(X) :- dep("nsubj", VM, X), not negated(VM), dep("aux", VM, VC), token(VC, _, "could", _, _).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Basic theory.
1 {pronominalized(N, P): mention(N)} 1 :- pronoun(P).
dep(T, V, N) :- pronominalized(N, P), dep(T, V, P).

% Left link.
N<P :- pronominalized(N, P).

% mention(N) :- predictedMention(N).
mention(N) :- use_gold_mention, gold(mention(N)).
mention(N) :- not use_gold_mention, predicted(mention(N)).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Deep sentiment theory.
deepsenti(Y, respect, p) :- respect(X, Y).
deepsenti(Y, damage, n) :- punish(X, Y).


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
:~ pronominalized(N, P), respected(N, yes), entitySentimentByModifier(P, positive). [1@1, wfRespectSomethingPositive, N, P]
:~ pronominalized(N, P), respected(N, yes), entitySentimentByEventSlot(P, positive). [1@1, wfRespectSomethingPositive, N, P]
:~ pronominalized(N, P), removed(N, yes), entitySentimentByModifier(P, negative). [1@1, wfRemoveSomethingNegative, N, P]
:~ pronominalized(N, P), removed(N, yes), entitySentimentByEventSlot(P, negative). [1@1, wfRemoveSomethingNegative, N, P]
:~ pronominalized(N, P), entitySentimentByEventSlot(N, S), entitySentimentByEventSlot(P, S), S != neutral. [1@1, wfSentimentFromESmatch, N, P]

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
