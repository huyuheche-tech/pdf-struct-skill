## Abstract

We study whether a sparse attention encoder improves sample efficiency in low-resource machine translation. Across 12 runs on three datasets, the encoder reduced validation error by 18.4% relative to a dense baseline. The gain is largest when only 5% of labels are available.

## Introduction

Low-resource translation is limited by scarce parallel data. Prior work reports that dense attention overfits when training sets are small. We ask whether a sparse attention pattern can preserve accuracy under the same training budget.

## Method

We train a 6-layer transformer with a sparse attention encoder on WMT-14 En-De, IWSLT-14 De-En and OPUS-100. All models use a batch size of 64 and a learning rate of 0.001 for 40 epochs. The decoder is frozen so that the comparison isolates the encoder change.

## Results

On all three datasets, the sparse encoder lowers validation error, with a mean relative reduction of 18.4%. The improvement remains when only 5% of labels are used. A limitation is that we evaluate only translation tasks, so the result may not transfer to summarisation. Future work should test the encoder on summarisation and on morphologically rich languages.
