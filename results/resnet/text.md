# resnet.pdf

<!-- schema=pdf-struct/2 pages=12 column_template=2 sha256=1e0651b6810ecba34a3dbc5b5b0209226f889004607c1f203540a48d64e5a93a -->


<!-- ===== page 1 | columns=2 | gutters=[[288.0, 307.0]] -->
<!-- p1-b000 | type=heading | col=-1 | bbox=153.4,105.9,441.8,120.3 -->
## Deep Residual Learning for Image Recognition

<!-- p1-b001 | type=author | col=-1 | bbox=222.1,152.4,296.8,164.3 -->
Xiangyu Zhang

<!-- p1-b002 | type=author | col=0 | bbox=136.4,152.4,195.2,164.3 -->
Kaiming He

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
$$ 56-layer 20-layer $$

<!-- p1-b023 | type=formula | col=1 | bbox=400.3,263.2,422.2,285.3 -->
$$ 56-layer 20-layer $$

<!-- p1-b042 | type=caption | col=1 | bbox=308.9,304.9,545.1,346.7 -->
Figure 1. Training error (left) and test error (right) on CIFAR-10 with 20-layer and 56-layer “plain” networks. The deeper network has higher training error, and thus test error. Similar phenomena on ImageNet is presented in Fig. 4.

<!-- p1-b043 | type=body | col=1 | bbox=308.9,362.8,472.5,372.8 -->
greatly beneﬁted from very deep models.

<!-- p1-b044 | type=body | col=1 | bbox=308.9,376.6,545.1,494.3 -->
Driven by the signiﬁcance of depth, a question arises: Is learning better networks as easy as stacking more layers? An obstacle to answering this question was the notorious problem of vanishing/exploding gradients [1, 9], which hamper convergence from the beginning. This problem, however, has been largely addressed by normalized initialization [23, 9, 37, 13] and intermediate normalization layers [16], which enable networks with tens of layers to start converging for stochastic gradient descent (SGD) with backpropagation [22].

<!-- p1-b045 | type=body | col=1 | bbox=308.9,498.2,545.1,591.9 -->
When deeper networks are able to start converging, a degradation problem has been exposed: with the network depth increasing, accuracy gets saturated (which might be unsurprising) and then degrades rapidly. Unexpectedly, such degradation is not caused by overﬁtting, and adding more layers to a suitably deep model leads to higher training error, as reported in [11, 42] and thoroughly veriﬁed by our experiments. Fig. 1 shows a typical example.

<!-- p1-b046 | type=body | col=1 | bbox=308.9,595.9,545.1,713.4 -->
The degradation (of training accuracy) indicates that not all systems are similarly easy to optimize. Let us consider a shallower architecture and its deeper counterpart that adds more layers onto it. There exists a solution by construction to the deeper model: the added layers are identity mapping, and the other layers are copied from the learned shallower model. The existence of this constructed solution indicates that a deeper model should produce no higher training error than its shallower counterpart. But experiments show that our current solvers on hand are unable to ﬁnd solutions that


<!-- ===== page 2 | columns=2 | gutters=[[288.0, 307.0]] -->
<!-- p2-b000 | type=body | col=0 | bbox=142.9,78.4,148.5,87.7 -->
x

<!-- p2-b001 | type=figure | col=0 | bbox=86.6,84.9,249.9,167.1 -->
![Figure 2. Residual learning: a building block.](figures/F2.png)

<!-- p2-b009 | type=caption | col=0 | bbox=86.6,146.2,249.9,167.1 -->
Figure 2. Residual learning: a building block.

<!-- p2-b010 | type=body | col=0 | bbox=50.1,182.2,286.4,204.1 -->
are comparably good or better than the constructed solution (or unable to do so in feasible time).

<!-- p2-b011 | type=body | col=0 | bbox=50.1,207.5,286.4,265.3 -->
In this paper, we address the degradation problem by introducing a deep residual learning framework. Instead of hoping each few stacked layers directly ﬁt a desired underlying mapping, we explicitly let these layers ﬁt a residual mapping. Formally, denoting the desired

<!-- p2-b012 | type=body | col=0 | bbox=50.1,267.1,286.4,308.3 -->
underlying mapping as H(x), we let the stacked nonlinear layers ﬁt another mapping of F(x) := H(x)−x. The original mapping is recast into F(x)+x. We hypothesize that it

<!-- p2-b013 | type=body | col=0 | bbox=50.1,303.1,286.4,360.9 -->
is easier to optimize the residual mapping than to optimize the original, unreferenced mapping. To the extreme, if an identity mapping were optimal, it would be easier to push the residual to zero than to ﬁt an identity mapping by a stack of nonlinear layers.

<!-- p2-b014 | type=body | col=0 | bbox=62.1,364.2,286.4,381.5 -->
The formulation of F(x)+x can be realized by feedfor-

<!-- p2-b015 | type=body | col=0 | bbox=50.1,376.3,286.4,493.9 -->
ward neural networks with “shortcut connections” (Fig. 2). Shortcut connections [2, 34, 49] are those skipping one or more layers. In our case, the shortcut connections simply perform identity mapping, and their outputs are added to the outputs of the stacked layers (Fig. 2). Identity shortcut connections add neither extra parameter nor computational complexity. The entire network can still be trained end-to-end by SGD with backpropagation, and can be easily implemented using common libraries (e.g., Caffe [19]) without modifying the solvers.

<!-- p2-b016 | type=body | col=0 | bbox=50.1,497.3,286.4,591.0 -->
We present comprehensive experiments on ImageNet [36] to show the degradation problem and evaluate our method. We show that: 1) Our extremely deep residual nets are easy to optimize, but the counterpart “plain” nets (that simply stack layers) exhibit higher training error when the depth increases; 2) Our deep residual nets can easily enjoy accuracy gains from greatly increased depth, producing results substantially better than previous networks.

<!-- p2-b017 | type=body | col=0 | bbox=50.1,594.4,286.4,652.2 -->
Similar phenomena are also shown on the CIFAR-10 set [20], suggesting that the optimization difﬁculties and the effects of our method are not just akin to a particular dataset. We present successfully trained models on this dataset with over 100 layers, and explore models with over 1000 layers.

<!-- p2-b018 | type=body | col=0 | bbox=50.1,655.6,286.4,701.5 -->
On the ImageNet classiﬁcation dataset [36], we obtain excellent results by extremely deep residual nets. Our 152layer residual net is the deepest network ever presented on ImageNet, while still having lower complexity than VGG

<!-- p2-b019 | type=body | col=0 | bbox=98.8,703.4,286.4,713.4 -->
Our ensemble has 3.57% top-5 error on the

<!-- p2-b020 | type=body | col=0 | bbox=50.1,703.4,89.7,713.4 -->
nets [41].

<!-- p2-b021 | type=body | col=1 | bbox=308.9,74.2,545.1,180.0 -->
ImageNet test set, and won the 1st place in the ILSVRC 2015 classiﬁcation competition. The extremely deep representations also have excellent generalization performance on other recognition tasks, and lead us to further win the 1st places on: ImageNet detection, ImageNet localization, COCO detection, and COCO segmentation in ILSVRC & COCO 2015 competitions. This strong evidence shows that the residual learning principle is generic, and we expect that it is applicable in other vision and non-vision problems.

<!-- p2-b022 | type=heading | col=1 | bbox=308.9,195.1,392.0,207.0 -->
## 2. Related Work

<!-- p2-b023 | type=body | col=1 | bbox=308.9,216.4,545.1,226.5 -->
Residual Representations. In image recognition, VLAD

<!-- p2-b024 | type=body | col=1 | bbox=308.9,228.5,545.1,310.2 -->
[18] is a representation that encodes by the residual vectors with respect to a dictionary, and Fisher Vector [30] can be formulated as a probabilistic version [18] of VLAD. Both of them are powerful shallow representations for image retrieval and classiﬁcation [4, 48]. For vector quantization, encoding residual vectors [17] is shown to be more effective than encoding original vectors.

<!-- p2-b025 | type=body | col=1 | bbox=308.9,313.1,545.1,454.6 -->
In low-level vision and computer graphics, for solving Partial Differential Equations (PDEs), the widely used Multigrid method [3] reformulates the system as subproblems at multiple scales, where each subproblem is responsible for the residual solution between a coarser and a ﬁner scale. An alternative to Multigrid is hierarchical basis preconditioning [45, 46], which relies on variables that represent residual vectors between two scales. It has been shown [3, 45, 46] that these solvers converge much faster than standard solvers that are unaware of the residual nature of the solutions. These methods suggest that a good reformulation or preconditioning can simplify the optimization.

<!-- p2-b026 | type=body | col=1 | bbox=308.9,463.3,545.1,473.4 -->
Shortcut Connections. Practices and theories that lead to

<!-- p2-b027 | type=body | col=1 | bbox=308.9,475.4,545.1,592.9 -->
shortcut connections [2, 34, 49] have been studied for a long time. An early practice of training multi-layer perceptrons (MLPs) is to add a linear layer connected from the network input to the output [34, 49]. In [44, 24], a few intermediate layers are directly connected to auxiliary classiﬁers for addressing vanishing/exploding gradients. The papers of [39, 38, 31, 47] propose methods for centering layer responses, gradients, and propagated errors, implemented by shortcut connections. In [44], an “inception” layer is composed of a shortcut branch and a few deeper branches.

<!-- p2-b028 | type=body | col=1 | bbox=308.9,595.9,545.1,713.4 -->
Concurrent with our work, “highway networks” [42, 43] present shortcut connections with gating functions [15]. These gates are data-dependent and have parameters, in contrast to our identity shortcuts that are parameter-free. When a gated shortcut is “closed” (approaching zero), the layers in highway networks represent non-residual functions. On the contrary, our formulation always learns residual functions; our identity shortcuts are never closed, and all information is always passed through, with additional residual functions to be learned. In addition, high-


<!-- ===== page 3 | columns=2 | gutters=[[288.0, 307.0]] -->
<!-- p3-b000 | type=body | col=0 | bbox=50.1,74.4,286.4,96.3 -->
way networks have not demonstrated accuracy gains with extremely increased depth (e.g., over 100 layers).

<!-- p3-b001 | type=heading | col=0 | bbox=50.1,109.0,185.4,120.9 -->
## 3. Deep Residual Learning

<!-- p3-b002 | type=heading | col=0 | bbox=50.1,128.8,155.9,139.7 -->
### 3.1. Residual Learning

<!-- p3-b003 | type=body | col=0 | bbox=62.1,147.5,286.4,164.8 -->
Let us consider H(x) as an underlying mapping to be

<!-- p3-b004 | type=body | col=0 | bbox=50.1,159.6,286.4,169.6 -->
ﬁt by a few stacked layers (not necessarily the entire net),

<!-- p3-b005 | type=body | col=0 | bbox=50.1,171.6,286.4,181.6 -->
with x denoting the inputs to the ﬁrst of these layers. If one

<!-- p3-b006 | type=body | col=0 | bbox=50.1,183.5,286.4,217.4 -->
hypothesizes that multiple nonlinear layers can asymptotically approximate complicated functions2, then it is equivalent to hypothesize that they can asymptotically approxi-

<!-- p3-b007 | type=body | col=0 | bbox=50.1,219.2,286.4,236.5 -->
mate the residual functions, i.e., H(x) −x (assuming that

<!-- p3-b008 | type=body | col=0 | bbox=50.1,231.3,286.4,241.3 -->
the input and output are of the same dimensions). So

<!-- p3-b009 | type=body | col=0 | bbox=50.1,243.1,286.4,260.4 -->
rather than expect stacked layers to approximate H(x), we

