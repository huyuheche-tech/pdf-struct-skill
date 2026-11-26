# resnet.pdf

<!-- schema=pdf-struct/2 pages=12 column_template=2 sha256=1e0651b6810ecba34a3dbc5b5b0209226f889004607c1f203540a48d64e5a93a -->


<!-- ===== page 1 | columns=2 | gutters=[[288.0, 307.0]] -->
<!-- p1-b000 | type=heading | col=-1 | bbox=153.4,105.9,441.8,120.3 -->
## Deep Residual Learning for Image Recognition

<!-- p1-b001 | type=author | col=0 | bbox=136.4,152.4,195.2,164.3 -->
Kaiming He

<!-- p1-b002 | type=author | col=0 | bbox=222.1,152.4,296.8,164.3 -->
Xiangyu Zhang

<!-- p1-b003 | type=author | col=1 | bbox=323.7,152.4,391.1,164.3 -->
Shaoqing Ren

<!-- p1-b004 | type=author | col=1 | bbox=418.0,152.4,458.8,164.3 -->
Jian Sun

<!-- p1-b005 | type=affiliation | col=-1 | bbox=249.1,169.1,343.1,181.1 -->
Microsoft Research

<!-- p1-b006 | type=affiliation | col=-1 | bbox=195.5,184.8,399.7,202.1 -->
{kahe, v-xiangz, v-shren, jiansun}@microsoft.com

<!-- p1-b008 | type=heading | col=0 | bbox=146.0,225.2,190.5,237.2 -->
## Abstract

<!-- p1-b009 | type=body | col=0 | bbox=50.1,246.1,286.4,423.4 -->
Deeper neural networks are more difﬁcult to train. We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously. We explicitly reformulate the layers as learning residual functions with reference to the layer inputs, instead of learning unreferenced functions. We provide comprehensive empirical evidence showing that these residual networks are easier to optimize, and can gain accuracy from considerably increased depth. On the ImageNet dataset we evaluate residual nets with a depth of up to 152 layers—8× deeper than VGG nets [41] but still having lower complexity. An ensemble of these residual nets achieves 3.57% error on the ImageNet test set. This result won the 1st place on the ILSVRC 2015 classiﬁcation task. We also present analysis on CIFAR-10 with 100 and 1000 layers.

<!-- p1-b010 | type=body | col=0 | bbox=50.1,425.8,286.4,519.5 -->
The depth of representations is of central importance for many visual recognition tasks. Solely due to our extremely deep representations, we obtain a 28% relative improvement on the COCO object detection dataset. Deep residual nets are foundations of our submissions to ILSVRC & COCO 2015 competitions1, where we also won the 1st places on the tasks of ImageNet detection, ImageNet localization, COCO detection, and COCO segmentation.

<!-- p1-b011 | type=heading | col=0 | bbox=50.1,535.2,127.0,547.2 -->
## 1. Introduction

<!-- p1-b012 | type=body | col=0 | bbox=50.1,556.2,286.4,685.7 -->
Deep convolutional neural networks [22, 21] have led to a series of breakthroughs for image classiﬁcation [21, 50, 40]. Deep networks naturally integrate low/mid/highlevel features [50] and classiﬁers in an end-to-end multilayer fashion, and the “levels” of features can be enriched by the number of stacked layers (depth). Recent evidence [41, 44] reveals that network depth is of crucial importance, and the leading results [41, 44, 13, 16] on the challenging ImageNet dataset [36] all exploit “very deep” [41] models, with a depth of sixteen [41] to thirty [16]. Many other nontrivial visual recognition tasks [8, 12, 7, 32, 27] have also

<!-- p1-b013 | type=footnote | col=0 | bbox=61.0,695.7,260.3,704.5 -->
1http://image-net.org/challenges/LSVRC/2015/

<!-- p1-b014 | type=footnote | col=0 | bbox=50.1,697.3,286.4,712.8 -->
and http://mscoco.org/dataset/#detections-challenge2015.

<!-- p1-b015 | type=figure | col=1 | bbox=308.9,224.4,545.1,346.7 -->
![Figure 1. Training error (left) and test error (right) on CIFAR-10 with 20-layer and 56-layer “plain” networks. The deeper network has higher training error, and thus test error. Similar phenomena on ImageNet is presented in Fig. 4.](figures/F1.png)

<!-- p1-b019 | type=formula | col=1 | bbox=521.6,240.4,543.6,258.9 -->
