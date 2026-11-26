## Abstract

We present a retrieval-augmented reader for open-domain question answering. The reader improves exact-match accuracy by 4.2 points over a closed-book baseline on Natural Questions. All gains reported here are for English only.

## Introduction

Closed-book readers must store all evidence in their parameters. Retrieval lets a model condition on passages that are selected at query time. We ask how much of the gain comes from retrieval rather than from a larger reader.

## Method

We build an index over the 2018 Wikipedia dump and retrieve 20 passages per question. The reader is a 12-layer encoder trained for 3 epochs with a batch size of 32. Retrieval is frozen during reader training.

## Results

The retrieval-augmented reader reaches 41.7 exact match on Natural Questions, 4.2 points above the closed-book baseline. Ablations show that removing retrieval costs 9.1 points. We do not evaluate languages other than English.