<!-- p3-b010 | type=body | col=0 | bbox=50.1,255.2,286.4,265.2 -->
explicitly let these layers approximate a residual function

<!-- p3-b011 | type=body | col=0 | bbox=50.1,267.0,286.4,296.3 -->
F(x) := H(x) −x. The original function thus becomes F(x)+x. Although both forms should be able to asymptot-

<!-- p3-b012 | type=body | col=0 | bbox=50.1,291.1,286.4,313.0 -->
ically approximate the desired functions (as hypothesized), the ease of learning might be different.

<!-- p3-b013 | type=body | col=0 | bbox=50.1,315.1,286.4,444.6 -->
This reformulation is motivated by the counterintuitive phenomena about the degradation problem (Fig. 1, left). As we discussed in the introduction, if the added layers can be constructed as identity mappings, a deeper model should have training error no greater than its shallower counterpart. The degradation problem suggests that the solvers might have difﬁculties in approximating identity mappings by multiple nonlinear layers. With the residual learning reformulation, if identity mappings are optimal, the solvers may simply drive the weights of the multiple nonlinear layers toward zero to approach identity mappings.

<!-- p3-b014 | type=body | col=0 | bbox=50.1,446.7,286.4,552.3 -->
In real cases, it is unlikely that identity mappings are optimal, but our reformulation may help to precondition the problem. If the optimal function is closer to an identity mapping than to a zero mapping, it should be easier for the solver to ﬁnd the perturbations with reference to an identity mapping, than to learn the function as a new one. We show by experiments (Fig. 7) that the learned residual functions in general have small responses, suggesting that identity mappings provide reasonable preconditioning.

<!-- p3-b015 | type=heading | col=0 | bbox=50.1,561.8,213.9,572.7 -->
### 3.2. Identity Mapping by Shortcuts

<!-- p3-b016 | type=body | col=0 | bbox=50.1,580.7,286.4,614.5 -->
We adopt residual learning to every few stacked layers. A building block is shown in Fig. 2. Formally, in this paper we consider a building block deﬁned as:

<!-- p3-b017 | type=formula | col=0 | bbox=123.5,626.5,213.0,643.8 -->
$$ y = F(x, {Wi}) + x. $$

<!-- p3-b018 | type=body | col=0 | bbox=274.8,626.7,286.4,636.6 -->
(1)

<!-- p3-b019 | type=body | col=0 | bbox=50.1,648.8,286.4,658.9 -->
Here x and y are the input and output vectors of the lay-

<!-- p3-b020 | type=body | col=0 | bbox=119.5,660.5,286.4,677.9 -->
The function F(x, {Wi}) represents the

<!-- p3-b021 | type=body | col=0 | bbox=50.1,660.8,286.4,682.7 -->
ers considered. residual mapping to be learned. For the example in Fig. 2

<!-- p3-b022 | type=body | col=0 | bbox=50.1,684.5,286.4,701.8 -->
that has two layers, F = W2σ(W1x) in which σ denotes

<!-- p3-b023 | type=footnote | col=0 | bbox=61.0,703.6,257.8,712.9 -->
2This hypothesis, however, is still an open question. See [28].

<!-- p3-b024 | type=body | col=1 | bbox=308.9,74.4,545.1,84.4 -->
ReLU [29] and the biases are omitted for simplifying no-

<!-- p3-b025 | type=body | col=1 | bbox=308.9,86.2,545.1,103.5 -->
tations. The operation F + x is performed by a shortcut

<!-- p3-b026 | type=body | col=1 | bbox=308.9,98.3,545.1,108.3 -->
connection and element-wise addition. We adopt the sec-

<!-- p3-b027 | type=body | col=1 | bbox=308.9,110.0,537.2,120.3 -->
ond nonlinearity after the addition (i.e., σ(y), see Fig. 2).

<!-- p3-b028 | type=body | col=1 | bbox=308.9,122.5,545.1,204.2 -->
The shortcut connections in Eqn.(1) introduce neither extra parameter nor computation complexity. This is not only attractive in practice but also important in our comparisons between plain and residual networks. We can fairly compare plain/residual networks that simultaneously have the same number of parameters, depth, width, and computational cost (except for the negligible element-wise addition).

<!-- p3-b029 | type=body | col=1 | bbox=320.8,206.2,545.1,223.5 -->
The dimensions of x and F must be equal in Eqn.(1).

<!-- p3-b030 | type=body | col=1 | bbox=308.9,218.2,545.1,252.2 -->
If this is not the case (e.g., when changing the input/output channels), we can perform a linear projection Ws by the shortcut connections to match the dimensions:

<!-- p3-b031 | type=formula | col=1 | bbox=375.4,264.4,478.6,281.8 -->
$$ y = F(x, {Wi}) + Wsx. $$

<!-- p3-b032 | type=body | col=1 | bbox=308.9,264.7,545.1,334.4 -->
(2) We can also use a square matrix Ws in Eqn.(1). But we will show by experiments that the identity mapping is sufﬁcient for addressing the degradation problem and is economical, and thus Ws is only used when matching dimensions.

<!-- p3-b033 | type=body | col=1 | bbox=308.9,335.0,545.1,388.1 -->
The form of the residual function F is ﬂexible. Experiments in this paper involve a function F that has two or three layers (Fig. 5), while more layers are possible. But if F has only a single layer, Eqn.(1) is similar to a linear layer:

<!-- p3-b034 | type=body | col=1 | bbox=308.9,382.7,545.1,393.5 -->
y = W1x + x, for which we have not observed advantages.

<!-- p3-b035 | type=body | col=1 | bbox=308.9,395.1,545.1,417.1 -->
We also note that although the above notations are about fully-connected layers for simplicity, they are applicable to

<!-- p3-b036 | type=body | col=1 | bbox=308.9,418.8,545.1,436.2 -->
convolutional layers. The function F(x, {Wi}) can repre-

<!-- p3-b037 | type=body | col=1 | bbox=308.9,431.0,545.1,452.9 -->
sent multiple convolutional layers. The element-wise addition is performed on two feature maps, channel by channel.

<!-- p3-b038 | type=heading | col=1 | bbox=308.9,462.8,434.9,473.7 -->
### 3.3. Network Architectures

<!-- p3-b039 | type=body | col=1 | bbox=308.9,481.8,545.1,515.7 -->
We have tested various plain/residual nets, and have observed consistent phenomena. To provide instances for discussion, we describe two models for ImageNet as follows.

<!-- p3-b040 | type=body | col=1 | bbox=308.9,523.8,545.1,533.8 -->
Plain Network. Our plain baselines (Fig. 3, middle) are

<!-- p3-b041 | type=body | col=1 | bbox=308.9,535.8,545.1,665.4 -->
mainly inspired by the philosophy of VGG nets [41] (Fig. 3, left). The convolutional layers mostly have 3×3 ﬁlters and follow two simple design rules: (i) for the same output feature map size, the layers have the same number of ﬁlters; and (ii) if the feature map size is halved, the number of ﬁlters is doubled so as to preserve the time complexity per layer. We perform downsampling directly by convolutional layers that have a stride of 2. The network ends with a global average pooling layer and a 1000-way fully-connected layer with softmax. The total number of weighted layers is 34 in Fig. 3 (middle).

<!-- p3-b042 | type=body | col=1 | bbox=308.9,667.4,545.1,713.4 -->
It is worth noticing that our model has fewer ﬁlters and lower complexity than VGG nets [41] (Fig. 3, left). Our 34layer baseline has 3.6 billion FLOPs (multiply-adds), which is only 18% of VGG-19 (19.6 billion FLOPs).


<!-- ===== page 4 | columns=2 | gutters=[[288.0, 307.0]] -->
<!-- p4-b000 | type=footnote | col=0 | bbox=85.9,77.5,110.5,85.4 -->
VGG-19

<!-- p4-b001 | type=footnote | col=0 | bbox=146.9,77.5,190.2,85.4 -->
34-layer plain

<!-- p4-b002 | type=footnote | col=0 | bbox=212.4,77.5,265.3,85.4 -->
34-layer residual

<!-- p4-b003 | type=footnote | col=0 | bbox=92.1,91.4,104.2,96.3 -->
image

<!-- p4-b004 | type=footnote | col=0 | bbox=162.3,91.4,174.3,96.3 -->
image

<!-- p4-b005 | type=footnote | col=0 | bbox=232.4,91.4,244.5,96.3 -->
image

<!-- p4-b006 | type=footnote | col=0 | bbox=52.7,101.1,67.4,106.0 -->
output

<!-- p4-b008 | type=footnote | col=0 | bbox=50.9,106.9,68.1,111.9 -->
size: 224

<!-- p4-b011 | type=footnote | col=0 | bbox=50.9,133.7,68.1,144.4 -->
output size: 112

<!-- p4-b012 | type=footnote | col=0 | bbox=84.2,142.1,111.5,159.7 -->
3x3 conv, 128 3x3 conv, 128

<!-- p4-b018 | type=footnote | col=0 | bbox=52.1,171.4,67.4,182.2 -->
output size: 56

<!-- p4-b038 | type=footnote | col=0 | bbox=52.1,260.3,67.4,271.1 -->
output size: 28

<!-- p4-b057 | type=footnote | col=0 | bbox=52.7,354.7,67.4,359.6 -->
output

<!-- p4-b058 | type=footnote | col=0 | bbox=90.1,357.6,105.7,362.6 -->
pool, /2

<!-- p4-b061 | type=footnote | col=0 | bbox=52.1,360.6,66.9,365.5 -->
size: 14

<!-- p4-b088 | type=footnote | col=0 | bbox=52.7,506.9,67.4,511.8 -->
output

<!-- p4-b089 | type=footnote | col=0 | bbox=90.2,509.8,105.8,514.7 -->
pool, /2

<!-- p4-b092 | type=footnote | col=0 | bbox=53.3,512.7,65.6,517.7 -->
size: 7

<!-- p4-b103 | type=figure | col=0 | bbox=50.1,580.5,286.4,685.7 -->
![Figure 3. Example network architectures for ImageNet. Left: the VGG-19 model [41\] (19.6 billion FLOPs) as a reference. Middle: a plain network with 34 parameter layers (3.6 billion FLOPs). Right: a residual network with 34 parameter layers (3.6 billion FLOPs). The dotted shortcuts increase dimensions. Table 1 shows](figures/F3.png)

<!-- p4-b113 | type=caption | col=0 | bbox=50.1,632.8,286.4,685.7 -->
Figure 3. Example network architectures for ImageNet. Left: the VGG-19 model [41] (19.6 billion FLOPs) as a reference. Middle: a plain network with 34 parameter layers (3.6 billion FLOPs). Right: a residual network with 34 parameter layers (3.6 billion FLOPs). The dotted shortcuts increase dimensions. Table 1 shows

<!-- p4-b114 | type=body | col=0 | bbox=50.1,687.7,162.7,696.7 -->
more details and other variants.

<!-- p4-b115 | type=body | col=1 | bbox=308.9,74.3,545.1,84.4 -->
Residual Network. Based on the above plain network, we

<!-- p4-b116 | type=body | col=1 | bbox=308.9,86.4,545.1,227.8 -->
insert shortcut connections (Fig. 3, right) which turn the network into its counterpart residual version. The identity shortcuts (Eqn.(1)) can be directly used when the input and output are of the same dimensions (solid line shortcuts in Fig. 3). When the dimensions increase (dotted line shortcuts in Fig. 3), we consider two options: (A) The shortcut still performs identity mapping, with extra zero entries padded for increasing dimensions. This option introduces no extra parameter; (B) The projection shortcut in Eqn.(2) is used to match dimensions (done by 1×1 convolutions). For both options, when the shortcuts go across feature maps of two sizes, they are performed with a stride of 2.

