
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% POS related rules.

isNoun(X) :- token(X, _, _, "NN", _).
isNoun(X) :- token(X, _, _, "NNS", _).
isNoun(X) :- isProperNoun(X).

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

number(I, xfNumber(I)) :- predicted(mention(I)).
number(I, xfNumber(I)) :- pronoun(I).
gender(I, xfGender(I)) :- predicted(mention(I)).
gender(I, xfGender(I)) :- pronoun(I).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Modifiers.
negated(X) :- dep("neg", X, _).
negated(X) :- dep("advmod", X, L), token(L, _, "less", "RBR", _).

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
% Sentiment propagator.
respected(X, xfIsRespected(V, T)) :- isVerb(V), dep(T, V, X), not negated(V).
respected(X, xfInvRsp(xfIsRespected(V, T))) :- isVerb(V), dep(T, V, X), negated(V).

removed(X, xfShouldBeRemoved(V, T)) :- isVerb(V), dep(T, V, X), not negated(V).
removed(X, xfInvRsp(xfShouldBeRemoved(V, T))) :- isVerb(V), dep(T, V, X), negated(V).

entitySentimentByModifier(X, xfSenti(N)) :- isa(X, N).
entitySentimentByModifier(X, xfSenti(J)) :- modify(J, X), not negated(J).
entitySentimentByModifier(X, xfInvSenti(xfSenti(J))) :- modify(J, X), negated(J).

entitySentimentByModifier(X, S) :- isa(X, Xi), not negated(Xi), entitySentimentByModifier(Xi, S).
entitySentimentByModifier(X, xfInvSenti(S)) :- isa(X, Xi), negated(Xi), entitySentimentByModifier(Xi, S).

entitySentimentByEventSlot(X, positive) :- canDo(X).
entitySentimentByEventSlot(X, negative) :- cantDo(X).
entitySentimentByEventSlot(X, negative) :- hasTooMuch(X).
entitySentimentByEventSlot(X, xfSenti(Y)) :- has(X, Y).
entitySentimentByEventSlot(X, xfSlotSenti(V, T)) :- isVerb(V), dep(T, V, X), not negated(V).
entitySentimentByEventSlot(X, xfInvSenti(xfSlotSenti(V, T))) :- isVerb(V), dep(T, V, X), negated(V).

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
