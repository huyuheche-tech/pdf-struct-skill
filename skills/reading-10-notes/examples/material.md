## Abstract

We test whether a linear probe can recover sentiment from frozen sentence embeddings. On three review datasets the probe reaches 91.2% accuracy, 3.1 points above a logistic baseline. The probe is trained for 20 epochs with a batch size of 128.

## Results

Accuracy is stable across all three datasets, and the gain persists when only 10% of training labels are used. A limitation is that we evaluate English reviews only. Future work should extend the probe to multilingual review data.