<!-- p4-b117 | type=heading | col=1 | bbox=308.9,236.1,402.9,247.1 -->
### 3.4. Implementation

<!-- p4-b118 | type=body | col=1 | bbox=308.9,254.9,545.1,420.3 -->
Our implementation for ImageNet follows the practice in [21, 41]. The image is resized with its shorter side randomly sampled in [256, 480] for scale augmentation [41]. A 224×224 crop is randomly sampled from an image or its horizontal ﬂip, with the per-pixel mean subtracted [21]. The standard color augmentation in [21] is used. We adopt batch normalization (BN) [16] right after each convolution and before activation, following [16]. We initialize the weights as in [13] and train all plain/residual nets from scratch. We use SGD with a mini-batch size of 256. The learning rate starts from 0.1 and is divided by 10 when the error plateaus, and the models are trained for up to 60 × 104 iterations. We use a weight decay of 0.0001 and a momentum of 0.9. We do not use dropout [14], following the practice in [16].

<!-- p4-b119 | type=body | col=1 | bbox=308.9,422.3,545.1,487.2 -->
In testing, for comparison studies we adopt the standard 10-crop testing [21]. For best results, we adopt the fullyconvolutional form as in [41, 13], and average the scores at multiple scales (images are resized such that the shorter side is in {224, 256, 384, 480, 640}).

<!-- p4-b120 | type=heading | col=1 | bbox=308.9,491.6,385.9,503.6 -->
## 4. Experiments

<!-- p4-b121 | type=heading | col=1 | bbox=308.9,511.3,439.1,522.3 -->
### 4.1. ImageNet Classiﬁcation

<!-- p4-b122 | type=body | col=1 | bbox=308.9,530.1,545.1,599.8 -->
We evaluate our method on the ImageNet 2012 classiﬁcation dataset [36] that consists of 1000 classes. The models are trained on the 1.28 million training images, and evaluated on the 50k validation images. We also obtain a ﬁnal result on the 100k test images, reported by the test server. We evaluate both top-1 and top-5 error rates.

<!-- p4-b123 | type=body | col=1 | bbox=308.9,607.7,545.1,617.8 -->
Plain Networks. We ﬁrst evaluate 18-layer and 34-layer

<!-- p4-b124 | type=body | col=1 | bbox=308.9,619.8,545.1,653.6 -->
plain nets. The 34-layer plain net is in Fig. 3 (middle). The 18-layer plain net is of a similar form. See Table 1 for detailed architectures.

<!-- p4-b125 | type=body | col=1 | bbox=308.9,655.6,545.1,713.4 -->
The results in Table 2 show that the deeper 34-layer plain net has higher validation error than the shallower 18-layer plain net. To reveal the reasons, in Fig. 4 (left) we compare their training/validation errors during the training procedure. We have observed the degradation problem - the


<!-- ===== page 5 | columns=2 | gutters=[[288.0, 307.0]] -->
<!-- p5-b000 | type=table | col=-1 | bbox=127.9,73.8,467.3,216.7 -->
[table T1]
layer name | output size | 18-layer | 34-layer | 50-layer | 101-layer | 152-layer
conv1 | 112×112 |  |  | 7×7, 64, stride 2 |  | 
 |  |  |  | 3×3 max pool, stride 2 |  | 
conv2 x | 56×56 | 3×3, 64
×2
3×3, 64 | 3×3, 64
×3
3×3, 64 |  1×1, 64 
3×3, 64 ×3

1×1, 256 |  1×1, 64 
3×3, 64 ×3

1×1, 256 |  1×1, 64 
3×3, 64 ×3

1×1, 256
conv3 x | 28×28 | 3×3, 128
×2
3×3, 128 | 3×3, 128
×4
3×3, 128 |  1×1, 128 
3×3, 128 ×4

1×1, 512 |  1×1, 128 
3×3, 128 ×4

1×1, 512 |  1×1, 128 
3×3, 128 ×8

1×1, 512
conv4 x | 14×14 | 3×3, 256
×2
3×3, 256 | 3×3, 256
×6
3×3, 256 |   1×1, 256
3×3, 256 ×6

1×1, 1024 |   1×1, 256
3×3, 256 ×23

1×1, 1024 |   1×1, 256
3×3, 256 ×36

1×1, 1024
conv5 x | 7×7 | 3×3, 512
×2
3×3, 512 | 3×3, 512
×3
3×3, 512 |  1×1, 512 
3×3, 512 ×3

1×1, 2048 |  1×1, 512 
3×3, 512 ×3

1×1, 2048 |  1×1, 512 
3×3, 512 ×3

1×1, 2048
 | 1×1 |  | average pool, 1000-d fc, softmax |  |  | 
FLOPs |  | 1.8×109 | 3.6×109 | 3.8×109 | 7.6×109 | 11.3×109
 | 
 | 
 | 
 | 
 | 
 | 
 | 
 | 
 | 
 | 
 | 
 | 
 | 
 | 
 | 
 | 

<!-- p5-b001 | type=caption | col=-1 | bbox=50.1,224.7,545.1,244.6 -->
Table 1. Architectures for ImageNet. Building blocks are shown in brackets (see also Fig. 5), with the numbers of blocks stacked. Downsampling is performed by conv3 1, conv4 1, and conv5 1 with a stride of 2.

<!-- p5-b002 | type=figure | col=-1 | bbox=50.1,251.4,545.1,401.3 -->
![Figure 4. Training on ImageNet. Thin curves denote training error, and bold curves denote validation error of the center crops. Left: plain](figures/F4.png)

<!-- p5-b010 | type=formula | col=0 | bbox=115.8,353.1,142.7,371.1 -->
$$ plain-18 plain-34 $$

<!-- p5-b036 | type=caption | col=-1 | bbox=50.1,392.3,545.1,401.3 -->
Figure 4. Training on ImageNet. Thin curves denote training error, and bold curves denote validation error of the center crops. Left: plain

<!-- p5-b037 | type=body | col=-1 | bbox=50.1,403.3,545.1,412.3 -->
networks of 18 and 34 layers. Right: ResNets of 18 and 34 layers. In this plot, the residual networks have no extra parameter compared to

<!-- p5-b038 | type=body | col=0 | bbox=50.1,414.3,135.5,423.3 -->
their plain counterparts.

<!-- p5-b039 | type=table | col=0 | bbox=101.5,445.7,235.0,478.2 -->
[table T2]
 | plain | ResNet
18 layers | 27.94 | 27.88
34 layers | 28.54 | 25.03

<!-- p5-b040 | type=body | col=0 | bbox=50.1,469.5,286.4,516.5 -->
28.54 Table 2. Top-1 error (%, 10-crop testing) on ImageNet validation. Here the ResNets have no extra parameter compared to their plain counterparts. Fig. 4 shows the training procedures.

<!-- p5-b041 | type=body | col=0 | bbox=50.1,544.7,286.4,590.7 -->
34-layer plain net has higher training error throughout the whole training procedure, even though the solution space of the 18-layer plain network is a subspace of that of the 34-layer one.

<!-- p5-b042 | type=body | col=0 | bbox=50.1,595.7,286.4,713.4 -->
We argue that this optimization difﬁculty is unlikely to be caused by vanishing gradients. These plain networks are trained with BN [16], which ensures forward propagated signals to have non-zero variances. We also verify that the backward propagated gradients exhibit healthy norms with BN. So neither forward nor backward signals vanish. In fact, the 34-layer plain net is still able to achieve competitive accuracy (Table 3), suggesting that the solver works to some extent. We conjecture that the deep plain nets may have exponentially low convergence rates, which impact the

<!-- p5-b043 | type=body | col=1 | bbox=308.9,444.0,545.1,467.3 -->
reducing of the training error3. The reason for such optimization difﬁculties will be studied in the future.

<!-- p5-b044 | type=body | col=1 | bbox=308.9,475.2,545.1,485.2 -->
Residual Networks. Next we evaluate 18-layer and 34-

<!-- p5-b045 | type=body | col=1 | bbox=308.9,487.0,545.1,568.9 -->
layer residual nets (ResNets). The baseline architectures are the same as the above plain nets, expect that a shortcut connection is added to each pair of 3×3 ﬁlters as in Fig. 3 (right). In the ﬁrst comparison (Table 2 and Fig. 4 right), we use identity mapping for all shortcuts and zero-padding for increasing dimensions (option A). So they have no extra parameter compared to the plain counterparts.

<!-- p5-b046 | type=body | col=1 | bbox=308.9,570.9,545.1,664.5 -->
We have three major observations from Table 2 and Fig. 4. First, the situation is reversed with residual learning – the 34-layer ResNet is better than the 18-layer ResNet (by 2.8%). More importantly, the 34-layer ResNet exhibits considerably lower training error and is generalizable to the validation data. This indicates that the degradation problem is well addressed in this setting and we manage to obtain accuracy gains from increased depth.

<!-- p5-b047 | type=body | col=1 | bbox=320.8,666.5,545.1,676.5 -->
Second, compared to its plain counterpart, the 34-layer

<!-- p5-b048 | type=footnote | col=1 | bbox=308.9,684.7,545.1,712.9 -->
3We have experimented with more training iterations (3×) and still observed the degradation problem, suggesting that this problem cannot be feasibly addressed by simply using more iterations.


<!-- ===== page 6 | columns=2 | gutters=[[288.0, 307.0]] -->
<!-- p6-b000 | type=table | col=0 | bbox=88.5,72.1,248.0,208.8 -->
[table T3]
model | top-1 err. top-5 err.
VGG-16 [41]
GoogLeNet [44]
PReLU-net [13] | 28.07 9.33
- 9.15
24.27 7.38
plain-34
ResNet-34 A
ResNet-34 B
ResNet-34 C | 28.54 10.02
25.03 7.76
24.52 7.46
24.19 7.40
ResNet-50
ResNet-101
ResNet-152 | 22.85 6.71
21.75 6.05
21.43 5.71

<!-- p6-b001 | type=caption | col=0 | bbox=50.1,214.3,286.4,223.3 -->
Table 3. Error rates (%, 10-crop testing) on ImageNet validation.

<!-- p6-b002 | type=body | col=0 | bbox=50.1,225.3,286.4,245.2 -->
VGG-16 is based on our test. ResNet-50/101/152 are of option B that only uses projections for increasing dimensions.

<!-- p6-b003 | type=table | col=0 | bbox=60.0,255.1,276.5,389.3 -->
[table T4]
method | top-1 err. top-5 err.
VGG [41] (ILSVRC’14)
GoogLeNet [44] (ILSVRC’14) | 8.43† -
- 7.89
VGG [41] (v5)
PReLU-net [13]
BN-inception [16] | 24.4 7.1
21.59 5.71
21.99 5.81
ResNet-34 B
ResNet-34 C
ResNet-50
ResNet-101
ResNet-152 | 21.84 5.71
21.53 5.60
20.74 5.25
19.87 4.60
19.38 4.49

<!-- p6-b004 | type=caption | col=0 | bbox=50.1,395.2,286.4,404.3 -->
Table 4. Error rates (%) of single-model results on the ImageNet

<!-- p6-b005 | type=body | col=0 | bbox=50.1,402.5,221.3,415.2 -->
validation set (except † reported on the test set).

<!-- p6-b006 | type=table | col=0 | bbox=60.0,426.2,276.5,512.1 -->
[table T5]
method | top-5 err. (test)
VGG [41] (ILSVRC’14)
GoogLeNet [44] (ILSVRC’14) | 7.32
6.66
VGG [41] (v5)
PReLU-net [13]
BN-inception [16] | 6.8
4.94
4.82
ResNet (ILSVRC’15) | 3.57

