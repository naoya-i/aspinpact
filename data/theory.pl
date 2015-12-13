
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
% Basic theory.
1 {pronominalized(N, P): mention(N)} 1 :- pronoun(P).
dep(T, V, N) :- pronominalized(N, P), dep(T, V, P).

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
:~ pronominalized(N, P), dep(R1, E, N), dep(R2, E, P), R1 != R2. [1@1, wfDiffPred, N, P]
% :~ pronominalized(N, P), N<P. [1@1, wfAnaphora, N, P]

N<P :- pronominalized(N, P).

% Semantic feature.
:~ pronominalized(N, P), number(N, NUM), number(P, NUM). [1@1, wfNumberMatch, N, P]
:~ pronominalized(N, P), G != neutral, gender(N, G), gender(P, G). [1@1, wfGenderMatch, N, P]
% :~ pronominalized(N, P), S != neutral, entitySentimentByEventSlot(N, S), entitySentimentByModifier(P, S). [1@1, wfSentimentGuessMatch_ESM, N, P]
% :~ pronominalized(N, P), S != neutral, entitySentimentByModifier(N, S), entitySentimentByEventSlot(P, S). [1@1, wfSentimentGuessMatch_ESM, N, P]
% :~ pronominalized(N, P), S != neutral, entitySentimentByEventSlot(N, S), entitySentimentByEventSlot(P, S). [1@1, wfSentimentGuessMatch_ES, N, P]
% :~ pronominalized(N, P), S != neutral, entitySentimentByModifier(N, S), entitySentimentByModifier(P, S). [1@1, wfSentimentGuessMatch_M, N, P]
:~ pronominalized(N, P), respected(N, yes), entitySentimentByModifier(P, positive). [1@1, wfRespectSomethingPositive, N, P]
:~ pronominalized(N, P), respected(N, yes), entitySentimentByEventSlot(P, positive). [1@1, wfRespectSomethingPositive, N, P]
:~ pronominalized(N, P), removed(N, yes), entitySentimentByModifier(P, negative). [1@1, wfRemoveSomethingNegative, N, P]
:~ pronominalized(N, P), removed(N, yes), entitySentimentByEventSlot(P, negative). [1@1, wfRemoveSomethingNegative, N, P]
:~ pronominalized(N, P), entitySentimentByEventSlot(N, S), entitySentimentByEventSlot(P, S), S != neutral. [1@1, wfSentimentFromESmatch, N, P]

:~ pronominalized(N, P), dep(T, VP, P). [1@1, wfSelpref, N, P, VP, T]
:~ pronominalized(N, P), dep(TN, VN, N), VN!=VP, dep(TP, VP, P). [1@1, wfESA, N, P, VN, TN, VP, TP]
%:~ pronominalized(N, P), modify(J, P). [1@1, wfGoogle, N, P, J]
