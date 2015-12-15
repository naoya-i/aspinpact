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
% Dependency complementizer.

% he had to watch = nsubj(had, he) + xcomp(had, watch)
dep("nsubj", V, X) :- dep("nsubj", Vcat, X), dep("xcomp", Vcat, V).


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
negated(X) :- dep("advmod", X, L), token(L, _, "less", "RBR", _).
negated(X) :- dep("advmod", X, L), token(L, _, "rarely", "RB", _).
negated(X) :- dep("advmod", X, L), token(L, _, "scarcely", "RB", _).
negated(X) :- dep("advmod", X, L), token(L, _, "hardly", "RB", _).
negated(X) :- dep("mark", X, U), token(U, _, "unless", "IN", _).

% No longer be a threat. (advmod(threat, longer) + neg(longer, no))
negated(X) :- dep("advmod", X, L), dep("neg", L, _).

% Nobody supports
negated(X) :- dep("nsubj", X, N), token(N, _, "nobody", "NN", _).

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
compared(X, Y) :- dep("nsubj", J, X), dep("nmod:than", J, Y), isAdj(J).


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

% Lexicon.
sentidb(J, @extfunc(senti(WJ))) :- isAdj(J), lemma(J, WJ).
sentidb(N, @extfunc(senti(WN))) :- isNoun(N), lemma(N, WN).

% Definitions.
deepsentiEventType("punish").
deepsentiEventType("hit").
deepsentiEventType("heal").
deepsentiEventType("respect").
deepsentiEventType("disrespect").

invDS("heal", "hit").
invDS("hit", "heal").
invDS("heal", "hit").
invDS("hit", "heal").
invDS("respect", "disrespect").
invDS("disrespect", "respect").

invSenti("p", "n").
invSenti("n", "p").

% Rules.
deepsentiEvent(DST, "focus", V, X) :-
  isVerb(V), isNoun(X),
  token(V, _, W_V, P_V, _),
  not negated(V),
  dep(@extfunc(dsTargetArg(W_V, P_V, DST)), V, X),
  deepsentiEventType(DST).

deepsentiEvent(INVDST, "focus", V, X) :-
  isVerb(V), isNoun(X),
  token(V, _, W_V, P_V, _),
  negated(V),
  dep(@extfunc(dsTargetArg(W_V, P_V, DST)), V, X),
  deepsentiEventType(DST),
  invDS(DST, INVDST).

deepsentiEvent(DST, "reference", V, X) :-
  isVerb(V), isNoun(X),
  token(V, _, W_V, P_V, _),
  not negated(V),
  dep(@extfunc(dsSubArg(W_V, P_V, DST)), V, X),
  deepsentiEventType(DST).

deepsentiEvent(INVDST, "reference", V, X) :-
  isVerb(V), isNoun(X),
  token(V, _, W_V, P_V, _),
  negated(V),
  dep(@extfunc(dsSubArg(W_V, P_V, DST)), V, X),
  deepsentiEventType(DST),
  invDS(DST, INVDST).


% Deep sentiment theory.
deepsenti(X, "respect", "p") :- deepsentiEvent("respect", "focus", V, X).
deepsenti(X, "respect", "n") :- deepsentiEvent("disrespect", "focus", V, X).
deepsenti(X, "damage", "n") :- deepsentiEvent("punish", "focus", V, X).
deepsenti(X, "damage", "n") :- deepsentiEvent("hit", "focus", V, X).
deepsenti(X, "strength", "p") :- deepsentiEvent("heal", "focus", V, X).

% threat
senti(X, S) :- isNoun(X), sentidb(X, S), S != "0".

% better candidate, he is cute
senti(X, S) :- isNoun(X), not negated(J), modify(J, X), not too(J), sentidb(J, S), S != "0".

% he is not cute.
senti(X, S) :- isNoun(X), negated(J), modify(J, X), not too(J), sentidb(J, Si), invSenti(S, Si).

% he is too shy.
senti(X, "n") :- isNoun(X), not negated(J), modify(J, X), too(J).

% he is a threat.
senti(X, S) :- isNoun(X), isa(X, Xi), not negated(Xi), senti(Xi, S), S != "0".

% he is not a threat.
senti(X, S) :- isNoun(X), isa(X, Xi), negated(Xi), senti(Xi, Si), invSenti(S, Si).

% it has a virus.
senti(X, S) :- isNoun(X), has(X, Xi, V), not negated(V), senti(Xi, S), S != "0".

% it does not have a virus.
senti(X, S) :- isNoun(X), has(X, Xi, V), negated(V), senti(Xi, S), S != "0".

% B: it is better than B
senti(X, S) :- isNoun(X), compared(Xfoc, X), senti(Xfoc, Si), invSenti(S, Si).

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
dep(T, V, N) :- pronominalized(N, P), dep(T, V, P).

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