<!-- p6-b007 | type=body | col=0 | bbox=50.1,501.5,286.4,527.1 -->
3.57 Table 5. Error rates (%) of ensembles. The top-5 error is on the

<!-- p6-b008 | type=body | col=0 | bbox=50.1,529.1,234.2,538.1 -->
test set of ImageNet and reported by the test server.

<!-- p6-b009 | type=body | col=0 | bbox=50.1,563.1,286.4,608.9 -->
ResNet reduces the top-1 error by 3.5% (Table 2), resulting from the successfully reduced training error (Fig. 4 right vs. left). This comparison veriﬁes the effectiveness of residual learning on extremely deep systems.

<!-- p6-b010 | type=body | col=0 | bbox=50.1,612.3,286.4,694.0 -->
Last, we also note that the 18-layer plain/residual nets are comparably accurate (Table 2), but the 18-layer ResNet converges faster (Fig. 4 right vs. left). When the net is “not overly deep” (18 layers here), the current SGD solver is still able to ﬁnd good solutions to the plain net. In this case, the ResNet eases the optimization by providing faster convergence at the early stage.

<!-- p6-b011 | type=body | col=0 | bbox=50.1,703.4,286.4,713.4 -->
Identity vs. Projection Shortcuts. We have shown that

<!-- p6-b012 | type=figure | col=1 | bbox=308.9,72.0,545.1,188.0 -->
![Figure 5. A deeper residual function F for ImageNet. Left: a building block (on 56×56 feature maps) as in Fig. 3 for ResNet- 34. Right: a “bottleneck” building block for ResNet-50/101/152.](figures/F5.png)

<!-- p6-b025 | type=caption | col=1 | bbox=308.9,156.8,545.1,188.0 -->
Figure 5. A deeper residual function F for ImageNet. Left: a building block (on 56×56 feature maps) as in Fig. 3 for ResNet- 34. Right: a “bottleneck” building block for ResNet-50/101/152.

<!-- p6-b026 | type=body | col=1 | bbox=308.9,205.5,545.1,287.2 -->
parameter-free, identity shortcuts help with training. Next we investigate projection shortcuts (Eqn.(2)). In Table 3 we compare three options: (A) zero-padding shortcuts are used for increasing dimensions, and all shortcuts are parameterfree (the same as Table 2 and Fig. 4 right); (B) projection shortcuts are used for increasing dimensions, and other shortcuts are identity; and (C) all shortcuts are projections.

<!-- p6-b027 | type=body | col=1 | bbox=308.9,289.9,545.1,431.4 -->
Table 3 shows that all three options are considerably better than the plain counterpart. B is slightly better than A. We argue that this is because the zero-padded dimensions in A indeed have no residual learning. C is marginally better than B, and we attribute this to the extra parameters introduced by many (thirteen) projection shortcuts. But the small differences among A/B/C indicate that projection shortcuts are not essential for addressing the degradation problem. So we do not use option C in the rest of this paper, to reduce memory/time complexity and model sizes. Identity shortcuts are particularly important for not increasing the complexity of the bottleneck architectures that are introduced below.

<!-- p6-b028 | type=body | col=1 | bbox=308.9,440.0,545.1,450.0 -->
Deeper Bottleneck Architectures. Next we describe our

<!-- p6-b029 | type=body | col=1 | bbox=308.9,452.0,545.1,557.6 -->
deeper nets for ImageNet. Because of concerns on the training time that we can afford, we modify the building block as a bottleneck design4. For each residual function F, we use a stack of 3 layers instead of 2 (Fig. 5). The three layers are 1×1, 3×3, and 1×1 convolutions, where the 1×1 layers are responsible for reducing and then increasing (restoring) dimensions, leaving the 3×3 layer a bottleneck with smaller input/output dimensions. Fig. 5 shows an example, where both designs have similar time complexity.

<!-- p6-b030 | type=body | col=1 | bbox=308.9,560.3,545.1,642.0 -->
The parameter-free identity shortcuts are particularly important for the bottleneck architectures. If the identity shortcut in Fig. 5 (right) is replaced with projection, one can show that the time complexity and model size are doubled, as the shortcut is connected to the two high-dimensional ends. So identity shortcuts lead to more efﬁcient models for the bottleneck designs.

<!-- p6-b031 | type=body | col=1 | bbox=320.8,644.6,545.1,654.7 -->
50-layer ResNet: We replace each 2-layer block in the

<!-- p6-b032 | type=footnote | col=1 | bbox=308.9,665.8,545.1,712.9 -->
4Deeper non-bottleneck ResNets (e.g., Fig. 5 left) also gain accuracy from increased depth (as shown on CIFAR-10), but are not as economical as the bottleneck ResNets. So the usage of bottleneck designs is mainly due to practical considerations. We further note that the degradation problem of plain nets is also witnessed for the bottleneck designs.


<!-- ===== page 7 | columns=2 | gutters=[[288.0, 307.0]] -->
<!-- p7-b000 | type=body | col=0 | bbox=50.1,74.4,286.4,108.3 -->
34-layer net with this 3-layer bottleneck block, resulting in a 50-layer ResNet (Table 1). We use option B for increasing dimensions. This model has 3.8 billion FLOPs.

<!-- p7-b001 | type=body | col=0 | bbox=62.1,110.6,286.4,120.7 -->
101-layer and 152-layer ResNets: We construct 101-

<!-- p7-b002 | type=body | col=0 | bbox=50.1,122.7,286.4,180.5 -->
layer and 152-layer ResNets by using more 3-layer blocks (Table 1). Remarkably, although the depth is signiﬁcantly increased, the 152-layer ResNet (11.3 billion FLOPs) still has lower complexity than VGG-16/19 nets (15.3/19.6 billion FLOPs).

<!-- p7-b003 | type=body | col=0 | bbox=50.1,182.9,286.4,252.7 -->
The 50/101/152-layer ResNets are more accurate than the 34-layer ones by considerable margins (Table 3 and 4). We do not observe the degradation problem and thus enjoy signiﬁcant accuracy gains from considerably increased depth. The beneﬁts of depth are witnessed for all evaluation metrics (Table 3 and 4).

<!-- p7-b004 | type=body | col=0 | bbox=50.1,261.0,286.4,271.1 -->
Comparisons with State-of-the-art Methods. In Table 4

<!-- p7-b005 | type=body | col=0 | bbox=50.1,273.0,286.4,354.7 -->
we compare with the previous best single-model results. Our baseline 34-layer ResNets have achieved very competitive accuracy. Our 152-layer ResNet has a single-model top-5 validation error of 4.49%. This single-model result outperforms all previous ensemble results (Table 5). We combine six models of different depth to form an ensemble (only with two 152-layer ones at the time of submitting).

<!-- p7-b006 | type=body | col=0 | bbox=50.1,356.6,286.4,366.7 -->
This leads to 3.57% top-5 error on the test set (Table 5).

<!-- p7-b007 | type=body | col=0 | bbox=50.1,368.5,232.5,378.5 -->
This entry won the 1st place in ILSVRC 2015.

<!-- p7-b008 | type=heading | col=0 | bbox=50.1,389.1,180.3,400.1 -->
### 4.2. CIFAR-10 and Analysis

<!-- p7-b009 | type=body | col=0 | bbox=50.1,408.4,286.4,490.1 -->
We conducted more studies on the CIFAR-10 dataset [20], which consists of 50k training images and 10k testing images in 10 classes. We present experiments trained on the training set and evaluated on the test set. Our focus is on the behaviors of extremely deep networks, but not on pushing the state-of-the-art results, so we intentionally use simple architectures as follows.

<!-- p7-b010 | type=body | col=0 | bbox=50.1,492.5,286.4,622.0 -->
The plain/residual architectures follow the form in Fig. 3 (middle/right). The network inputs are 32×32 images, with the per-pixel mean subtracted. The ﬁrst layer is 3×3 convolutions. Then we use a stack of 6n layers with 3×3 convolutions on the feature maps of sizes {32, 16, 8} respectively, with 2n layers for each feature map size. The numbers of ﬁlters are {16, 32, 64} respectively. The subsampling is performed by convolutions with a stride of 2. The network ends with a global average pooling, a 10-way fully-connected layer, and softmax. There are totally 6n+2 stacked weighted layers. The following table summarizes the architecture:

<!-- p7-b011 | type=table | col=0 | bbox=74.2,632.8,262.3,669.8 -->
[table T7]
output map size | 32×32 | 16×16 | 8×8
\# layers
\# ﬁlters | 1+2n
16 | 2n
32 | 2n
64

<!-- p7-b012 | type=body | col=0 | bbox=50.1,659.1,286.4,713.4 -->
64 When shortcut connections are used, they are connected to the pairs of 3×3 layers (totally 3n shortcuts). On this dataset we use identity shortcuts in all cases (i.e., option A),

<!-- p7-b013 | type=table | col=1 | bbox=311.2,73.2,542.8,242.6 -->
[table T6]
method |  |  | error (%)
Maxout [10]
NIN [25]
DSN [24] |  |  | 9.38
8.81
8.22
 | # layers | # params | 
FitNet [35]
Highway [42, 43]
Highway [42, 43] | 19
19
32 | 2.5M
2.3M
1.25M | 8.39
7.54 (7.72±0.16)
8.80
ResNet
ResNet
ResNet
ResNet
ResNet
ResNet | 20
32
44
56
110
1202 | 0.27M
0.46M
0.66M
0.85M
1.7M
19.4M | 8.75
7.51
7.17
6.97
6.43 (6.61±0.16)
7.93

<!-- p7-b014 | type=caption | col=1 | bbox=308.9,253.1,545.1,262.1 -->
Table 6. Classiﬁcation error on the CIFAR-10 test set. All meth-

<!-- p7-b015 | type=body | col=1 | bbox=308.9,264.1,545.1,284.1 -->
ods are with data augmentation. For ResNet-110, we run it 5 times and show “best (mean±std)” as in [43].

<!-- p7-b016 | type=body | col=1 | bbox=308.9,305.5,545.1,327.4 -->
so our residual models have exactly the same depth, width, and number of parameters as the plain counterparts.

<!-- p7-b017 | type=body | col=1 | bbox=308.9,329.4,545.1,466.1 -->
We use a weight decay of 0.0001 and momentum of 0.9, and adopt the weight initialization in [13] and BN [16] but with no dropout. These models are trained with a minibatch size of 128 on two GPUs. We start with a learning rate of 0.1, divide it by 10 at 32k and 48k iterations, and terminate training at 64k iterations, which is determined on a 45k/5k train/val split. We follow the simple data augmentation in [24] for training: 4 pixels are padded on each side, and a 32×32 crop is randomly sampled from the padded image or its horizontal ﬂip. For testing, we only evaluate the single view of the original 32×32 image.

<!-- p7-b018 | type=body | col=1 | bbox=308.9,460.7,545.1,542.6 -->
We compare n = {3, 5, 7, 9}, leading to 20, 32, 44, and 56-layer networks. Fig. 6 (left) shows the behaviors of the plain nets. The deep plain nets suffer from increased depth, and exhibit higher training error when going deeper. This phenomenon is similar to that on ImageNet (Fig. 4, left) and on MNIST (see [42]), suggesting that such an optimization difﬁculty is a fundamental problem.

<!-- p7-b019 | type=caption | col=1 | bbox=308.9,544.6,545.1,590.4 -->
Fig. 6 (middle) shows the behaviors of ResNets. Also similar to the ImageNet cases (Fig. 4, right), our ResNets manage to overcome the optimization difﬁculty and demonstrate accuracy gains when the depth increases.

