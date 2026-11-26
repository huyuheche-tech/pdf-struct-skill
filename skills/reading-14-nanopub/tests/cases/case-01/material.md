## Abstract

We introduce a calibration layer that rescales logits for frozen classifiers. The layer adds 2.1 points of expected calibration error improvement on ImageNet.

## Results

On ImageNet, the calibration layer reduces expected calibration error from 8.4% to 6.3%. Under distribution shift (ImageNet-C, severity 3), the layer keeps the error below 7.0%. The layer adds 0.4 ms per image at inference time. In most cases the gain persists when only 100 calibration samples are used.
