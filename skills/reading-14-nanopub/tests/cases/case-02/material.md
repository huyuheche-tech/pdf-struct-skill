## Abstract

We evaluate a reranker for passage retrieval. The reranker is trained on 50k query-passage pairs.

## Results

On MS MARCO, the reranker lifts nDCG@10 from 0.312 to 0.358. Removing the reranker costs 4.6 points, so the gain comes from reranking rather than from a larger index. In most cases the reranker keeps its advantage when only 1,000 training pairs are used.