<!-- p7-b020 | type=body | col=1 | bbox=308.9,592.2,545.1,626.3 -->
We further explore n = 18 that leads to a 110-layer ResNet. In this case, we ﬁnd that the initial learning rate of 0.1 is slightly too large to start converging5. So we use

<!-- p7-b021 | type=body | col=1 | bbox=308.9,628.3,545.1,638.3 -->
0.01 to warm up the training until the training error is below

<!-- p7-b022 | type=body | col=1 | bbox=308.9,640.2,545.1,686.1 -->
80% (about 400 iterations), and then go back to 0.1 and continue training. The rest of the learning schedule is as done previously. This 110-layer network converges well (Fig. 6, middle). It has fewer parameters than other deep and thin

<!-- p7-b023 | type=footnote | col=1 | bbox=308.9,694.2,545.1,712.9 -->
5With an initial learning rate of 0.1, it starts converging (<90% error) after several epochs, but still reaches similar accuracy.


<!-- ===== page 8 | columns=2 | gutters=[[288.0, 307.0]] -->
<!-- p8-b000 | type=figure | col=-1 | bbox=50.1,72.0,545.1,192.5 -->
![Figure 6. Training on CIFAR-10. Dashed lines denote training error, and bold lines denote testing error. Left: plain networks. The error of plain-110 is higher than 60% and not displayed. Middle: ResNets. Right: ResNets with 110 and 1202 layers.](figures/F7.png)

<!-- p8-b011 | type=formula | col=0 | bbox=121.3,140.1,135.6,160.6 -->
$$ plain-20 plain-32 plain-44 plain-56 $$

<!-- p8-b046 | type=caption | col=-1 | bbox=50.1,172.5,545.1,192.5 -->
Figure 6. Training on CIFAR-10. Dashed lines denote training error, and bold lines denote testing error. Left: plain networks. The error of plain-110 is higher than 60% and not displayed. Middle: ResNets. Right: ResNets with 110 and 1202 layers.

<!-- p8-b047 | type=figure | col=0 | bbox=50.1,212.2,286.4,348.2 -->
![Figure 7. Standard deviations (std) of layer responses on CIFAR- 10. The responses are the outputs of each 3×3 layer, after BN and](figures/F6.png)

<!-- p8-b076 | type=caption | col=0 | bbox=50.1,328.3,286.4,348.2 -->
Figure 7. Standard deviations (std) of layer responses on CIFAR- 10. The responses are the outputs of each 3×3 layer, after BN and

<!-- p8-b077 | type=body | col=0 | bbox=50.1,350.1,286.4,370.2 -->
before nonlinearity. Top: the layers are shown in their original order. Bottom: the responses are ranked in descending order.

<!-- p8-b078 | type=body | col=0 | bbox=50.1,392.4,286.4,414.3 -->
networks such as FitNet [35] and Highway [42] (Table 6), yet is among the state-of-the-art results (6.43%, Table 6).

<!-- p8-b079 | type=body | col=0 | bbox=50.1,422.3,286.4,432.3 -->
Analysis of Layer Responses. Fig. 7 shows the standard

<!-- p8-b080 | type=body | col=0 | bbox=50.1,434.3,286.4,587.7 -->
deviations (std) of the layer responses. The responses are the outputs of each 3×3 layer, after BN and before other nonlinearity (ReLU/addition). For ResNets, this analysis reveals the response strength of the residual functions. Fig. 7 shows that ResNets have generally smaller responses than their plain counterparts. These results support our basic motivation (Sec.3.1) that the residual functions might be generally closer to zero than the non-residual functions. We also notice that the deeper ResNet has smaller magnitudes of responses, as evidenced by the comparisons among ResNet-20, 56, and 110 in Fig. 7. When there are more layers, an individual layer of ResNets tends to modify the signal less.

<!-- p8-b081 | type=body | col=0 | bbox=50.1,595.7,286.4,605.7 -->
Exploring Over 1000 layers. We explore an aggressively

<!-- p8-b082 | type=body | col=0 | bbox=50.1,607.5,286.4,677.5 -->
deep model of over 1000 layers. We set n = 200 that leads to a 1202-layer network, which is trained as described above. Our method shows no optimization difﬁculty, and this 103-layer network is able to achieve training error <0.1% (Fig. 6, right). Its test error is still fairly good (7.93%, Table 6).

<!-- p8-b083 | type=body | col=0 | bbox=50.1,679.5,286.4,713.4 -->
But there are still open problems on such aggressively deep models. The testing result of this 1202-layer network is worse than that of our 110-layer network, although both

<!-- p8-b084 | type=table | col=1 | bbox=397.9,213.1,518.3,258.6 -->
[table T8]
07+12 | 07++12
VOC 07 test | VOC 12 test
73.2
76.4 | 70.4
73.8

<!-- p8-b085 | type=body | col=1 | bbox=343.6,213.8,388.7,222.8 -->
training data

<!-- p8-b086 | type=body | col=1 | bbox=351.4,225.8,381.0,234.7 -->
test data

<!-- p8-b087 | type=body | col=1 | bbox=350.6,237.7,381.8,246.6 -->
VGG-16

<!-- p8-b088 | type=body | col=1 | bbox=308.9,249.2,545.1,274.1 -->
ResNet-101 Table 7. Object detection mAP (%) on the PASCAL VOC

<!-- p8-b089 | type=body | col=1 | bbox=308.9,276.0,545.1,285.0 -->
2007/2012 test sets using baseline Faster R-CNN. See also Ta-

<!-- p8-b090 | type=body | col=1 | bbox=308.9,287.0,420.7,296.0 -->
ble 10 and 11 for better results.

<!-- p8-b091 | type=table | col=1 | bbox=344.2,302.2,509.7,331.9 -->
[table T9]
metric | mAP@.5 | mAP@[.5, .95]
VGG-16 | 41.5 | 21.2
ResNet-101 | 48.4 | 27.2

<!-- p8-b092 | type=body | col=1 | bbox=308.9,325.0,545.1,349.9 -->
ResNet-101 Table 8. Object detection mAP (%) on the COCO validation set

<!-- p8-b093 | type=body | col=1 | bbox=308.9,351.8,541.6,360.9 -->
using baseline Faster R-CNN. See also Table 9 for better results.

<!-- p8-b094 | type=body | col=1 | bbox=308.9,378.2,545.1,495.7 -->
have similar training error. We argue that this is because of overﬁtting. The 1202-layer network may be unnecessarily large (19.4M) for this small dataset. Strong regularization such as maxout [10] or dropout [14] is applied to obtain the best results ([10, 25, 24, 35]) on this dataset. In this paper, we use no maxout/dropout and just simply impose regularization via deep and thin architectures by design, without distracting from the focus on the difﬁculties of optimization. But combining with stronger regularization may improve results, which we will study in the future.

<!-- p8-b095 | type=heading | col=1 | bbox=308.9,505.1,542.1,516.1 -->
### 4.3. Object Detection on PASCAL and MS COCO

<!-- p8-b096 | type=body | col=1 | bbox=308.9,524.0,545.1,665.5 -->
Our method has good generalization performance on other recognition tasks. Table 7 and 8 show the object detection baseline results on PASCAL VOC 2007 and 2012 [5] and COCO [26]. We adopt Faster R-CNN [32] as the detection method. Here we are interested in the improvements of replacing VGG-16 [41] with ResNet-101. The detection implementation (see appendix) of using both models is the same, so the gains can only be attributed to better networks. Most remarkably, on the challenging COCO dataset we obtain a 6.0% increase in COCO’s standard metric (mAP@[.5, .95]), which is a 28% relative improvement. This gain is solely due to the learned representations.

<!-- p8-b097 | type=body | col=1 | bbox=308.9,667.6,545.1,713.4 -->
Based on deep residual nets, we won the 1st places in several tracks in ILSVRC & COCO 2015 competitions: ImageNet detection, ImageNet localization, COCO detection, and COCO segmentation. The details are in the appendix.


<!-- ===== page 9 | columns=2 | gutters=[[288.0, 307.0]] -->
<!-- p9-b000 | type=heading | col=0 | bbox=50.1,72.8,105.7,84.7 -->
## References

<!-- p9-b001 | type=reference | col=0 | bbox=54.1,92.4,286.4,100.3 -->
[1] Y. Bengio, P. Simard, and P. Frasconi. Learning long-term dependen-

<!-- p9-b002 | type=reference | col=0 | bbox=68.4,101.7,286.4,119.3 -->
cies with gradient descent is difﬁcult. IEEE Transactions on Neural Networks, 5(2):157–166, 1994.

<!-- p9-b003 | type=reference | col=0 | bbox=54.1,121.6,286.4,129.7 -->
[2] C. M. Bishop. Neural networks for pattern recognition. Oxford

<!-- p9-b004 | type=reference | col=0 | bbox=54.1,131.2,286.4,149.6 -->
university press, 1995. [3] W. L. Briggs, S. F. McCormick, et al. A Multigrid Tutorial. Siam,

<!-- p9-b005 | type=reference | col=0 | bbox=54.1,151.1,286.4,169.6 -->
2000. [4] K. Chatﬁeld, V. Lempitsky, A. Vedaldi, and A. Zisserman. The devil

<!-- p9-b006 | type=reference | col=0 | bbox=68.4,171.1,286.4,188.5 -->
is in the details: an evaluation of recent feature encoding methods. In BMVC, 2011.

<!-- p9-b007 | type=reference | col=0 | bbox=54.1,191.0,286.4,198.9 -->
[5] M. Everingham, L. Van Gool, C. K. Williams, J. Winn, and A. Zis-

<!-- p9-b008 | type=reference | col=0 | bbox=68.4,200.3,286.4,217.9 -->
serman. The Pascal Visual Object Classes (VOC) Challenge. IJCV, pages 303–338, 2010.

<!-- p9-b009 | type=reference | col=0 | bbox=54.1,220.4,286.4,228.3 -->
[6] S. Gidaris and N. Komodakis. Object detection via a multi-region &

<!-- p9-b010 | type=reference | col=0 | bbox=54.1,229.7,251.6,248.2 -->
semantic segmentation-aware cnn model. In ICCV, 2015. [7] R. Girshick. Fast R-CNN. In ICCV, 2015.

<!-- p9-b011 | type=reference | col=0 | bbox=54.1,250.7,286.4,258.7 -->
[8] R. Girshick, J. Donahue, T. Darrell, and J. Malik. Rich feature hier-

<!-- p9-b012 | type=reference | col=0 | bbox=68.4,260.2,286.4,277.6 -->
archies for accurate object detection and semantic segmentation. In CVPR, 2014.

<!-- p9-b013 | type=reference | col=0 | bbox=54.1,280.1,286.4,288.1 -->
[9] X. Glorot and Y. Bengio. Understanding the difﬁculty of training

<!-- p9-b014 | type=reference | col=0 | bbox=50.1,289.4,286.4,308.0 -->
deep feedforward neural networks. In AISTATS, 2010. [10] I. J. Goodfellow, D. Warde-Farley, M. Mirza, A. Courville, and

<!-- p9-b015 | type=reference | col=0 | bbox=50.1,309.4,286.4,327.9 -->
Y. Bengio. Maxout networks. arXiv:1302.4389, 2013. [11] K. He and J. Sun. Convolutional neural networks at constrained time

<!-- p9-b016 | type=reference | col=0 | bbox=50.1,329.3,286.4,347.9 -->
cost. In CVPR, 2015. [12] K. He, X. Zhang, S. Ren, and J. Sun. Spatial pyramid pooling in deep

