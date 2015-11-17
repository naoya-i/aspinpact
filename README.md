# aspinpact
Answer Set Programming-based implementation for Interpretation as Abduction

## Inference

    echo "I went to a school." > test.txt
    make test.sys.interp

## Learning

Prepare input files (input logical forms). Let us say ~/tmp/learning_*.pl

    python src/learn.py \
        --weight ~/tmp/weight.tsv \
        --input ~/tmp/learning_0.pl \
        --gold ~/tmp/learning_0.gold.interp

   
