
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

mention(N) :- isNoun(N), not dep("compound", _, N).
pronoun(P) :- isPronoun(P).

number(I, xfNumber(I)) :- mention(I).
number(I, xfNumber(I)) :- pronoun(I).
gender(I, xfGender(I)) :- mention(I).
gender(I, xfGender(I)) :- pronoun(I).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Modifiers.

% He is cute, cool guy.
modify(J, N) :- isAdj(J), dep("nsubj", J, N).
modify(J, N) :- isAdj(J), dep("amod", N, J).

% He looks sad. (xcomp(look, sad) + nsubj(look, he))
modify(J, N) :- isAdj(J), dep("xcomp", V, J), dep("nsubj", V, N).

    
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% ISA.

% He wants to be a friend. (nsubj(want, he) + xcomp(want, friend))
isa(X, Xi) :- dep("nsubj", V, X), dep("xcomp", V, Xi).

% He is a player. (nsubj(player, he))
isa(X, Xi) :- dep("nsubj", Xi, X), isNoun(Xi).

% He is perceived as a good artist. (nsubjpass(perceived, he) + nmod:as(perceived, artist))
isa(X, Xi) :- dep("nsubjpass", V, X), dep("nmod:as", V, Xi), isNoun(Xi).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Sentiment propagator.

entitySentiment(X, S) :- modify(J, X), senti(J, S).
entitySentiment(X, S) :- isa(X, Xi), entitySentiment(Xi, S).
entityEventSlotSentiment(X, S) :- isVerb(V), dep(T, V, X), slotSenti(V, T, S).

senti(I, xfSenti(I)) :- token(I, _, _, _, _).
slotSenti(V, T, xfSlotSenti(V, T)) :- token(V, _, _, _, _), dep(T, V, _).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Display.

#show.

#show token/5.
#show dep/3.

#show mention/1.
#show pronoun/1.

#show number/2.
#show gender/2.
#show entitySentiment/2.
#show entityEventSlotSentiment/2.