<!-- p9-b017 | type=reference | col=0 | bbox=50.1,349.2,286.4,367.8 -->
convolutional networks for visual recognition. In ECCV, 2014. [13] K. He, X. Zhang, S. Ren, and J. Sun. Delving deep into rectiﬁers:

<!-- p9-b018 | type=reference | col=0 | bbox=68.4,369.3,286.4,386.7 -->
Surpassing human-level performance on imagenet classiﬁcation. In ICCV, 2015.

<!-- p9-b019 | type=reference | col=0 | bbox=50.1,389.2,286.4,397.2 -->
[14] G. E. Hinton, N. Srivastava, A. Krizhevsky, I. Sutskever, and

<!-- p9-b020 | type=reference | col=0 | bbox=68.4,398.7,286.4,416.1 -->
R. R. Salakhutdinov. Improving neural networks by preventing coadaptation of feature detectors. arXiv:1207.0580, 2012.

<!-- p9-b021 | type=reference | col=0 | bbox=50.1,418.4,286.4,426.6 -->
[15] S. Hochreiter and J. Schmidhuber. Long short-term memory. Neural

<!-- p9-b022 | type=reference | col=0 | bbox=50.1,427.9,286.4,446.5 -->
computation, 9(8):1735–1780, 1997. [16] S. Ioffe and C. Szegedy. Batch normalization: Accelerating deep

<!-- p9-b023 | type=reference | col=0 | bbox=50.1,447.8,286.4,466.4 -->
network training by reducing internal covariate shift. In ICML, 2015. [17] H. Jegou, M. Douze, and C. Schmid. Product quantization for nearest

<!-- p9-b024 | type=reference | col=0 | bbox=50.1,467.7,286.4,486.3 -->
neighbor search. TPAMI, 33, 2011. [18] H. Jegou, F. Perronnin, M. Douze, J. Sanchez, P. Perez, and

<!-- p9-b025 | type=reference | col=0 | bbox=68.4,487.8,286.4,505.2 -->
C. Schmid. Aggregating local image descriptors into compact codes. TPAMI, 2012.

<!-- p9-b026 | type=reference | col=0 | bbox=50.1,507.7,286.4,515.7 -->
[19] Y. Jia, E. Shelhamer, J. Donahue, S. Karayev, J. Long, R. Girshick,

<!-- p9-b027 | type=reference | col=0 | bbox=68.4,517.2,286.4,534.6 -->
S. Guadarrama, and T. Darrell. Caffe: Convolutional architecture for fast feature embedding. arXiv:1408.5093, 2014.

<!-- p9-b028 | type=reference | col=0 | bbox=50.1,537.1,286.4,545.1 -->
[20] A. Krizhevsky. Learning multiple layers of features from tiny im-

<!-- p9-b029 | type=reference | col=0 | bbox=50.1,546.4,286.4,565.0 -->
ages. Tech Report, 2009. [21] A. Krizhevsky, I. Sutskever, and G. Hinton. Imagenet classiﬁcation

<!-- p9-b030 | type=reference | col=0 | bbox=50.1,566.4,286.4,584.9 -->
with deep convolutional neural networks. In NIPS, 2012. [22] Y. LeCun, B. Boser, J. S. Denker, D. Henderson, R. E. Howard,

<!-- p9-b031 | type=reference | col=0 | bbox=68.4,586.4,286.4,603.9 -->
W. Hubbard, and L. D. Jackel. Backpropagation applied to handwritten zip code recognition. Neural computation, 1989.

<!-- p9-b032 | type=reference | col=0 | bbox=50.1,606.3,286.4,614.3 -->
[23] Y. LeCun, L. Bottou, G. B. Orr, and K.-R. M¨uller. Efﬁcient backprop.

<!-- p9-b033 | type=reference | col=0 | bbox=50.1,615.7,286.4,634.2 -->
In Neural Networks: Tricks of the Trade, pages 9–50. Springer, 1998. [24] C.-Y. Lee, S. Xie, P. Gallagher, Z. Zhang, and Z. Tu. Deeply-

<!-- p9-b034 | type=reference | col=0 | bbox=50.1,635.6,286.4,654.1 -->
supervised nets. arXiv:1409.5185, 2014. [25] M. Lin, Q. Chen, and S. Yan. Network in network. arXiv:1312.4400,

<!-- p9-b035 | type=reference | col=0 | bbox=50.1,655.6,286.4,674.1 -->
2013. [26] T.-Y. Lin, M. Maire, S. Belongie, J. Hays, P. Perona, D. Ramanan,

<!-- p9-b036 | type=reference | col=0 | bbox=68.4,675.5,286.4,693.0 -->
P. Doll´ar, and C. L. Zitnick. Microsoft COCO: Common objects in context. In ECCV. 2014.

<!-- p9-b037 | type=reference | col=0 | bbox=50.1,695.5,286.4,703.5 -->
[27] J. Long, E. Shelhamer, and T. Darrell. Fully convolutional networks

<!-- p9-b038 | type=reference | col=0 | bbox=68.4,704.8,207.7,712.9 -->
for semantic segmentation. In CVPR, 2015.

<!-- p9-b039 | type=reference | col=1 | bbox=308.9,75.9,545.1,83.9 -->
[28] G. Mont´ufar, R. Pascanu, K. Cho, and Y. Bengio. On the number of

<!-- p9-b040 | type=reference | col=1 | bbox=308.9,85.2,545.1,103.8 -->
linear regions of deep neural networks. In NIPS, 2014. [29] V. Nair and G. E. Hinton. Rectiﬁed linear units improve restricted

<!-- p9-b041 | type=reference | col=1 | bbox=308.9,105.2,545.1,123.7 -->
boltzmann machines. In ICML, 2010. [30] F. Perronnin and C. Dance. Fisher kernels on visual vocabularies for

<!-- p9-b042 | type=reference | col=1 | bbox=308.9,125.1,545.1,143.7 -->
image categorization. In CVPR, 2007. [31] T. Raiko, H. Valpola, and Y. LeCun. Deep learning made easier by

<!-- p9-b043 | type=reference | col=1 | bbox=308.9,145.0,545.1,163.6 -->
linear transformations in perceptrons. In AISTATS, 2012. [32] S. Ren, K. He, R. Girshick, and J. Sun. Faster R-CNN: Towards

<!-- p9-b044 | type=reference | col=1 | bbox=327.1,164.9,545.1,182.5 -->
real-time object detection with region proposal networks. In NIPS, 2015.

<!-- p9-b045 | type=reference | col=1 | bbox=308.9,185.0,545.1,193.0 -->
[33] S. Ren, K. He, R. Girshick, X. Zhang, and J. Sun. Object detection

<!-- p9-b046 | type=reference | col=1 | bbox=308.9,194.3,545.1,212.9 -->
networks on convolutional feature maps. arXiv:1504.06066, 2015. [34] B. D. Ripley. Pattern recognition and neural networks. Cambridge

<!-- p9-b047 | type=reference | col=1 | bbox=308.9,214.4,545.1,232.8 -->
university press, 1996. [35] A. Romero, N. Ballas, S. E. Kahou, A. Chassang, C. Gatta, and

<!-- p9-b048 | type=reference | col=1 | bbox=308.9,234.2,545.1,252.8 -->
Y. Bengio. Fitnets: Hints for thin deep nets. In ICLR, 2015. [36] O. Russakovsky, J. Deng, H. Su, J. Krause, S. Satheesh, S. Ma,

<!-- p9-b049 | type=reference | col=1 | bbox=327.1,254.2,545.1,271.7 -->
Z. Huang, A. Karpathy, A. Khosla, M. Bernstein, et al. Imagenet large scale visual recognition challenge. arXiv:1409.0575, 2014.

<!-- p9-b050 | type=reference | col=1 | bbox=308.9,274.2,545.1,282.1 -->
[37] A. M. Saxe, J. L. McClelland, and S. Ganguli. Exact solutions to

<!-- p9-b051 | type=reference | col=1 | bbox=327.1,283.6,545.1,301.1 -->
the nonlinear dynamics of learning in deep linear neural networks. arXiv:1312.6120, 2013.

<!-- p9-b052 | type=reference | col=1 | bbox=308.9,303.6,545.1,311.5 -->
[38] N. N. Schraudolph. Accelerated gradient descent by factor-centering

<!-- p9-b053 | type=reference | col=1 | bbox=308.9,313.0,545.1,331.5 -->
decomposition. Technical report, 1998. [39] N. N. Schraudolph. Centering neural network gradient factors. In

<!-- p9-b054 | type=reference | col=1 | bbox=327.1,332.8,545.1,350.4 -->
Neural Networks: Tricks of the Trade, pages 207–226. Springer, 1998.

<!-- p9-b055 | type=reference | col=1 | bbox=308.9,352.9,545.1,360.9 -->
[40] P. Sermanet, D. Eigen, X. Zhang, M. Mathieu, R. Fergus, and Y. Le-

<!-- p9-b056 | type=reference | col=1 | bbox=327.1,362.3,545.1,379.8 -->
Cun. Overfeat: Integrated recognition, localization and detection using convolutional networks. In ICLR, 2014.

<!-- p9-b057 | type=reference | col=1 | bbox=308.9,382.3,545.1,390.2 -->
[41] K. Simonyan and A. Zisserman. Very deep convolutional networks

<!-- p9-b058 | type=reference | col=1 | bbox=308.9,391.6,545.1,410.2 -->
for large-scale image recognition. In ICLR, 2015. [42] R. K. Srivastava, K. Greff, and J. Schmidhuber. Highway networks.

<!-- p9-b059 | type=reference | col=1 | bbox=308.9,411.5,545.1,430.1 -->
arXiv:1505.00387, 2015. [43] R. K. Srivastava, K. Greff, and J. Schmidhuber. Training very deep

<!-- p9-b060 | type=reference | col=1 | bbox=308.9,431.4,545.1,450.0 -->
networks. 1507.06228, 2015. [44] C. Szegedy, W. Liu, Y. Jia, P. Sermanet, S. Reed, D. Anguelov, D. Er-

<!-- p9-b061 | type=reference | col=1 | bbox=327.1,451.5,545.1,468.9 -->
han, V. Vanhoucke, and A. Rabinovich. Going deeper with convolutions. In CVPR, 2015.

<!-- p9-b062 | type=reference | col=1 | bbox=308.9,471.4,545.1,479.4 -->
[45] R. Szeliski. Fast surface interpolation using hierarchical basis func-

<!-- p9-b063 | type=reference | col=1 | bbox=308.9,480.8,545.1,499.3 -->
tions. TPAMI, 1990. [46] R. Szeliski. Locally adapted hierarchical basis preconditioning. In

<!-- p9-b064 | type=reference | col=1 | bbox=308.9,500.7,545.1,519.3 -->
SIGGRAPH, 2006. [47] T. Vatanen, T. Raiko, H. Valpola, and Y. LeCun. Pushing stochas-

<!-- p9-b065 | type=reference | col=1 | bbox=327.1,520.8,545.1,547.6 -->
tic gradient towards second-order methods–backpropagation learning with transformations in nonlinearities. In Neural Information Processing, 2013.

<!-- p9-b066 | type=reference | col=1 | bbox=308.9,550.1,545.1,558.1 -->
[48] A. Vedaldi and B. Fulkerson. VLFeat: An open and portable library

<!-- p9-b067 | type=reference | col=1 | bbox=308.9,559.6,545.1,578.0 -->
of computer vision algorithms, 2008. [49] W. Venables and B. Ripley. Modern applied statistics with s-plus.

<!-- p9-b068 | type=reference | col=1 | bbox=308.9,579.5,545.1,598.0 -->
1999. [50] M. D. Zeiler and R. Fergus. Visualizing and understanding convolu-

<!-- p9-b069 | type=reference | col=1 | bbox=327.1,599.3,454.1,607.4 -->
tional neural networks. In ECCV, 2014.


<!-- ===== page 10 | columns=2 | gutters=[[288.0, 307.0]] -->
<!-- p10-b000 | type=heading | col=0 | bbox=50.1,72.8,200.9,84.7 -->
## A. Object Detection Baselines

<!-- p10-b001 | type=body | col=0 | bbox=50.1,93.7,286.4,163.4 -->
In this section we introduce our detection method based on the baseline Faster R-CNN [32] system. The models are initialized by the ImageNet classiﬁcation models, and then ﬁne-tuned on the object detection data. We have experimented with ResNet-50/101 at the time of the ILSVRC & COCO 2015 detection competitions.

<!-- p10-b002 | type=body | col=0 | bbox=50.1,165.8,286.4,367.0 -->
Unlike VGG-16 used in [32], our ResNet has no hidden fc layers. We adopt the idea of “Networks on Conv feature maps” (NoC) [33] to address this issue. We compute the full-image shared conv feature maps using those layers whose strides on the image are no greater than 16 pixels (i.e., conv1, conv2 x, conv3 x, and conv4 x, totally 91 conv layers in ResNet-101; Table 1). We consider these layers as analogous to the 13 conv layers in VGG-16, and by doing so, both ResNet and VGG-16 have conv feature maps of the same total stride (16 pixels). These layers are shared by a region proposal network (RPN, generating 300 proposals) [32] and a Fast R-CNN detection network [7]. RoI pooling [7] is performed before conv5 1. On this RoI-pooled feature, all layers of conv5 x and up are adopted for each region, playing the roles of VGG-16’s fc layers. The ﬁnal classiﬁcation layer is replaced by two sibling layers (classiﬁcation and box regression [7]).

<!-- p10-b003 | type=body | col=0 | bbox=50.1,369.3,286.4,463.0 -->
For the usage of BN layers, after pre-training, we compute the BN statistics (means and variances) for each layer on the ImageNet training set. Then the BN layers are ﬁxed during ﬁne-tuning for object detection. As such, the BN layers become linear activations with constant offsets and scales, and BN statistics are not updated by ﬁne-tuning. We ﬁx the BN layers mainly for reducing memory consumption in Faster R-CNN training.

<!-- p10-b004 | type=body | col=0 | bbox=50.1,470.2,113.4,480.2 -->
PASCAL VOC

<!-- p10-b005 | type=body | col=0 | bbox=50.1,482.4,286.4,600.1 -->
Following [7, 32], for the PASCAL VOC 2007 test set, we use the 5k trainval images in VOC 2007 and 16k trainval images in VOC 2012 for training (“07+12”). For the PASCAL VOC 2012 test set, we use the 10k trainval+test images in VOC 2007 and 16k trainval images in VOC 2012 for training (“07++12”). The hyper-parameters for training Faster R-CNN are the same as in [32]. Table 7 shows the results. ResNet-101 improves the mAP by >3% over VGG-16. This gain is solely because of the improved features learned by ResNet.

<!-- p10-b006 | type=body | col=0 | bbox=50.1,607.4,97.4,617.3 -->
MS COCO

<!-- p10-b007 | type=body | col=0 | bbox=50.1,619.8,286.4,713.4 -->
The MS COCO dataset [26] involves 80 object categories. We evaluate the PASCAL VOC metric (mAP @ IoU = 0.5) and the standard COCO metric (mAP @ IoU = .5:.05:.95). We use the 80k images on the train set for training and the 40k images on the val set for evaluation. Our detection system for COCO is similar to that for PASCAL VOC. We train the COCO models with an 8-GPU implementation, and thus the RPN step has a mini-batch size of

<!-- p10-b008 | type=body | col=1 | bbox=308.9,74.2,545.1,84.4 -->
8 images (i.e., 1 per GPU) and the Fast R-CNN step has a

<!-- p10-b009 | type=body | col=1 | bbox=308.9,86.4,545.1,120.2 -->
mini-batch size of 16 images. The RPN step and Fast R- CNN step are both trained for 240k iterations with a learning rate of 0.001 and then for 80k iterations with 0.0001.

<!-- p10-b010 | type=caption | col=1 | bbox=308.9,123.3,545.1,216.9 -->
Table 8 shows the results on the MS COCO validation set. ResNet-101 has a 6% increase of mAP@[.5, .95] over VGG-16, which is a 28% relative improvement, solely contributed by the features learned by the better network. Remarkably, the mAP@[.5, .95]’s absolute increase (6.0%) is nearly as big as mAP@.5’s (6.9%). This suggests that a deeper network can improve both recognition and localization.

<!-- p10-b011 | type=heading | col=1 | bbox=308.9,232.4,485.7,244.3 -->
## B. Object Detection Improvements

<!-- p10-b012 | type=body | col=1 | bbox=308.9,253.9,545.1,287.8 -->
For completeness, we report the improvements made for the competitions. These improvements are based on deep features and thus should beneﬁt from residual learning.

<!-- p10-b013 | type=body | col=1 | bbox=308.9,295.8,356.2,305.7 -->
MS COCO

<!-- p10-b014 | type=body | col=1 | bbox=308.9,308.7,545.1,426.4 -->
Box reﬁnement. Our box reﬁnement partially follows the iterative localization in [6]. In Faster R-CNN, the ﬁnal output is a regressed box that is different from its proposal box. So for inference, we pool a new feature from the regressed box and obtain a new classiﬁcation score and a new regressed box. We combine these 300 new predictions with the original 300 predictions. Non-maximum suppression (NMS) is applied on the union set of predicted boxes using an IoU threshold of 0.3 [8], followed by box voting [6]. Box reﬁnement improves mAP by about 2 points (Table 9).

<!-- p10-b015 | type=body | col=1 | bbox=308.9,434.2,545.1,563.9 -->
Global context. We combine global context in the Fast R-CNN step. Given the full-image conv feature map, we pool a feature by global Spatial Pyramid Pooling [12] (with a “single-level” pyramid) which can be implemented as “RoI” pooling using the entire image’s bounding box as the RoI. This pooled feature is fed into the post-RoI layers to obtain a global context feature. This global feature is concatenated with the original per-region feature, followed by the sibling classiﬁcation and box regression layers. This new structure is trained end-to-end. Global context improves mAP@.5 by about 1 point (Table 9).

<!-- p10-b016 | type=body | col=1 | bbox=308.9,571.8,545.1,720.6 -->
Multi-scale testing. In the above, all results are obtained by single-scale training/testing as in [32], where the image’s shorter side is s = 600 pixels. Multi-scale training/testing has been developed in [12, 7] by selecting a scale from a feature pyramid, and in [33] by using maxout layers. In our current implementation, we have performed multi-scale testing following [33]; we have not performed multi-scale training because of limited time. In addition, we have performed multi-scale testing only for the Fast R-CNN step (but not yet for the RPN step). With a trained model, we compute conv feature maps on an image pyramid, where the image’s shorter sides are s ∈{200, 400, 600, 800, 1000}.


<!-- ===== page 11 | columns=2 | gutters=[[288.0, 294.0]] -->
<!-- p11-b000 | type=table | col=-1 | bbox=140.0,72.2,456.9,177.8 -->
[table T10]
training data | COCO train |  | COCO trainval | 
test data | COCO val |  | COCO test-dev | 
mAP | @.5 | @[.5, .95] | @.5 | @[.5, .95]
baseline Faster R-CNN (VGG-16)
baseline Faster R-CNN (ResNet-101)
+box reﬁnement
+context
+multi-scale testing | 41.5
48.4
49.9
51.1
53.8 | 21.2
27.2
29.9
30.0
32.5 | 53.3
55.7 | 32.2
34.9
ensemble |  |  | 59.0 | 37.4

<!-- p11-b001 | type=caption | col=-1 | bbox=130.1,183.2,465.2,192.2 -->
Table 9. Object detection improvements on MS COCO using Faster R-CNN and ResNet-101.

<!-- p11-b002 | type=footnote | col=0 | bbox=105.8,210.0,114.6,217.2 -->
net

<!-- p11-b003 | type=footnote | col=0 | bbox=149.6,210.0,161.6,217.2 -->
data

<!-- p11-b004 | type=footnote | col=0 | bbox=184.6,210.0,199.4,217.2 -->
mAP

<!-- p11-b005 | type=footnote | col=-1 | bbox=206.6,211.4,537.8,216.8 -->
areo bike bird boat bottle bus car cat chair cow table dog horse mbike person plant sheep sofa train tv

<!-- p11-b006 | type=footnote | col=0 | bbox=53.3,211.4,68.3,216.8 -->
system

<!-- p11-b007 | type=footnote | col=-1 | bbox=185.7,220.6,542.0,227.8 -->
73.2 76.5 79.0 70.9 65.5 52.1 83.1 84.7 86.4 52.0 81.9 65.7 84.8 84.6 77.5 76.7 38.8 73.6 73.9 83.0 72.6

<!-- p11-b008 | type=footnote | col=0 | bbox=53.3,220.6,76.9,227.8 -->
baseline

<!-- p11-b009 | type=footnote | col=0 | bbox=97.6,220.6,122.7,227.8 -->
VGG-16

<!-- p11-b010 | type=footnote | col=0 | bbox=146.3,220.6,164.8,227.8 -->
07+12

<!-- p11-b011 | type=footnote | col=-1 | bbox=185.7,230.8,542.0,248.4 -->
79.8 80.7 76.2 68.3 55.9 85.1 85.3 89.8 56.7 87.8 69.4 88.3 88.9 80.9 78.4 41.7 78.6 79.8 85.3 72.0 85.6 90.0 89.6 87.8 80.8 76.1 89.9 89.9 89.6 75.5 90.0 80.7 89.6 90.3 89.1 88.7 65.4 88.1 85.6 89.0 86.8

<!-- p11-b012 | type=footnote | col=0 | bbox=53.3,230.9,76.9,238.1 -->
baseline

<!-- p11-b013 | type=footnote | col=0 | bbox=93.0,230.9,127.4,238.1 -->
ResNet-101

<!-- p11-b014 | type=footnote | col=0 | bbox=146.3,230.9,164.8,238.1 -->
07+12

<!-- p11-b015 | type=footnote | col=0 | bbox=185.7,230.9,198.3,238.1 -->
76.4

<!-- p11-b016 | type=formula | col=0 | bbox=53.3,241.2,176.9,248.4 -->
$$ baseline+++ ResNet-101 COCO+07+12 $$

<!-- p11-b017 | type=caption | col=-1 | bbox=50.1,255.4,545.1,275.3 -->
Table 10. Detection results on the PASCAL VOC 2007 test set. The baseline is the Faster R-CNN system. The system “baseline+++” include box reﬁnement, context, and multi-scale testing in Table 9.

<!-- p11-b018 | type=table | col=-1 | bbox=51.9,293.8,543.3,335.6 -->
[table T11]
system | net | data | mAP | areo bike bird boat bottle bus car cat chair cow table dog horse mbike person plant sheep sofa train tv
baseline
baseline
baseline+++ | VGG-16
ResNet-101
ResNet-101 | 07++12
07++12
COCO+07++12 | 70.4
73.8
83.8 | 84.9 79.8 74.3 53.9 49.8 77.5 75.9 88.5 45.6 77.1 55.3 86.9 81.7 80.9 79.6 40.1 72.6 60.9 81.2 61.5
86.5 81.6 77.2 58.0 51.0 78.6 76.6 93.2 48.6 80.4 59.0 92.1 85.3 84.8 80.7 48.1 77.3 66.5 84.7 65.6
92.1 88.4 84.8 75.9 71.4 86.3 87.8 94.2 66.8 89.4 69.2 93.9 91.9 90.9 89.6 67.9 88.2 76.8 90.3 80.0

<!-- p11-b019 | type=caption | col=-1 | bbox=50.1,340.6,545.1,361.0 -->
Table 11. Detection results on the PASCAL VOC 2012 test set (http://host.robots.ox.ac.uk:8080/leaderboard/ displaylb.php?challengeid=11&compid=4). The baseline is the Faster R-CNN system. The system “baseline+++” include

<!-- p11-b020 | type=body | col=0 | bbox=50.1,362.9,260.7,371.9 -->
box reﬁnement, context, and multi-scale testing in Table 9.

<!-- p11-b021 | type=body | col=0 | bbox=50.1,394.0,286.4,451.8 -->
We select two adjacent scales from the pyramid following [33]. RoI pooling and subsequent layers are performed on the feature maps of these two scales [33], which are merged by maxout as in [33]. Multi-scale testing improves the mAP by over 2 points (Table 9).

<!-- p11-b022 | type=body | col=0 | bbox=50.1,459.2,286.4,529.2 -->
Using validation data. Next we use the 80k+40k trainval set for training and the 20k test-dev set for evaluation. The testdev set has no publicly available ground truth and the result is reported by the evaluation server. Under this setting, the results are an mAP@.5 of 55.7% and an mAP@[.5, .95] of 34.9% (Table 9). This is our single-model result.

<!-- p11-b023 | type=body | col=0 | bbox=50.1,536.6,286.4,630.2 -->
Ensemble. In Faster R-CNN, the system is designed to learn region proposals and also object classiﬁers, so an ensemble can be used to boost both tasks. We use an ensemble for proposing regions, and the union set of proposals are processed by an ensemble of per-region classiﬁers. Table 9 shows our result based on an ensemble of 3 networks. The mAP is 59.0% and 37.4% on the test-dev set. This result won the 1st place in the detection task in COCO 2015.

<!-- p11-b024 | type=body | col=0 | bbox=50.1,642.9,113.4,652.9 -->
PASCAL VOC

<!-- p11-b025 | type=body | col=0 | bbox=50.1,655.6,286.4,713.4 -->
We revisit the PASCAL VOC dataset based on the above model. With the single model on the COCO dataset (55.7% mAP@.5 in Table 9), we ﬁne-tune this model on the PAS- CAL VOC sets. The improvements of box reﬁnement, context, and multi-scale testing are also adopted. By doing so

<!-- p11-b026 | type=table | col=1 | bbox=324.2,391.8,529.1,445.6 -->
[table T12]
 | val2 | test
GoogLeNet [44] (ILSVRC’14) | - | 43.9
our single model (ILSVRC’15)
our ensemble (ILSVRC’15) | 60.5
63.6 | 58.8
62.1

<!-- p11-b027 | type=body | col=1 | bbox=308.9,434.7,545.1,482.0 -->
our ensemble (ILSVRC’15) Table 12. Our results (mAP, %) on the ImageNet detection dataset. Our detection system is Faster R-CNN [32] with the improvements in Table 9, using ResNet-101.

<!-- p11-b028 | type=body | col=1 | bbox=308.9,499.4,545.1,545.2 -->
we achieve 85.6% mAP on PASCAL VOC 2007 (Table 10) and 83.8% on PASCAL VOC 2012 (Table 11)6. The result on PASCAL VOC 2012 is 10 points higher than the previous state-of-the-art result [6].

<!-- p11-b029 | type=body | col=1 | bbox=308.9,557.2,393.2,567.1 -->
ImageNet Detection

<!-- p11-b030 | type=body | col=1 | bbox=308.9,569.4,545.1,686.9 -->
The ImageNet Detection (DET) task involves 200 object categories. The accuracy is evaluated by mAP@.5. Our object detection algorithm for ImageNet DET is the same as that for MS COCO in Table 9. The networks are pretrained on the 1000-class ImageNet classiﬁcation set, and are ﬁne-tuned on the DET data. We split the validation set into two parts (val1/val2) following [8]. We ﬁne-tune the detection models using the DET training set and the val1 set. The val2 set is used for validation. We do not use other ILSVRC 2015 data. Our single model with ResNet-101 has

<!-- p11-b031 | type=footnote | col=1 | bbox=308.9,695.7,534.6,712.6 -->
6http://host.robots.ox.ac.uk:8080/anonymous/3OJ4OJ.html, submitted on 2015-11-26.


<!-- ===== page 12 | columns=2 | gutters=[[288.0, 307.0]] -->
<!-- p12-b000 | type=table | col=0 | bbox=51.9,72.7,284.6,147.5 -->
[table T13]
LOC
method | LOC
network | testing | LOC error
on GT CLS | classiﬁcation
network | top-5 LOC error
on predicted CLS
VGG’s [41]
RPN
RPN | VGG-16
ResNet-101
ResNet-101 | 1-crop
1-crop
dense | 33.1 [41]
13.3
11.7 |  | 
RPN
RPN+RCNN
RPN+RCNN | ResNet-101
ResNet-101
ensemble | dense
dense
dense |  | ResNet-101
ResNet-101
ensemble | 14.4
10.6
8.9

<!-- p12-b001 | type=caption | col=0 | bbox=50.1,152.9,286.4,205.7 -->
Table 13. Localization error (%) on the ImageNet validation. In the column of “LOC error on GT class” ([41]), the ground truth class is used. In the “testing” column, “1-crop” denotes testing on a center crop of 224×224 pixels, “dense” denotes dense (fully convolutional) and multi-scale testing.

<!-- p12-b002 | type=body | col=0 | bbox=50.1,224.5,286.4,258.4 -->
58.8% mAP and our ensemble of 3 models has 62.1% mAP on the DET test set (Table 12). This result won the 1st place in the ImageNet detection task in ILSVRC 2015, surpassing

<!-- p12-b003 | type=body | col=0 | bbox=50.1,260.3,216.7,270.3 -->
the second place by 8.5 points (absolute).

<!-- p12-b004 | type=heading | col=0 | bbox=50.1,285.1,180.6,297.1 -->
## C. ImageNet Localization

<!-- p12-b005 | type=body | col=0 | bbox=50.1,306.5,286.4,436.0 -->
The ImageNet Localization (LOC) task [36] requires to classify and localize the objects. Following [40, 41], we assume that the image-level classiﬁers are ﬁrst adopted for predicting the class labels of an image, and the localization algorithm only accounts for predicting bounding boxes based on the predicted classes. We adopt the “per-class regression” (PCR) strategy [40, 41], learning a bounding box regressor for each class. We pre-train the networks for ImageNet classiﬁcation and then ﬁne-tune them for localization. We train networks on the provided 1000-class ImageNet training set.

<!-- p12-b006 | type=body | col=0 | bbox=50.1,438.8,286.4,592.2 -->
Our localization algorithm is based on the RPN framework of [32] with a few modiﬁcations. Unlike the way in [32] that is category-agnostic, our RPN for localization is designed in a per-class form. This RPN ends with two sibling 1×1 convolutional layers for binary classiﬁcation (cls) and box regression (reg), as in [32]. The cls and reg layers are both in a per-class from, in contrast to [32]. Speciﬁcally, the cls layer has a 1000-d output, and each dimension is binary logistic regression for predicting being or not being an object class; the reg layer has a 1000×4-d output consisting of box regressors for 1000 classes. As in [32], our bounding box regression is with reference to multiple translation-invariant “anchor” boxes at each position.

<!-- p12-b007 | type=body | col=0 | bbox=50.1,595.0,286.4,676.7 -->
As in our ImageNet classiﬁcation training (Sec. 3.4), we randomly sample 224×224 crops for data augmentation. We use a mini-batch size of 256 images for ﬁne-tuning. To avoid negative samples being dominate, 8 anchors are randomly sampled for each image, where the sampled positive and negative anchors have a ratio of 1:1 [32]. For testing, the network is applied on the image fully-convolutionally.

<!-- p12-b008 | type=caption | col=0 | bbox=50.1,679.5,286.4,713.4 -->
Table 13 compares the localization results. Following [41], we ﬁrst perform “oracle” testing using the ground truth class as the classiﬁcation prediction. VGG’s paper [41] re-

<!-- p12-b009 | type=table | col=1 | bbox=313.5,72.7,540.5,142.4 -->
[table T14]
method | top-5 localization err | 
 | val | test
OverFeat [40] (ILSVRC’13)
GoogLeNet [44] (ILSVRC’14)
VGG [41] (ILSVRC’14) | 30.0
-
26.9 | 29.9
26.7
25.3
ours (ILSVRC’15) | 8.9 | 9.0

<!-- p12-b010 | type=body | col=1 | bbox=308.9,132.0,545.1,167.8 -->
ours (ILSVRC’15) Table 14. Comparisons of localization error (%) on the ImageNet dataset with state-of-the-art methods.

<!-- p12-b011 | type=body | col=1 | bbox=308.9,183.2,545.1,288.8 -->
ports a center-crop error of 33.1% (Table 13) using ground truth classes. Under the same setting, our RPN method using ResNet-101 net signiﬁcantly reduces the center-crop error to 13.3%. This comparison demonstrates the excellent performance of our framework. With dense (fully convolutional) and multi-scale testing, our ResNet-101 has an error of 11.7% using ground truth classes. Using ResNet-101 for predicting classes (4.6% top-5 classiﬁcation error, Table 4), the top-5 localization error is 14.4%.

<!-- p12-b012 | type=body | col=1 | bbox=308.9,290.6,545.1,420.3 -->
The above results are only based on the proposal network (RPN) in Faster R-CNN [32]. One may use the detection network (Fast R-CNN [7]) in Faster R-CNN to improve the results. But we notice that on this dataset, one image usually contains a single dominate object, and the proposal regions highly overlap with each other and thus have very similar RoI-pooled features. As a result, the image-centric training of Fast R-CNN [7] generates samples of small variations, which may not be desired for stochastic training. Motivated by this, in our current experiment we use the original R- CNN [8] that is RoI-centric, in place of Fast R-CNN.

<!-- p12-b013 | type=body | col=1 | bbox=308.9,422.3,545.1,599.6 -->
Our R-CNN implementation is as follows. We apply the per-class RPN trained as above on the training images to predict bounding boxes for the ground truth class. These predicted boxes play a role of class-dependent proposals. For each training image, the highest scored 200 proposals are extracted as training samples to train an R-CNN classiﬁer. The image region is cropped from a proposal, warped to 224×224 pixels, and fed into the classiﬁcation network as in R-CNN [8]. The outputs of this network consist of two sibling fc layers for cls and reg, also in a per-class form. This R-CNN network is ﬁne-tuned on the training set using a mini-batch size of 256 in the RoI-centric fashion. For testing, the RPN generates the highest scored 200 proposals for each predicted class, and the R-CNN network is used to update these proposals’ scores and box positions.

<!-- p12-b014 | type=body | col=1 | bbox=308.9,601.6,545.1,695.1 -->
This method reduces the top-5 localization error to 10.6% (Table 13). This is our single-model result on the validation set. Using an ensemble of networks for both classiﬁcation and localization, we achieve a top-5 localization error of 9.0% on the test set. This number signiﬁcantly outperforms the ILSVRC 14 results (Table 14), showing a 64% relative reduction of error. This result won the 1st place in the ImageNet localization task in ILSVRC 2015.
