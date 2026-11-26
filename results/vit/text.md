# vit.pdf

<!-- schema=pdf-struct/2 pages=22 column_template=1 sha256=f031259d8c15905506f3cf3d376b695b3110cb6f724792d5396776dcae610b16 -->


<!-- ===== page 1 | columns=1 | gutters=[] -->
<!-- p1-b000 | type=heading | col=0 | bbox=108.4,80.5,503.6,117.6 -->
## AN IMAGE IS WORTH 16X16 WORDS: TRANSFORMERS FOR IMAGE RECOGNITION AT SCALE

<!-- p1-b001 | type=author | col=0 | bbox=141.6,135.4,487.4,160.7 -->
Alexey Dosovitskiy∗,†, Lucas Beyer∗, Alexander Kolesnikov∗, Dirk Weissenborn∗, Xiaohua Zhai∗, Thomas Unterthiner, Mostafa Dehghani, Matthias Minderer,

<!-- p1-b002 | type=author | col=0 | bbox=178.1,162.4,445.3,173.8 -->
Georg Heigold, Sylvain Gelly, Jakob Uszkoreit, Neil Houlsby∗,†

<!-- p1-b003 | type=body | col=0 | bbox=220.7,176.1,403.3,187.7 -->
∗equal technical contribution, †equal advising

<!-- p1-b004 | type=affiliation | col=0 | bbox=199.4,190.7,424.6,213.5 -->
Google Research, Brain Team {adosovitskiy, neilhoulsby}@google.com

<!-- p1-b005 | type=heading | col=0 | bbox=278.3,243.6,333.7,255.6 -->
## ABSTRACT

<!-- p1-b006 | type=body | col=0 | bbox=143.9,270.5,468.1,390.1 -->
While the Transformer architecture has become the de-facto standard for natural language processing tasks, its applications to computer vision remain limited. In vision, attention is either applied in conjunction with convolutional networks, or used to replace certain components of convolutional networks while keeping their overall structure in place. We show that this reliance on CNNs is not necessary and a pure transformer applied directly to sequences of image patches can perform very well on image classiﬁcation tasks. When pre-trained on large amounts of data and transferred to multiple mid-sized or small image recognition benchmarks (ImageNet, CIFAR-100, VTAB, etc.), Vision Transformer (ViT) attains excellent results compared to state-of-the-art convolutional networks while requiring substantially fewer computational resources to train.1

<!-- p1-b007 | type=heading | col=0 | bbox=108.3,415.6,206.0,427.6 -->
## 1 INTRODUCTION

<!-- p1-b008 | type=body | col=0 | bbox=108.0,441.9,504.0,506.7 -->
Self-attention-based architectures, in particular Transformers (Vaswani et al., 2017), have become the model of choice in natural language processing (NLP). The dominant approach is to pre-train on a large text corpus and then ﬁne-tune on a smaller task-speciﬁc dataset (Devlin et al., 2019). Thanks to Transformers’ computational efﬁciency and scalability, it has become possible to train models of unprecedented size, with over 100B parameters (Brown et al., 2020; Lepikhin et al., 2020). With the models and datasets growing, there is still no sign of saturating performance.

<!-- p1-b009 | type=body | col=0 | bbox=108.0,513.6,504.0,600.3 -->
In computer vision, however, convolutional architectures remain dominant (LeCun et al., 1989; Krizhevsky et al., 2012; He et al., 2016). Inspired by NLP successes, multiple works try combining CNN-like architectures with self-attention (Wang et al., 2018; Carion et al., 2020), some replacing the convolutions entirely (Ramachandran et al., 2019; Wang et al., 2020a). The latter models, while theoretically efﬁcient, have not yet been scaled effectively on modern hardware accelerators due to the use of specialized attention patterns. Therefore, in large-scale image recognition, classic ResNetlike architectures are still state of the art (Mahajan et al., 2018; Xie et al., 2020; Kolesnikov et al., 2020).

<!-- p1-b010 | type=body | col=0 | bbox=108.0,607.3,504.0,661.1 -->
Inspired by the Transformer scaling successes in NLP, we experiment with applying a standard Transformer directly to images, with the fewest possible modiﬁcations. To do so, we split an image into patches and provide the sequence of linear embeddings of these patches as an input to a Transformer. Image patches are treated the same way as tokens (words) in an NLP application. We train the model on image classiﬁcation in supervised fashion.

<!-- p1-b011 | type=body | col=0 | bbox=108.0,668.1,504.0,700.0 -->
When trained on mid-sized datasets such as ImageNet without strong regularization, these models yield modest accuracies of a few percentage points below ResNets of comparable size. This seemingly discouraging outcome may be expected: Transformers lack some of the inductive biases

<!-- p1-b012 | type=body | col=0 | bbox=108.0,711.6,504.0,731.6 -->
1Fine-tuning code and pre-trained models are available at https://github.com/ google-research/vision_transformer


<!-- ===== page 2 | columns=1 | gutters=[] -->
<!-- p2-b000 | type=body | col=0 | bbox=108.0,84.3,504.0,105.2 -->
inherent to CNNs, such as translation equivariance and locality, and therefore do not generalize well when trained on insufﬁcient amounts of data.

<!-- p2-b001 | type=body | col=0 | bbox=108.0,112.2,504.0,187.9 -->
However, the picture changes if the models are trained on larger datasets (14M-300M images). We ﬁnd that large scale training trumps inductive bias. Our Vision Transformer (ViT) attains excellent results when pre-trained at sufﬁcient scale and transferred to tasks with fewer datapoints. When pre-trained on the public ImageNet-21k dataset or the in-house JFT-300M dataset, ViT approaches or beats state of the art on multiple image recognition benchmarks. In particular, the best model reaches the accuracy of 88.55% on ImageNet, 90.72% on ImageNet-ReaL, 94.55% on CIFAR-100, and 77.63% on the VTAB suite of 19 tasks.

<!-- p2-b002 | type=heading | col=0 | bbox=108.3,226.9,211.2,238.8 -->
## 2 RELATED WORK

<!-- p2-b003 | type=body | col=0 | bbox=108.0,265.0,504.0,318.8 -->
Transformers were proposed by Vaswani et al. (2017) for machine translation, and have since become the state of the art method in many NLP tasks. Large Transformer-based models are often pre-trained on large corpora and then ﬁne-tuned for the task at hand: BERT (Devlin et al., 2019) uses a denoising self-supervised pre-training task, while the GPT line of work uses language modeling as its pre-training task (Radford et al., 2018; 2019; Brown et al., 2020).

<!-- p2-b004 | type=body | col=0 | bbox=108.0,325.8,504.0,456.3 -->
Naive application of self-attention to images would require that each pixel attends to every other pixel. With quadratic cost in the number of pixels, this does not scale to realistic input sizes. Thus, to apply Transformers in the context of image processing, several approximations have been tried in the past. Parmar et al. (2018) applied the self-attention only in local neighborhoods for each query pixel instead of globally. Such local multi-head dot-product self attention blocks can completely replace convolutions (Hu et al., 2019; Ramachandran et al., 2019; Zhao et al., 2020). In a different line of work, Sparse Transformers (Child et al., 2019) employ scalable approximations to global selfattention in order to be applicable to images. An alternative way to scale attention is to apply it in blocks of varying sizes (Weissenborn et al., 2019), in the extreme case only along individual axes (Ho et al., 2019; Wang et al., 2020a). Many of these specialized attention architectures demonstrate promising results on computer vision tasks, but require complex engineering to be implemented efﬁciently on hardware accelerators.

<!-- p2-b005 | type=body | col=0 | bbox=108.0,462.9,504.0,528.0 -->
Most related to ours is the model of Cordonnier et al. (2020), which extracts patches of size 2 × 2 from the input image and applies full self-attention on top. This model is very similar to ViT, but our work goes further to demonstrate that large scale pre-training makes vanilla transformers competitive with (or even better than) state-of-the-art CNNs. Moreover, Cordonnier et al. (2020) use a small patch size of 2 × 2 pixels, which makes the model applicable only to small-resolution images, while we handle medium-resolution images as well.

<!-- p2-b006 | type=body | col=0 | bbox=108.0,535.0,504.0,599.8 -->
There has also been a lot of interest in combining convolutional neural networks (CNNs) with forms of self-attention, e.g. by augmenting feature maps for image classiﬁcation (Bello et al., 2019) or by further processing the output of a CNN using self-attention, e.g. for object detection (Hu et al., 2018; Carion et al., 2020), video processing (Wang et al., 2018; Sun et al., 2019), image classiﬁcation (Wu et al., 2020), unsupervised object discovery (Locatello et al., 2020), or uniﬁed text-vision tasks (Chen et al., 2020c; Lu et al., 2019; Li et al., 2019).

<!-- p2-b007 | type=body | col=0 | bbox=108.0,606.7,504.0,732.3 -->
Another recent related model is image GPT (iGPT) (Chen et al., 2020a), which applies Transformers to image pixels after reducing image resolution and color space. The model is trained in an unsupervised fashion as a generative model, and the resulting representation can then be ﬁne-tuned or probed linearly for classiﬁcation performance, achieving a maximal accuracy of 72% on ImageNet. Our work adds to the increasing collection of papers that explore image recognition at larger scales than the standard ImageNet dataset. The use of additional data sources allows to achieve state-ofthe-art results on standard benchmarks (Mahajan et al., 2018; Touvron et al., 2019; Xie et al., 2020). Moreover, Sun et al. (2017) study how CNN performance scales with dataset size, and Kolesnikov et al. (2020); Djolonga et al. (2020) perform an empirical exploration of CNN transfer learning from large scale datasets such as ImageNet-21k and JFT-300M. We focus on these two latter datasets as well, but train Transformers instead of ResNet-based models used in prior works.


<!-- ===== page 3 | columns=2 | gutters=[[323.0, 401.0]] -->
<!-- p3-b002 | type=figure | col=-1 | bbox=108.0,81.9,504.0,309.2 -->
![Figure 1: Model overview. We split an image into ﬁxed-size patches, linearly embed each of them, add position embeddings, and feed the resulting sequence of vectors to a standard Transformer encoder. In order to perform classiﬁcation, we use the standard approach of adding an extra learnable “classiﬁcation token” to the sequence. The illustration of the Transformer encoder was inspired by](figures/F1.png)

<!-- p3-b018 | type=caption | col=-1 | bbox=108.0,266.3,504.0,309.2 -->
Figure 1: Model overview. We split an image into ﬁxed-size patches, linearly embed each of them, add position embeddings, and feed the resulting sequence of vectors to a standard Transformer encoder. In order to perform classiﬁcation, we use the standard approach of adding an extra learnable “classiﬁcation token” to the sequence. The illustration of the Transformer encoder was inspired by

<!-- p3-b019 | type=body | col=0 | bbox=108.0,310.2,195.1,320.1 -->
Vaswani et al. (2017).

<!-- p3-b020 | type=heading | col=0 | bbox=108.3,358.8,172.8,370.8 -->
## 3 METHOD

<!-- p3-b021 | type=body | col=-1 | bbox=108.0,396.5,504.0,428.4 -->
In model design we follow the original Transformer (Vaswani et al., 2017) as closely as possible. An advantage of this intentionally simple setup is that scalable NLP Transformer architectures – and their efﬁcient implementations – can be used almost out of the box.

<!-- p3-b022 | type=heading | col=0 | bbox=108.2,464.3,258.6,474.2 -->
### 3.1 VISION TRANSFORMER (VIT)

<!-- p3-b023 | type=body | col=-1 | bbox=108.0,493.1,504.0,503.1 -->
An overview of the model is depicted in Figure 1. The standard Transformer receives as input a 1D

<!-- p3-b024 | type=body | col=-1 | bbox=108.0,500.5,504.0,528.2 -->
sequence of token embeddings. To handle 2D images, we reshape the image x ∈RH×W ×C into a sequence of ﬂattened 2D patches xp ∈RN×(P 2·C), where (H, W) is the resolution of the original

<!-- p3-b025 | type=body | col=-1 | bbox=108.0,527.5,504.0,571.9 -->
image, C is the number of channels, (P, P) is the resolution of each image patch, and N = HW/P 2 is the resulting number of patches, which also serves as the effective input sequence length for the Transformer. The Transformer uses constant latent vector size D through all of its layers, so we ﬂatten the patches and map to D dimensions with a trainable linear projection (Eq. 1). We refer to

<!-- p3-b026 | type=body | col=0 | bbox=108.0,572.9,321.4,582.8 -->
the output of this projection as the patch embeddings.

<!-- p3-b027 | type=body | col=-1 | bbox=108.0,589.3,504.0,599.8 -->
Similar to BERT’s [class] token, we prepend a learnable embedding to the sequence of embed-

<!-- p3-b028 | type=body | col=-1 | bbox=166.7,599.2,444.5,613.0 -->
0 = xclass), whose state at the output of the Transformer encoder (z0

<!-- p3-b029 | type=body | col=0 | bbox=108.0,599.2,170.6,632.6 -->
ded patches (z0 tached to z0

<!-- p3-b030 | type=body | col=1 | bbox=440.5,600.8,504.0,612.6 -->
L) serves as the

<!-- p3-b031 | type=body | col=-1 | bbox=108.0,611.5,504.0,621.7 -->
image representation y (Eq. 4). Both during pre-training and ﬁne-tuning, a classiﬁcation head is at-

<!-- p3-b032 | type=body | col=-1 | bbox=151.2,622.7,504.0,634.5 -->
L. The classiﬁcation head is implemented by a MLP with one hidden layer at pre-training

<!-- p3-b033 | type=body | col=0 | bbox=108.0,633.6,314.4,643.6 -->
time and by a single linear layer at ﬁne-tuning time.

<!-- p3-b034 | type=body | col=-1 | bbox=108.0,650.6,504.0,693.4 -->
Position embeddings are added to the patch embeddings to retain positional information. We use standard learnable 1D position embeddings, since we have not observed signiﬁcant performance gains from using more advanced 2D-aware position embeddings (Appendix D.4). The resulting sequence of embedding vectors serves as input to the encoder.

<!-- p3-b035 | type=body | col=-1 | bbox=108.0,700.4,504.0,732.3 -->
The Transformer encoder (Vaswani et al., 2017) consists of alternating layers of multiheaded selfattention (MSA, see Appendix A) and MLP blocks (Eq. 2, 3). Layernorm (LN) is applied before every block, and residual connections after every block (Wang et al., 2019; Baevski & Auli, 2019).


<!-- ===== page 4 | columns=1 | gutters=[] -->
<!-- p4-b000 | type=body | col=0 | bbox=108.0,84.3,337.8,94.2 -->
The MLP contains two layers with a GELU non-linearity.

<!-- p4-b001 | type=formula | col=0 | bbox=326.2,99.9,472.8,114.4 -->
$$ E ∈R(P 2·C)×D, Epos ∈R(N+1)×D $$

<!-- p4-b002 | type=body | col=0 | bbox=129.0,101.3,190.8,114.5 -->
z0 = [xclass; x1

<!-- p4-b003 | type=body | col=0 | bbox=186.9,101.3,215.1,114.9 -->
pE; x2

<!-- p4-b004 | type=formula | col=0 | bbox=211.1,101.3,261.1,114.9 -->
$$ pE; · · · ; xN $$

<!-- p4-b005 | type=body | col=0 | bbox=254.8,103.1,307.4,115.5 -->
p E] + Epos,

<!-- p4-b006 | type=body | col=0 | bbox=492.4,103.3,504.0,113.3 -->
(1)

<!-- p4-b007 | type=body | col=0 | bbox=126.8,117.0,134.2,128.8 -->
z′

<!-- p4-b008 | type=formula | col=0 | bbox=134.7,118.9,256.4,129.7 -->
$$ ℓ= MSA(LN(zℓ−1)) + zℓ−1, $$

<!-- p4-b009 | type=formula | col=0 | bbox=326.2,118.9,370.4,128.8 -->
$$ ℓ= 1 . . . L $$

<!-- p4-b010 | type=body | col=0 | bbox=492.4,119.1,504.0,129.1 -->
(2)

<!-- p4-b011 | type=formula | col=0 | bbox=129.7,132.3,234.5,144.9 -->
$$ zℓ= MLP(LN(z′ℓ)) + z′ $$

<!-- p4-b012 | type=body | col=0 | bbox=235.0,134.1,241.6,144.9 -->
ℓ,

<!-- p4-b013 | type=formula | col=0 | bbox=326.2,134.1,370.4,144.1 -->
$$ ℓ= 1 . . . L $$

<!-- p4-b014 | type=body | col=0 | bbox=492.4,134.4,504.0,144.3 -->
(3)

<!-- p4-b015 | type=body | col=0 | bbox=132.4,148.2,178.5,160.0 -->
y = LN(z0

<!-- p4-b016 | type=body | col=0 | bbox=174.5,150.0,184.4,161.8 -->
L)

<!-- p4-b017 | type=body | col=0 | bbox=492.4,150.2,504.0,160.2 -->
(4)

<!-- p4-b018 | type=body | col=0 | bbox=108.0,172.7,170.1,182.6 -->
Inductive bias.

<!-- p4-b019 | type=body | col=0 | bbox=108.0,172.7,504.0,270.4 -->
We note that Vision Transformer has much less image-speciﬁc inductive bias than CNNs. In CNNs, locality, two-dimensional neighborhood structure, and translation equivariance are baked into each layer throughout the whole model. In ViT, only MLP layers are local and translationally equivariant, while the self-attention layers are global. The two-dimensional neighborhood structure is used very sparingly: in the beginning of the model by cutting the image into patches and at ﬁne-tuning time for adjusting the position embeddings for images of different resolution (as described below). Other than that, the position embeddings at initialization time carry no information about the 2D positions of the patches and all spatial relations between the patches have to be learned from scratch.

<!-- p4-b020 | type=body | col=0 | bbox=108.0,283.7,198.1,293.7 -->
Hybrid Architecture.

<!-- p4-b021 | type=body | col=0 | bbox=108.0,283.8,504.0,304.7 -->
As an alternative to raw image patches, the input sequence can be formed from feature maps of a CNN (LeCun et al., 1989). In this hybrid model, the patch embedding

<!-- p4-b022 | type=body | col=0 | bbox=108.0,305.5,504.0,315.7 -->
projection E (Eq. 1) is applied to patches extracted from a CNN feature map. As a special case,

<!-- p4-b023 | type=body | col=0 | bbox=108.0,316.7,504.0,348.6 -->
the patches can have spatial size 1x1, which means that the input sequence is obtained by simply ﬂattening the spatial dimensions of the feature map and projecting to the Transformer dimension. The classiﬁcation input embedding and position embeddings are added as described above.

<!-- p4-b024 | type=heading | col=0 | bbox=108.2,363.4,306.8,373.3 -->
### 3.2 FINE-TUNING AND HIGHER RESOLUTION

<!-- p4-b025 | type=body | col=0 | bbox=108.0,383.9,504.0,492.5 -->
Typically, we pre-train ViT on large datasets, and ﬁne-tune to (smaller) downstream tasks. For this, we remove the pre-trained prediction head and attach a zero-initialized D × K feedforward layer, where K is the number of downstream classes. It is often beneﬁcial to ﬁne-tune at higher resolution than pre-training (Touvron et al., 2019; Kolesnikov et al., 2020). When feeding images of higher resolution, we keep the patch size the same, which results in a larger effective sequence length. The Vision Transformer can handle arbitrary sequence lengths (up to memory constraints), however, the pre-trained position embeddings may no longer be meaningful. We therefore perform 2D interpolation of the pre-trained position embeddings, according to their location in the original image. Note that this resolution adjustment and patch extraction are the only points at which an inductive bias about the 2D structure of the images is manually injected into the Vision Transformer.

<!-- p4-b026 | type=heading | col=0 | bbox=108.3,509.6,200.1,521.6 -->
## 4 EXPERIMENTS

<!-- p4-b027 | type=body | col=0 | bbox=108.0,534.6,504.0,599.3 -->
We evaluate the representation learning capabilities of ResNet, Vision Transformer (ViT), and the hybrid. To understand the data requirements of each model, we pre-train on datasets of varying size and evaluate many benchmark tasks. When considering the computational cost of pre-training the model, ViT performs very favourably, attaining state of the art on most recognition benchmarks at a lower pre-training cost. Lastly, we perform a small experiment using self-supervision, and show that self-supervised ViT holds promise for the future.

<!-- p4-b028 | type=heading | col=0 | bbox=108.2,614.1,159.6,624.1 -->
### 4.1 SETUP

<!-- p4-b029 | type=body | col=0 | bbox=108.0,634.5,504.0,644.6 -->
Datasets. To explore model scalability, we use the ILSVRC-2012 ImageNet dataset with 1k classes

<!-- p4-b030 | type=body | col=0 | bbox=108.0,645.6,504.0,732.3 -->
and 1.3M images (we refer to it as ImageNet in what follows), its superset ImageNet-21k with 21k classes and 14M images (Deng et al., 2009), and JFT (Sun et al., 2017) with 18k classes and 303M high-resolution images. We de-duplicate the pre-training datasets w.r.t. the test sets of the downstream tasks following Kolesnikov et al. (2020). We transfer the models trained on these dataset to several benchmark tasks: ImageNet on the original validation labels and the cleaned-up ReaL labels (Beyer et al., 2020), CIFAR-10/100 (Krizhevsky, 2009), Oxford-IIIT Pets (Parkhi et al., 2012), and Oxford Flowers-102 (Nilsback & Zisserman, 2008). For these datasets, pre-processing follows Kolesnikov et al. (2020).


<!-- ===== page 5 | columns=1 | gutters=[] -->
<!-- p5-b000 | type=table | col=-1 | bbox=177.1,86.3,434.9,129.3 -->
[table T1]
Model | Layers | D Hidden size | MLP size | Heads | Params
ViT-Base
ViT-Large
ViT-Huge | 12
24
32 | 768
1024
1280 | 3072
4096
5120 | 12
16
16 | 86M
307M
632M

<!-- p5-b001 | type=caption | col=0 | bbox=196.8,143.0,415.1,153.0 -->
Table 1: Details of Vision Transformer model variants.

<!-- p5-b002 | type=body | col=0 | bbox=108.0,174.1,504.0,216.9 -->
We also evaluate on the 19-task VTAB classiﬁcation suite (Zhai et al., 2019b). VTAB evaluates low-data transfer to diverse tasks, using 1 000 training examples per task. The tasks are divided into three groups: Natural – tasks like the above, Pets, CIFAR, etc. Specialized – medical and satellite imagery, and Structured – tasks that require geometric understanding like localization.

<!-- p5-b003 | type=body | col=0 | bbox=108.0,223.8,504.0,233.8 -->
Model Variants. We base ViT conﬁgurations on those used for BERT (Devlin et al., 2019), as

<!-- p5-b004 | type=body | col=0 | bbox=108.0,234.8,504.0,288.6 -->
summarized in Table 1. The “Base” and “Large” models are directly adopted from BERT and we add the larger “Huge” model. In what follows we use brief notation to indicate the model size and the input patch size: for instance, ViT-L/16 means the “Large” variant with 16×16 input patch size. Note that the Transformer’s sequence length is inversely proportional to the square of the patch size, thus models with smaller patch size are computationally more expensive.

<!-- p5-b005 | type=body | col=0 | bbox=108.0,295.6,504.0,382.3 -->
For the baseline CNNs, we use ResNet (He et al., 2016), but replace the Batch Normalization layers (Ioffe & Szegedy, 2015) with Group Normalization (Wu & He, 2018), and used standardized convolutions (Qiao et al., 2019). These modiﬁcations improve transfer (Kolesnikov et al., 2020), and we denote the modiﬁed model “ResNet (BiT)”. For the hybrids, we feed the intermediate feature maps into ViT with patch size of one “pixel”. To experiment with different sequence lengths, we either (i) take the output of stage 4 of a regular ResNet50 or (ii) remove stage 4, place the same number of layers in stage 3 (keeping the total number of layers), and take the output of this extended stage 3. Option (ii) results in a 4x longer sequence length, and a more expensive ViT model.

<!-- p5-b006 | type=body | col=0 | bbox=108.0,389.2,504.0,399.2 -->
Training & Fine-tuning. We train all models, including ResNets, using Adam (Kingma & Ba,

<!-- p5-b007 | type=body | col=0 | bbox=108.0,400.0,504.0,475.9 -->
2015) with β1 = 0.9, β2 = 0.999, a batch size of 4096 and apply a high weight decay of 0.1, which we found to be useful for transfer of all models (Appendix D.1 shows that, in contrast to common practices, Adam works slightly better than SGD for ResNets in our setting). We use a linear learning rate warmup and decay, see Appendix B.1 for details. For ﬁne-tuning we use SGD with momentum, batch size 512, for all models, see Appendix B.1.1. For ImageNet results in Table 2, we ﬁne-tuned at higher resolution: 512 for ViT-L/16 and 518 for ViT-H/14, and also used Polyak & Juditsky (1992) averaging with a factor of 0.9999 (Ramachandran et al., 2019; Wang et al., 2020b).

<!-- p5-b008 | type=body | col=0 | bbox=108.0,482.8,504.0,492.9 -->
Metrics. We report results on downstream datasets either through few-shot or ﬁne-tuning accuracy.

<!-- p5-b009 | type=body | col=0 | bbox=108.0,493.9,504.0,558.6 -->
Fine-tuning accuracies capture the performance of each model after ﬁne-tuning it on the respective dataset. Few-shot accuracies are obtained by solving a regularized least-squares regression problem that maps the (frozen) representation of a subset of training images to {−1, 1}K target vectors. This formulation allows us to recover the exact solution in closed form. Though we mainly focus on ﬁne-tuning performance, we sometimes use linear few-shot accuracies for fast on-the-ﬂy evaluation where ﬁne-tuning would be too costly.

<!-- p5-b010 | type=heading | col=0 | bbox=108.2,574.8,286.6,584.8 -->
### 4.2 COMPARISON TO STATE OF THE ART

<!-- p5-b011 | type=body | col=0 | bbox=108.0,595.8,504.0,682.5 -->
We ﬁrst compare our largest models – ViT-H/14 and ViT-L/16 – to state-of-the-art CNNs from the literature. The ﬁrst comparison point is Big Transfer (BiT) (Kolesnikov et al., 2020), which performs supervised transfer learning with large ResNets. The second is Noisy Student (Xie et al., 2020), which is a large EfﬁcientNet trained using semi-supervised learning on ImageNet and JFT- 300M with the labels removed. Currently, Noisy Student is the state of the art on ImageNet and BiT-L on the other datasets reported here. All models were trained on TPUv3 hardware, and we report the number of TPUv3-core-days taken to pre-train each of them, that is, the number of TPU v3 cores (2 per chip) used for training multiplied by the training time in days.

<!-- p5-b012 | type=caption | col=0 | bbox=108.0,689.4,504.0,732.3 -->
Table 2 shows the results. The smaller ViT-L/16 model pre-trained on JFT-300M outperforms BiT-L (which is pre-trained on the same dataset) on all tasks, while requiring substantially less computational resources to train. The larger model, ViT-H/14, further improves the performance, especially on the more challenging datasets – ImageNet, CIFAR-100, and the VTAB suite. Interestingly, this


<!-- ===== page 6 | columns=1 | gutters=[] -->
<!-- p6-b000 | type=table | col=-1 | bbox=115.8,85.9,496.2,193.7 -->
[table T2]
 | Ours-JFT
(ViT-H/14) | Ours-JFT
(ViT-L/16) | Ours-I21k
(ViT-L/16) | BiT-L
(ResNet152x4) | Noisy Student
(EfﬁcientNet-L2)
ImageNet
ImageNet ReaL | 88.55 ± 0.04
90.72 ± 0.05 | 87.76 ± 0.03
90.54 ± 0.03 | 85.30 ± 0.02
88.62 ± 0.05 | 87.54 ± 0.02
90.54 | 88.4/88.5∗
90.55
CIFAR-10 | 99.50 ± 0.06 | 99.42 ± 0.03 | 99.15 ± 0.03 | 99.37 ± 0.06 | −
CIFAR-100 | 94.55 ± 0.04 | 93.90 ± 0.05 | 93.25 ± 0.05 | 93.51 ± 0.08 | −
Oxford-IIIT Pets | 97.56 ± 0.03 | 97.32 ± 0.11 | 94.67 ± 0.15 | 96.62 ± 0.23 | −
Oxford Flowers-102 | 99.68 ± 0.02 | 99.74 ± 0.00 | 99.61 ± 0.02 | 99.63 ± 0.03 | −
VTAB (19 tasks) | 77.63 ± 0.23 | 76.28 ± 0.46 | 72.72 ± 0.21 | 76.29 ± 1.70 | −
TPUv3-core-days | 2.5k | 0.68k | 0.23k | 9.9k | 12.3k

<!-- p6-b001 | type=body | col=0 | bbox=108.0,184.8,504.0,272.0 -->
TPUv3-core-days Table 2: Comparison with state of the art on popular image classiﬁcation benchmarks. We report mean and standard deviation of the accuracies, averaged over three ﬁne-tuning runs. Vision Transformer models pre-trained on the JFT-300M dataset outperform ResNet-based baselines on all datasets, while taking substantially less computational resources to pre-train. ViT pre-trained on the smaller public ImageNet-21k dataset performs well too. ∗Slightly improved 88.5% result reported in Touvron et al. (2020).

<!-- p6-b002 | type=figure | col=-1 | bbox=108.0,283.7,504.0,896.8 -->
![Figure 2: Breakdown of VTAB performance in Natural, Specialized, and Structured task groups. model still took substantially less compute to pre-train than prior state of the art. However, we note that pre-training efﬁciency may be affected not only by the architecture choice, but also other parameters, such as training schedule, optimizer, weight decay, etc. We provide a controlled study of performance vs. compute for different architectures in Section 4.4. Finally, the ViT-L/16 model pre-trained on the public ImageNet-21k dataset performs well on most datasets too, while taking fewer resources to pre-train: it could be trained using a standard cloud TPUv3 with 8 cores in approximately 30 days.](figures/F2.png)

<!-- p6-b003 | type=figure | col=-1 | bbox=108.0,283.7,504.0,896.8 -->
![Figure 2 decomposes the VTAB tasks into their respective groups, and compares to previous SOTA methods on this benchmark: BiT, VIVI – a ResNet co-trained on ImageNet and Youtube (Tschannen et al., 2020), and S4L – supervised plus semi-supervised learning on ImageNet (Zhai et al., 2019a). ViT-H/14 outperforms BiT-R152x4, and other methods, on the Natural and Structured tasks. On the Specialized the performance of the top two models is similar.](figures/F3.png)

<!-- p6-b028 | type=caption | col=0 | bbox=108.0,391.0,504.0,490.9 -->
Figure 2: Breakdown of VTAB performance in Natural, Specialized, and Structured task groups. model still took substantially less compute to pre-train than prior state of the art. However, we note that pre-training efﬁciency may be affected not only by the architecture choice, but also other parameters, such as training schedule, optimizer, weight decay, etc. We provide a controlled study of performance vs. compute for different architectures in Section 4.4. Finally, the ViT-L/16 model pre-trained on the public ImageNet-21k dataset performs well on most datasets too, while taking fewer resources to pre-train: it could be trained using a standard cloud TPUv3 with 8 cores in approximately 30 days.

<!-- p6-b029 | type=caption | col=0 | bbox=108.0,497.8,504.0,551.6 -->
Figure 2 decomposes the VTAB tasks into their respective groups, and compares to previous SOTA methods on this benchmark: BiT, VIVI – a ResNet co-trained on ImageNet and Youtube (Tschannen et al., 2020), and S4L – supervised plus semi-supervised learning on ImageNet (Zhai et al., 2019a). ViT-H/14 outperforms BiT-R152x4, and other methods, on the Natural and Structured tasks. On the Specialized the performance of the top two models is similar.

<!-- p6-b030 | type=heading | col=0 | bbox=108.2,567.1,292.4,577.1 -->
### 4.3 PRE-TRAINING DATA REQUIREMENTS

<!-- p6-b031 | type=body | col=0 | bbox=108.0,587.9,504.0,619.7 -->
The Vision Transformer performs well when pre-trained on a large JFT-300M dataset. With fewer inductive biases for vision than ResNets, how crucial is the dataset size? We perform two series of experiments.

<!-- p6-b032 | type=body | col=0 | bbox=108.0,626.7,504.0,702.4 -->
First, we pre-train ViT models on datasets of increasing size: ImageNet, ImageNet-21k, and JFT- 300M. To boost the performance on the smaller datasets, we optimize three basic regularization parameters – weight decay, dropout, and label smoothing. Figure 3 shows the results after ﬁnetuning to ImageNet (results on other datasets are shown in Table 5)2. When pre-trained on the smallest dataset, ImageNet, ViT-Large models underperform compared to ViT-Base models, despite (moderate) regularization. With ImageNet-21k pre-training, their performances are similar. Only with JFT-300M, do we see the full beneﬁt of larger models. Figure 3 also shows the performance

<!-- p6-b033 | type=body | col=0 | bbox=108.0,711.6,504.0,732.0 -->
2Note that the ImageNet pre-trained models are also ﬁne-tuned, but again on ImageNet. This is because the resolution increase during ﬁne-tuning improves the performance.


<!-- ===== page 7 | columns=1 | gutters=[] -->
<!-- p7-b000 | type=figure | col=-1 | bbox=108.0,81.9,294.1,236.0 -->
![Figure 3: Transfer to ImageNet.](figures/F4.png)

<!-- p7-b001 | type=figure | col=-1 | bbox=108.0,81.9,493.8,290.8 -->
![Figure 4: Linear few-shot evaluation on Imalarge ViT models perform worse than BiT geNet versus pre-training size. ResNets per- ResNets (shaded area) when pre-trained on form better with smaller pre-training datasets small datasets, they shine when pre-trained on but plateau sooner than ViT, which performs larger datasets. Similarly, larger ViT variants better with larger pre-training. ViT-b is ViT-B overtake smaller ones as the dataset grows.](figures/F5.png)

<!-- p7-b019 | type=formula | col=0 | bbox=353.0,177.0,416.1,186.8 -->
$$ ViT-L/32 ViT-b/32 $$

<!-- p7-b032 | type=caption | col=0 | bbox=108.0,226.0,254.9,236.0 -->
Figure 3: Transfer to ImageNet.

<!-- p7-b033 | type=caption | col=0 | bbox=108.0,226.0,493.8,290.8 -->
Figure 4: Linear few-shot evaluation on Imalarge ViT models perform worse than BiT geNet versus pre-training size. ResNets per- ResNets (shaded area) when pre-trained on form better with smaller pre-training datasets small datasets, they shine when pre-trained on but plateau sooner than ViT, which performs larger datasets. Similarly, larger ViT variants better with larger pre-training. ViT-b is ViT-B overtake smaller ones as the dataset grows.

<!-- p7-b034 | type=body | col=0 | bbox=307.7,280.8,446.7,290.8 -->
with all hidden dimensions halved.

<!-- p7-b035 | type=footnote | col=0 | bbox=209.8,309.4,244.1,321.3 -->
Average-5

<!-- p7-b036 | type=footnote | col=0 | bbox=386.7,309.4,418.7,321.3 -->
ImageNet

<!-- p7-b037 | type=footnote | col=0 | bbox=311.6,315.9,318.7,326.3 -->
90

<!-- p7-b038 | type=footnote | col=0 | bbox=135.8,342.2,142.9,352.6 -->
95

<!-- p7-b040 | type=footnote | col=0 | bbox=311.6,355.4,318.7,365.8 -->
85

<!-- p7-b041 | type=footnote | col=0 | bbox=311.6,394.9,318.7,405.3 -->
80

<!-- p7-b044 | type=footnote | col=0 | bbox=135.8,408.1,142.9,418.5 -->
90

<!-- p7-b049 | type=footnote | col=0 | bbox=311.6,434.4,318.7,444.8 -->
75

<!-- p7-b050 | type=footnote | col=0 | bbox=171.1,440.1,180.8,450.9 -->
102

<!-- p7-b051 | type=footnote | col=0 | bbox=247.2,440.1,256.9,450.9 -->
103

<!-- p7-b052 | type=footnote | col=0 | bbox=346.8,440.1,356.5,450.9 -->
102

<!-- p7-b053 | type=footnote | col=0 | bbox=422.9,440.1,432.6,450.9 -->
103

<!-- p7-b054 | type=footnote | col=0 | bbox=240.0,451.5,369.2,463.4 -->
Total pre-training compute [exaFLOPs]

<!-- p7-b055 | type=body | col=0 | bbox=108.0,475.1,504.0,517.9 -->
Figure 5: Performance versus pre-training compute for different architectures: Vision Transformers, ResNets, and hybrids. Vision Transformers generally outperform ResNets with the same computational budget. Hybrids improve upon pure Transformers for smaller model sizes, but the gap vanishes for larger models.

<!-- p7-b056 | type=body | col=0 | bbox=108.0,546.0,504.0,566.9 -->
region spanned by BiT models of different sizes. The BiT CNNs outperform ViT on ImageNet, but with the larger datasets, ViT overtakes.

<!-- p7-b057 | type=body | col=0 | bbox=108.0,573.9,504.0,693.4 -->
Second, we train our models on random subsets of 9M, 30M, and 90M as well as the full JFT- 300M dataset. We do not perform additional regularization on the smaller subsets and use the same hyper-parameters for all settings. This way, we assess the intrinsic model properties, and not the effect of regularization. We do, however, use early-stopping, and report the best validation accuracy achieved during training. To save compute, we report few-shot linear accuracy instead of full ﬁnetuning accuracy. Figure 4 contains the results. Vision Transformers overﬁt more than ResNets with comparable computational cost on smaller datasets. For example, ViT-B/32 is slightly faster than ResNet50; it performs much worse on the 9M subset, but better on 90M+ subsets. The same is true for ResNet152x2 and ViT-L/16. This result reinforces the intuition that the convolutional inductive bias is useful for smaller datasets, but for larger ones, learning the relevant patterns directly from data is sufﬁcient, even beneﬁcial.

<!-- p7-b058 | type=body | col=0 | bbox=108.0,700.4,504.0,732.3 -->
Overall, the few-shot results on ImageNet (Figure 4), as well as the low-data results on VTAB (Table 2) seem promising for very low-data transfer. Further analysis of few-shot properties of ViT is an exciting direction of future work.


<!-- ===== page 8 | columns=2 | gutters=[[295.0, 384.0]] -->
<!-- p8-b000 | type=heading | col=0 | bbox=108.2,84.3,202.9,94.2 -->
### 4.4 SCALING STUDY

<!-- p8-b001 | type=body | col=-1 | bbox=108.0,105.3,504.0,192.0 -->
We perform a controlled scaling study of different models by evaluating transfer performance from JFT-300M. In this setting data size does not bottleneck the models’ performances, and we assess performance versus pre-training cost of each model. The model set includes: 7 ResNets, R50x1, R50x2 R101x1, R152x1, R152x2, pre-trained for 7 epochs, plus R152x2 and R200x3 pre-trained for 14 epochs; 6 Vision Transformers, ViT-B/32, B/16, L/32, L/16, pre-trained for 7 epochs, plus L/16 and H/14 pre-trained for 14 epochs; and 5 hybrids, R50+ViT-B/32, B/16, L/32, L/16 pretrained for 7 epochs, plus R50+ViT-L/16 pre-trained for 14 epochs (for hybrids, the number at the end of the model name stands not for the patch size, but for the total dowsampling ratio in the ResNet

<!-- p8-b002 | type=body | col=0 | bbox=108.0,193.0,152.0,203.0 -->
backbone).

<!-- p8-b003 | type=body | col=-1 | bbox=108.0,209.9,504.0,296.6 -->
Figure 5 contains the transfer performance versus total pre-training compute (see Appendix D.5 for details on computational costs). Detailed results per model are provided in Table 6 in the Appendix. A few patterns can be observed. First, Vision Transformers dominate ResNets on the performance/compute trade-off. ViT uses approximately 2 −4× less compute to attain the same performance (average over 5 datasets). Second, hybrids slightly outperform ViT at small computational budgets, but the difference vanishes for larger models. This result is somewhat surprising, since one might expect convolutional local feature processing to assist ViT at any size. Third, Vision Transformers appear not to saturate within the range tried, motivating future scaling efforts.

<!-- p8-b004 | type=heading | col=0 | bbox=108.2,313.1,285.6,323.0 -->
### 4.5 INSPECTING VISION TRANSFORMER

<!-- p8-b005 | type=body | col=-1 | bbox=108.0,334.1,375.2,409.8 -->
To begin to understand how the Vision Transformer processes image data, we analyze its internal representations. The ﬁrst layer of the Vision Transformer linearly projects the ﬂattened patches into a lower-dimensional space (Eq. 1). Figure 7 (left) shows the top principal components of the the learned embedding ﬁlters. The components resemble plausible basis functions for a low-dimensional representation of the ﬁne structure within each patch.

<!-- p8-b006 | type=figure | col=1 | bbox=385.2,339.7,504.0,543.0 -->
![Figure 6: Representative ex-](figures/F6.png)

<!-- p8-b009 | type=body | col=-1 | bbox=108.0,416.8,375.2,514.5 -->
After the projection, a learned position embedding is added to the patch representations. Figure 7 (center) shows that the model learns to encode distance within the image in the similarity of position embeddings, i.e. closer patches tend to have more similar position embeddings. Further, the row-column structure appears; patches in the same row/column have similar embeddings. Finally, a sinusoidal structure is sometimes apparent for larger grids (Appendix D). That the position embeddings learn to represent 2D image topology explains why hand-crafted 2D-aware embedding variants do not yield

<!-- p8-b010 | type=body | col=0 | bbox=108.0,515.4,232.8,525.4 -->
improvements (Appendix D.4).

<!-- p8-b011 | type=body | col=-1 | bbox=108.0,532.4,504.0,575.2 -->
Self-attention allows ViT to integrate information across the entire image even in the lowest layers. We investigate to what degree amples of attention from the the network makes use of this capability. Speciﬁcally, we compute output token to the input the average distance in image space across which information is

<!-- p8-b012 | type=caption | col=1 | bbox=385.2,533.1,504.0,543.0 -->
Figure 6: Representative ex-

<!-- p8-b013 | type=body | col=1 | bbox=385.2,566.0,504.0,586.9 -->
space. See Appendix D.7 for details.

<!-- p8-b014 | type=body | col=-1 | bbox=108.0,576.2,504.0,673.9 -->
integrated, based on the attention weights (Figure 7, right). This “attention distance” is analogous to receptive ﬁeld size in CNNs. We ﬁnd that some heads attend to most of the image already in the lowest layers, showing that the ability to integrate information globally is indeed used by the model. Other attention heads have consistently small attention distances in the low layers. This highly localized attention is less pronounced in hybrid models that apply a ResNet before the Transformer (Figure 7, right), suggesting that it may serve a similar function as early convolutional layers in CNNs. Further, the attention distance increases with network depth. Globally, we ﬁnd that the model attends to image regions that are semantically relevant for classiﬁcation (Figure 6).

<!-- p8-b015 | type=heading | col=0 | bbox=108.2,690.3,213.7,700.2 -->
### 4.6 SELF-SUPERVISION

<!-- p8-b016 | type=body | col=-1 | bbox=108.0,711.4,504.0,732.3 -->
Transformers show impressive performance on NLP tasks. However, much of their success stems not only from their excellent scalability but also from large scale self-supervised pre-training (Devlin


<!-- ===== page 9 | columns=2 | gutters=[[363.0, 430.0]] -->
<!-- p9-b001 | type=figure | col=-1 | bbox=108.0,101.2,504.0,229.4 -->
![Figure 7: Left: Filters of the initial linear embedding of RGB values of ViT-L/32. Center: Sim-](figures/F7.png)

<!-- p9-b017 | type=caption | col=-1 | bbox=108.0,219.3,504.0,229.4 -->
Figure 7: Left: Filters of the initial linear embedding of RGB values of ViT-L/32. Center: Sim-

<!-- p9-b018 | type=body | col=-1 | bbox=108.0,230.4,504.0,251.3 -->
ilarity of position embeddings of ViT-L/32. Tiles show the cosine similarity between the position embedding of the patch with the indicated row and column and the position embeddings of all other

<!-- p9-b019 | type=body | col=-1 | bbox=108.0,252.2,504.0,262.3 -->
patches. Right: Size of attended area by head and network depth. Each dot shows the mean attention

<!-- p9-b020 | type=body | col=-1 | bbox=108.0,263.3,450.6,273.2 -->
distance across images for one of 16 heads at one layer. See Appendix D.7 for details.

<!-- p9-b021 | type=body | col=-1 | bbox=108.0,307.6,504.0,372.5 -->
et al., 2019; Radford et al., 2018). We also perform a preliminary exploration on masked patch prediction for self-supervision, mimicking the masked language modeling task used in BERT. With self-supervised pre-training, our smaller ViT-B/16 model achieves 79.9% accuracy on ImageNet, a signiﬁcant improvement of 2% to training from scratch, but still 4% behind supervised pre-training. Appendix B.1.2 contains further details. We leave exploration of contrastive pre-training (Chen et al., 2020b; He et al., 2020; Bachman et al., 2019; H´enaff et al., 2020) to future work.

<!-- p9-b022 | type=heading | col=0 | bbox=108.3,389.6,195.4,401.5 -->
## 5 CONCLUSION

<!-- p9-b023 | type=body | col=-1 | bbox=108.0,414.4,504.0,479.1 -->
We have explored the direct application of Transformers to image recognition. Unlike prior works using self-attention in computer vision, we do not introduce image-speciﬁc inductive biases into the architecture apart from the initial patch extraction step. Instead, we interpret an image as a sequence of patches and process it by a standard Transformer encoder as used in NLP. This simple, yet scalable, strategy works surprisingly well when coupled with pre-training on large datasets. Thus, Vision Transformer matches or exceeds the state of the art on many image classiﬁcation

<!-- p9-b024 | type=body | col=0 | bbox=108.0,480.1,308.5,490.1 -->
datasets, whilst being relatively cheap to pre-train.

<!-- p9-b025 | type=body | col=-1 | bbox=108.0,497.1,504.0,561.8 -->
While these initial results are encouraging, many challenges remain. One is to apply ViT to other computer vision tasks, such as detection and segmentation. Our results, coupled with those in Carion et al. (2020), indicate the promise of this approach. Another challenge is to continue exploring selfsupervised pre-training methods. Our initial experiments show improvement from self-supervised pre-training, but there is still large gap between self-supervised and large-scale supervised pretraining. Finally, further scaling of ViT would likely lead to improved performance.

<!-- p9-b026 | type=heading | col=0 | bbox=108.3,578.8,224.9,590.8 -->
## ACKNOWLEDGEMENTS

<!-- p9-b027 | type=body | col=-1 | bbox=108.0,603.6,504.0,657.4 -->
The work was performed in Berlin, Z¨urich, and Amsterdam. We thank many colleagues at Google for their help, in particular Andreas Steiner for crucial help with the infrastructure and the opensource release of the code; Joan Puigcerver and Maxim Neumann for help with the large-scale training infrastructure; Dmitry Lepikhin, Aravindh Mahendran, Daniel Keysers, Mario Luˇci´c, Noam Shazeer, Ashish Vaswani, and Colin Raffel for useful discussions.

<!-- p9-b028 | type=heading | col=0 | bbox=108.3,674.5,175.3,686.4 -->
## REFERENCES

<!-- p9-b029 | type=reference | col=-1 | bbox=108.0,693.1,504.0,721.3 -->
Samira Abnar and Willem Zuidema. Quantifying attention ﬂow in transformers. In ACL, 2020. Philip Bachman, R Devon Hjelm, and William Buchwalter. Learning representations by maximizing

<!-- p9-b030 | type=reference | col=0 | bbox=118.0,722.1,326.6,732.3 -->
mutual information across views. In NeurIPS, 2019.


<!-- ===== page 10 | columns=1 | gutters=[] -->
<!-- p10-b000 | type=reference | col=0 | bbox=108.0,84.3,504.0,94.2 -->
Alexei Baevski and Michael Auli. Adaptive input representations for neural language modeling. In

<!-- p10-b001 | type=reference | col=0 | bbox=108.0,95.0,504.0,124.9 -->
ICLR, 2019. I. Bello, B. Zoph, Q. Le, A. Vaswani, and J. Shlens. Attention augmented convolutional networks.

<!-- p10-b002 | type=reference | col=0 | bbox=108.0,125.8,504.0,155.6 -->
In ICCV, 2019. Lucas Beyer, Olivier J. H´enaff, Alexander Kolesnikov, Xiaohua Zhai, and A¨aron van den Oord. Are

<!-- p10-b003 | type=reference | col=0 | bbox=108.0,156.4,504.0,186.3 -->
we done with imagenet? arXiv, 2020. Tom B Brown, Benjamin Mann, Nick Ryder, Melanie Subbiah, Jared Kaplan, Prafulla Dhariwal,

<!-- p10-b004 | type=reference | col=0 | bbox=118.0,187.3,504.0,208.2 -->
Arvind Neelakantan, Pranav Shyam, Girish Sastry, Amanda Askell, et al. Language models are few-shot learners. arXiv, 2020.

<!-- p10-b005 | type=reference | col=0 | bbox=108.0,218.0,504.0,228.0 -->
Nicolas Carion, Francisco Massa, Gabriel Synnaeve, Nicolas Usunier, Alexander Kirillov, and

<!-- p10-b006 | type=reference | col=0 | bbox=108.0,228.8,504.0,258.7 -->
Sergey Zagoruyko. End-to-end object detection with transformers. In ECCV, 2020. Mark Chen, Alec Radford, Rewon Child, Jeff Wu, and Heewoo Jun. Generative pretraining from

<!-- p10-b007 | type=reference | col=0 | bbox=108.0,259.5,504.0,289.4 -->
pixels. In ICML, 2020a. Ting Chen, Simon Kornblith, Mohammad Norouzi, and Geoffrey E. Hinton. A simple framework

<!-- p10-b008 | type=reference | col=0 | bbox=108.0,290.2,504.0,320.1 -->
for contrastive learning of visual representations. In ICML, 2020b. Yen-Chun Chen, Linjie Li, Licheng Yu, Ahmed El Kholy, Faisal Ahmed, Zhe Gan, Yu Cheng, and

<!-- p10-b009 | type=reference | col=0 | bbox=108.0,320.9,504.0,350.8 -->
Jingjing Liu. UNITER: UNiversal Image-TExt Representation Learning. In ECCV, 2020c. Rewon Child, Scott Gray, Alec Radford, and Ilya Sutskever. Generating long sequences with sparse

<!-- p10-b010 | type=reference | col=0 | bbox=108.0,351.6,504.0,381.5 -->
transformers. arXiv, 2019. Jean-Baptiste Cordonnier, Andreas Loukas, and Martin Jaggi. On the relationship between self-

<!-- p10-b011 | type=reference | col=0 | bbox=108.0,382.3,504.0,412.2 -->
attention and convolutional layers. In ICLR, 2020. J. Deng, W. Dong, R. Socher, L. Li, Kai Li, and Li Fei-Fei. Imagenet: A large-scale hierarchical

<!-- p10-b012 | type=reference | col=0 | bbox=108.0,413.0,504.0,442.9 -->
image database. In CVPR, 2009. Jacob Devlin, Ming-Wei Chang, Kenton Lee, and Kristina Toutanova. BERT: Pre-training of deep

<!-- p10-b013 | type=reference | col=0 | bbox=108.0,443.7,504.0,473.6 -->
bidirectional transformers for language understanding. In NAACL, 2019. Josip Djolonga, Jessica Yung, Michael Tschannen, Rob Romijnders, Lucas Beyer, Alexander

<!-- p10-b014 | type=reference | col=0 | bbox=118.0,474.6,504.0,506.4 -->
Kolesnikov, Joan Puigcerver, Matthias Minderer, Alexander D’Amour, Dan Moldovan, Sylvan Gelly, Neil Houlsby, Xiaohua Zhai, and Mario Lucic. On robustness and transferability of convolutional neural networks. arXiv, 2020.

<!-- p10-b015 | type=reference | col=0 | bbox=108.0,516.2,504.0,526.2 -->
Kaiming He, Xiangyu Zhang, Shaoqing Ren, and Jian Sun. Deep residual learning for image recog-

<!-- p10-b016 | type=reference | col=0 | bbox=108.0,527.0,504.0,556.9 -->
nition. In CVPR, 2016. Kaiming He, Haoqi Fan, Yuxin Wu, Saining Xie, and Ross Girshick. Momentum contrast for

<!-- p10-b017 | type=reference | col=0 | bbox=108.0,557.7,504.0,587.6 -->
unsupervised visual representation learning. In CVPR, 2020. Jonathan Ho, Nal Kalchbrenner, Dirk Weissenborn, and Tim Salimans. Axial attention in multidi-

<!-- p10-b018 | type=reference | col=0 | bbox=108.0,588.4,504.0,618.3 -->
mensional transformers. arXiv, 2019. Han Hu, Jiayuan Gu, Zheng Zhang, Jifeng Dai, and Yichen Wei. Relation networks for object

<!-- p10-b019 | type=reference | col=0 | bbox=108.0,619.1,504.0,649.0 -->
detection. In CVPR, 2018. Han Hu, Zheng Zhang, Zhenda Xie, and Stephen Lin. Local relation networks for image recognition.

<!-- p10-b020 | type=reference | col=0 | bbox=108.0,649.8,504.0,679.6 -->
In ICCV, 2019. Zilong Huang, Xinggang Wang, Yunchao Wei, Lichao Huang, Humphrey Shi, Wenyu Liu, and

<!-- p10-b021 | type=reference | col=0 | bbox=108.0,680.5,504.0,710.4 -->
Thomas S. Huang. Ccnet: Criss-cross attention for semantic segmentation. In ICCV, 2020. Olivier J. H´enaff, Aravind Srinivas, Jeffrey De Fauw, Ali Razavi, Carl Doersch, S. M. Ali Eslami,

<!-- p10-b022 | type=reference | col=0 | bbox=118.0,711.4,504.0,732.3 -->
and Aaron van den Oord. Data-efﬁcient image recognition with contrastive predictive coding. In ICML, 2020.


<!-- ===== page 11 | columns=1 | gutters=[] -->
<!-- p11-b000 | type=reference | col=0 | bbox=108.0,84.3,504.0,94.2 -->
Sergey Ioffe and Christian Szegedy. Batch normalization: Accelerating deep network training by

<!-- p11-b001 | type=reference | col=0 | bbox=108.0,95.2,504.0,143.8 -->
reducing internal covariate shift. 2015. Diederik P. Kingma and Jimmy Ba. Adam: A method for stochastic optimization. In ICLR, 2015. Alexander Kolesnikov, Lucas Beyer, Xiaohua Zhai, Joan Puigcerver, Jessica Yung, Sylvain Gelly,

<!-- p11-b002 | type=reference | col=0 | bbox=108.0,144.6,504.0,193.3 -->
and Neil Houlsby. Big transfer (BiT): General visual representation learning. In ECCV, 2020. Alex Krizhevsky. Learning multiple layers of features from tiny images. Technical report, 2009. Alex Krizhevsky, Ilya Sutskever, and Geoffrey E. Hinton. Imagenet classiﬁcation with deep convo-

<!-- p11-b003 | type=reference | col=0 | bbox=108.0,194.2,504.0,223.6 -->
lutional neural networks. In NIPS, 2012. Y. LeCun, B. Boser, J. Denker, D. Henderson, R. Howard, W. Hubbard, and L. Jackel. Backpropa-

<!-- p11-b004 | type=reference | col=0 | bbox=108.0,224.4,504.0,253.9 -->
gation applied to handwritten zip code recognition. Neural Computation, 1:541–551, 1989. Dmitry Lepikhin, HyoukJoong Lee, Yuanzhong Xu, Dehao Chen, Orhan Firat, Yanping Huang,

<!-- p11-b005 | type=reference | col=0 | bbox=118.0,254.9,504.0,275.8 -->
Maxim Krikun, Noam Shazeer, and Zhifeng Chen. Gshard: Scaling giant models with conditional computation and automatic sharding. arXiv, 2020.

<!-- p11-b006 | type=reference | col=0 | bbox=108.0,285.1,504.0,295.1 -->
Liunian Harold Li, Mark Yatskar, Da Yin, Cho-Jui Hsieh, and Kai-Wei Chang. VisualBERT: A

<!-- p11-b007 | type=reference | col=0 | bbox=108.0,295.9,504.0,325.3 -->
Simple and Performant Baseline for Vision and Language. In Arxiv, 2019. Francesco Locatello, Dirk Weissenborn, Thomas Unterthiner, Aravindh Mahendran, Georg Heigold,

<!-- p11-b008 | type=reference | col=0 | bbox=118.0,326.3,504.0,347.2 -->
Jakob Uszkoreit, Alexey Dosovitskiy, and Thomas Kipf. Object-centric learning with slot attention. arXiv, 2020.

<!-- p11-b009 | type=reference | col=0 | bbox=108.0,356.6,504.0,366.6 -->
Jiasen Lu, Dhruv Batra, Devi Parikh, and Stefan Lee. ViLBERT: Pretraining Task-Agnostic Visi-

<!-- p11-b010 | type=reference | col=0 | bbox=108.0,367.4,504.0,396.8 -->
olinguistic Representations for Vision-and-Language Tasks. In NeurIPS. 2019. Dhruv Mahajan, Ross Girshick, Vignesh Ramanathan, Kaiming He, Manohar Paluri, Yixuan Li,

<!-- p11-b011 | type=reference | col=0 | bbox=118.0,397.8,504.0,418.7 -->
Ashwin Bharambe, and Laurens van der Maaten. Exploring the limits of weakly supervised pretraining. In ECCV, 2018.

<!-- p11-b012 | type=reference | col=0 | bbox=108.0,428.1,504.0,438.0 -->
M. Nilsback and A. Zisserman. Automated ﬂower classiﬁcation over a large number of classes. In

<!-- p11-b013 | type=reference | col=0 | bbox=108.0,438.9,504.0,468.3 -->
ICVGIP, 2008. Omkar M. Parkhi, Andrea Vedaldi, Andrew Zisserman, and C. V. Jawahar. Cats and dogs. In CVPR,

<!-- p11-b014 | type=reference | col=0 | bbox=108.0,469.3,504.0,498.5 -->
2012. Niki Parmar, Ashish Vaswani, Jakob Uszkoreit, Lukasz Kaiser, Noam Shazeer, Alexander Ku, and

<!-- p11-b015 | type=reference | col=0 | bbox=108.0,499.4,504.0,528.8 -->
Dustin Tran. Image transformer. In ICML, 2018. B. T. Polyak and A. B. Juditsky. Acceleration of stochastic approximation by averaging. SIAM

<!-- p11-b016 | type=reference | col=0 | bbox=118.0,529.6,370.0,539.8 -->
Journal on Control and Optimization, 30(4):838–855, 1992.

<!-- p11-b017 | type=reference | col=0 | bbox=379.6,529.8,504.0,539.8 -->
doi: 10.1137/0330046. URL

<!-- p11-b018 | type=reference | col=0 | bbox=108.0,540.2,504.0,570.0 -->
https://doi.org/10.1137/0330046. Siyuan Qiao, Huiyu Wang, Chenxi Liu, Wei Shen, and Alan Yuille. Weight standardization. arXiv

<!-- p11-b019 | type=reference | col=0 | bbox=108.0,570.8,504.0,600.3 -->
preprint arXiv:1903.10520, 2019. Alec Radford, Karthik Narasimhan, Tim Salimans, and Ilya Sutskever. Improving language under-

<!-- p11-b020 | type=reference | col=0 | bbox=108.0,601.1,504.0,630.5 -->
standing with unsupervised learning. Technical Report, 2018. Alec Radford, Jeff Wu, Rewon Child, David Luan, Dario Amodei, and Ilya Sutskever. Language

<!-- p11-b021 | type=reference | col=0 | bbox=108.0,631.4,504.0,660.8 -->
models are unsupervised multitask learners. Technical Report, 2019. Prajit Ramachandran, Niki Parmar, Ashish Vaswani, Irwan Bello, Anselm Levskaya, and Jon Shlens.

<!-- p11-b022 | type=reference | col=0 | bbox=108.0,661.6,504.0,691.0 -->
Stand-alone self-attention in vision models. In NeurIPS, 2019. Chen Sun, Abhinav Shrivastava, Saurabh Singh, and Abhinav Gupta. Revisiting unreasonable ef-

<!-- p11-b023 | type=reference | col=0 | bbox=108.0,691.9,504.0,721.3 -->
fectiveness of data in deep learning era. In ICCV, 2017. Chen Sun, Austin Myers, Carl Vondrick, Kevin Murphy, and Cordelia Schmid. Videobert: A joint

<!-- p11-b024 | type=reference | col=0 | bbox=118.0,722.1,398.0,732.3 -->
model for video and language representation learning. In ICCV, 2019.


<!-- ===== page 12 | columns=1 | gutters=[] -->
<!-- p12-b000 | type=reference | col=0 | bbox=108.0,84.3,504.0,94.2 -->
Hugo Touvron, Andrea Vedaldi, Matthijs Douze, and Herve Jegou. Fixing the train-test resolution

<!-- p12-b001 | type=reference | col=0 | bbox=108.0,95.0,504.0,124.1 -->
discrepancy. In NeurIPS. 2019. Hugo Touvron, Andrea Vedaldi, Matthijs Douze, and Herve Jegou. Fixing the train-test resolution

<!-- p12-b002 | type=reference | col=0 | bbox=108.0,124.9,504.0,154.0 -->
discrepancy: Fixefﬁcientnet. arXiv preprint arXiv:2003.08237, 2020. Michael Tschannen, Josip Djolonga, Marvin Ritter, Aravindh Mahendran, Neil Houlsby, Sylvain

<!-- p12-b003 | type=reference | col=0 | bbox=118.0,154.8,504.0,186.9 -->
Gelly, and Mario Lucic. Self-supervised learning of video-induced visual invariances. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), June 2020.

<!-- p12-b004 | type=reference | col=0 | bbox=108.0,195.8,504.0,205.8 -->
Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N Gomez,

<!-- p12-b005 | type=reference | col=0 | bbox=108.0,206.6,504.0,235.7 -->
Łukasz Kaiser, and Illia Polosukhin. Attention is all you need. In NIPS, 2017. Huiyu Wang, Yukun Zhu, Bradley Green, Hartwig Adam, Alan Yuille, and Liang-Chieh Chen.

<!-- p12-b006 | type=reference | col=0 | bbox=108.0,236.5,504.0,265.6 -->
Axial-deeplab: Stand-alone axial-attention for panoptic segmentation. In ECCV, 2020a. Huiyu Wang, Yukun Zhu, Bradley Green, Hartwig Adam, Alan Yuille, and Liang-Chieh

<!-- p12-b007 | type=reference | col=0 | bbox=118.0,266.4,504.0,287.5 -->
Chen. Axial-deeplab: Stand-alone axial-attention for panoptic segmentation. arXiv preprint arXiv:2003.07853, 2020b.

<!-- p12-b008 | type=reference | col=0 | bbox=108.0,296.5,504.0,306.4 -->
Qiang Wang, Bei Li, Tong Xiao, Jingbo Zhu, Changliang Li, Derek F. Wong, and Lidia S. Chao.

<!-- p12-b009 | type=reference | col=0 | bbox=108.0,307.3,504.0,336.3 -->
Learning deep transformer models for machine translation. In ACL, 2019. Xiaolong Wang, Ross Girshick, Abhinav Gupta, and Kaiming He. Non-local neural networks. In

<!-- p12-b010 | type=reference | col=0 | bbox=108.0,337.1,504.0,366.2 -->
CVPR, 2018. Dirk Weissenborn, Oscar T¨ackstr¨om, and Jakob Uszkoreit. Scaling autoregressive video models. In

<!-- p12-b011 | type=reference | col=0 | bbox=108.0,367.0,504.0,396.1 -->
ICLR, 2019. Bichen Wu, Chenfeng Xu, Xiaoliang Dai, Alvin Wan, Peizhao Zhang, Masayoshi Tomizuka, Kurt

<!-- p12-b012 | type=reference | col=0 | bbox=118.0,397.1,504.0,418.0 -->
Keutzer, and Peter Vajda. Visual transformers: Token-based image representation and processing for computer vision. arxiv, 2020.

<!-- p12-b013 | type=reference | col=0 | bbox=108.0,426.8,504.0,455.9 -->
Yuxin Wu and Kaiming He. Group normalization. In ECCV, 2018. Qizhe Xie, Minh-Thang Luong, Eduard Hovy, and Quoc V. Le. Self-training with noisy student

<!-- p12-b014 | type=reference | col=0 | bbox=118.0,456.7,317.4,466.8 -->
improves imagenet classiﬁcation. In CVPR, 2020.

<!-- p12-b015 | type=reference | col=0 | bbox=108.0,474.3,504.0,485.8 -->
Xiaohua Zhai, Avital Oliver, Alexander Kolesnikov, and Lucas Beyer. S4L: Self-Supervised Semi-

<!-- p12-b016 | type=reference | col=0 | bbox=108.0,486.6,504.0,515.6 -->
Supervised Learning. In ICCV, 2019a. Xiaohua Zhai, Joan Puigcerver, Alexander Kolesnikov, Pierre Ruyssen, Carlos Riquelme, Mario

<!-- p12-b017 | type=reference | col=0 | bbox=118.0,516.6,504.0,548.5 -->
Lucic, Josip Djolonga, Andre Susano Pinto, Maxim Neumann, Alexey Dosovitskiy, et al. A large-scale study of representation learning with the visual task adaptation benchmark. arXiv preprint arXiv:1910.04867, 2019b.

<!-- p12-b018 | type=reference | col=0 | bbox=108.0,557.5,504.0,567.5 -->
Hengshuang Zhao, Jiaya Jia, and Vladlen Koltun. Exploring self-attention for image recognition. In

<!-- p12-b019 | type=reference | col=0 | bbox=118.0,568.3,170.3,578.4 -->
CVPR, 2020.


<!-- ===== page 13 | columns=2 | gutters=[[349.0, 358.0]] -->
<!-- p13-b000 | type=table | col=-1 | bbox=121.4,86.3,490.6,237.8 -->
[table T3]
Models | Dataset | Epochs | Base LR | LR decay | Weight decay | Dropout
ViT-B/{16,32} | JFT-300M | 7 | 10−4 8 · | linear | 0.1 | 0.0
ViT-L/32 | JFT-300M | 7 | 6 · 10−4 | linear | 0.1 | 0.0
ViT-L/16 | JFT-300M | 7/14 | 10−4 4 · | linear | 0.1 | 0.0
ViT-H/14 | JFT-300M | 14 | 3 · 10−4 | linear | 0.1 | 0.0
R50x{1,2} | JFT-300M | 7 | 10−3 | linear | 0.1 | 0.0
R101x1 | JFT-300M | 7 | 8 · 10−4 | linear | 0.1 | 0.0
R152x{1,2} | JFT-300M | 7 | 10−4 6 · | linear | 0.1 | 0.0
R50+ViT-B/{16,32} | JFT-300M | 7 | · 10−4 8 | linear | 0.1 | 0.0
R50+ViT-L/32 | JFT-300M | 7 | 2 · 10−4 | linear | 0.1 | 0.0
R50+ViT-L/16 | JFT-300M | 7/14 | 10−4 4 · | linear | 0.1 | 0.0
ViT-B/{16,32} | ImageNet-21k | 90 | 10−3 | linear | 0.03 | 0.1
ViT-L/{16,32} | ImageNet-21k | 30/90 | 10−3 | linear | 0.03 | 0.1
ViT-∗ | ImageNet | 300 | 3 · 10−3 | cosine | 0.3 | 0.1

<!-- p13-b001 | type=caption | col=-1 | bbox=108.0,251.6,504.0,272.5 -->
Table 3: Hyperparameters for training. All models are trained with a batch size of 4096 and learning rate warmup of 10k steps. For ImageNet we found it beneﬁcial to additionally apply gradient

<!-- p13-b002 | type=body | col=0 | bbox=108.0,273.5,319.7,283.4 -->
clipping at global norm 1. Training resolution is 224.

<!-- p13-b003 | type=heading | col=0 | bbox=108.3,303.5,161.4,315.4 -->
## APPENDIX

<!-- p13-b004 | type=heading | col=0 | bbox=108.3,330.0,284.3,342.0 -->
### A MULTIHEAD SELF-ATTENTION

<!-- p13-b005 | type=body | col=-1 | bbox=108.0,354.8,504.0,399.0 -->
Standard qkv self-attention (SA, Vaswani et al. (2017)) is a popular building block for neural architectures. For each element in an input sequence z ∈RN×D, we compute a weighted sum over all values v in the sequence. The attention weights Aij are based on the pairwise similarity between two elements of the sequence and their respective query qi and key kj representations.

<!-- p13-b006 | type=body | col=0 | bbox=168.8,407.1,241.0,417.9 -->
[q, k, v] = zUqkv

<!-- p13-b007 | type=body | col=0 | bbox=250.8,422.0,256.7,431.9 -->


<!-- p13-b008 | type=body | col=0 | bbox=303.9,422.0,309.9,431.9 -->


<!-- p13-b009 | type=body | col=0 | bbox=280.6,423.9,290.5,433.8 -->
p

<!-- p13-b010 | type=body | col=0 | bbox=256.8,424.0,280.5,435.8 -->
qk⊤/

<!-- p13-b011 | type=body | col=0 | bbox=194.0,425.9,249.1,435.8 -->
A = softmax

<!-- p13-b012 | type=body | col=0 | bbox=290.5,425.9,303.4,436.7 -->
Dh

<!-- p13-b013 | type=body | col=0 | bbox=175.6,444.0,232.9,454.0 -->
SA(z) = Av .

<!-- p13-b014 | type=formula | col=1 | bbox=370.7,405.0,443.2,418.5 -->
$$ Uqkv ∈RD×3Dh, $$

<!-- p13-b015 | type=body | col=1 | bbox=492.4,407.4,504.0,417.3 -->
(5)

<!-- p13-b016 | type=formula | col=1 | bbox=385.0,423.7,435.5,435.8 -->
$$ A ∈RN×N, $$

<!-- p13-b017 | type=body | col=1 | bbox=492.4,426.1,504.0,454.2 -->
(6) (7)

<!-- p13-b018 | type=body | col=-1 | bbox=108.0,467.2,504.0,500.9 -->
Multihead self-attention (MSA) is an extension of SA in which we run k self-attention operations, called “heads”, in parallel, and project their concatenated outputs. To keep compute and number of parameters constant when changing k, Dh (Eq. 5) is typically set to D/k.

<!-- p13-b019 | type=body | col=0 | bbox=148.4,507.8,347.4,518.7 -->
MSA(z) = [SA1(z); SA2(z); · · · ; SAk(z)] Umsa

<!-- p13-b020 | type=heading | col=0 | bbox=108.3,535.4,242.2,547.3 -->
### B EXPERIMENT DETAILS

<!-- p13-b021 | type=body | col=0 | bbox=108.2,560.4,177.0,570.4 -->
B.1 TRAINING

<!-- p13-b022 | type=formula | col=1 | bbox=388.4,505.7,462.8,519.2 -->
$$ Umsa ∈Rk·Dh×D $$

<!-- p13-b023 | type=body | col=1 | bbox=492.4,508.1,504.0,518.1 -->
(8)

<!-- p13-b024 | type=caption | col=-1 | bbox=108.0,581.0,504.0,623.8 -->
Table 3 summarizes our training setups for our different models. We found strong regularization to be key when training models from scratch on ImageNet. Dropout, when used, is applied after every dense layer except for the the qkv-projections and directly after adding positional- to patch embeddings. Hybrid models are trained with the exact setup as their ViT counterparts. Finally, all

<!-- p13-b025 | type=body | col=0 | bbox=108.0,624.8,244.7,658.3 -->
training is done on resolution 224. B.1.1 FINE-TUNING

<!-- p13-b026 | type=body | col=-1 | bbox=108.0,667.5,504.0,732.3 -->
We ﬁne-tune all ViT models using SGD with a momentum of 0.9. We run a small grid search over learning rates, see learning rate ranges in Table 4. To do so, we use small sub-splits from the training set (10% for Pets and Flowers, 2% for CIFAR, 1% ImageNet) as development set and train on the remaining data. For ﬁnal results we train on the entire training set and evaluate on the respective test data. For ﬁne-tuning ResNets and hybrid models we use the exact same setup, with the only exception of ImageNet where we add another value 0.06 to the learning rate sweep. Additionally,


<!-- ===== page 14 | columns=2 | gutters=[[273.0, 282.0]] -->
<!-- p14-b000 | type=table | col=-1 | bbox=198.3,86.4,413.7,158.8 -->
[table T4]
Dataset | Steps | Base LR
ImageNet
CIFAR100
CIFAR10
Oxford-IIIT Pets
Oxford Flowers-102
VTAB (19 tasks) | 20 000
10 000
10 000
500
500
2 500 | {0.003, 0.06} 0.01, 0.03,
{0.001, 0.003, 0.01, 0.03}
{0.001, 0.003, 0.01, 0.03}
{0.001, 0.003, 0.01, 0.03}
{0.001, 0.003, 0.01, 0.03}
0.01

<!-- p14-b001 | type=caption | col=-1 | bbox=108.0,172.9,504.0,193.8 -->
Table 4: Hyperparameters for ﬁne-tuning. All models are ﬁne-tuned with cosine learning rate decay, a batch size of 512, no weight decay, and grad clipping at global norm 1. If not mentioned otherwise,

<!-- p14-b002 | type=body | col=0 | bbox=108.0,194.8,223.1,204.8 -->
ﬁne-tuning resolution is 384.

<!-- p14-b003 | type=body | col=-1 | bbox=108.0,230.2,504.0,262.1 -->
for ResNets we also run the setup of Kolesnikov et al. (2020) and select the best results across this run and our sweep. Finally, if not mentioned otherwise, all ﬁne-tuning experiments run at 384 resolution (running ﬁne-tuning at different resolution than training is common practice (Kolesnikov

<!-- p14-b004 | type=body | col=0 | bbox=108.0,263.1,161.4,273.0 -->
et al., 2020)).

<!-- p14-b005 | type=body | col=-1 | bbox=108.0,280.0,504.0,383.6 -->
When transferring ViT models to another dataset, we remove the whole head (two linear layers) and replace it by a single, zero-initialized linear layer outputting the number of classes required by the target dataset. We found this to be a little more robust than simply re-initializing the very last layer. For VTAB we follow the protocol in Kolesnikov et al. (2020), and use the same hyperparameter setting for all tasks. We use a learning rate of 0.01 and train for 2500 steps (Tab. 4). We chose this setting by running a small sweep over two learning rates and two schedules, and selecting the setting with the highest VTAB score on the 200-example validation sets. We follow the pre-processing used in Kolesnikov et al. (2020), except that we do not use task-speciﬁc input resolutions. Instead we ﬁnd that Vision Transformer beneﬁts most from a high resolution (384 × 384) for all tasks.

<!-- p14-b006 | type=body | col=0 | bbox=108.2,401.0,223.9,411.0 -->
B.1.2 SELF-SUPERVISION

<!-- p14-b007 | type=body | col=-1 | bbox=108.0,421.5,504.0,475.5 -->
We employ the masked patch prediction objective for preliminary self-supervision experiments. To do so we corrupt 50% of patch embeddings by either replacing their embeddings with a learnable [mask] embedding (80%), a random other patch embedding (10%) or just keeping them as is (10%). This setup is very similar to the one used for language by Devlin et al. (2019). Finally, we predict the 3-bit, mean color (i.e., 512 colors in total) of every corrupted patch using their respective

<!-- p14-b008 | type=body | col=0 | bbox=108.0,476.5,194.9,486.4 -->
patch representations.

<!-- p14-b009 | type=body | col=-1 | bbox=108.0,493.4,504.0,591.1 -->
We trained our self-supervised model for 1M steps (ca. 14 epochs) with batch size 4096 on JFT. We use Adam, with a base learning rate of 2·10−4, warmup of 10k steps and cosine learning rate decay. As prediction targets for pretraining we tried the following settings: 1) predicting only the mean, 3bit color (i.e., 1 prediction of 512 colors), 2) predicting a 4 × 4 downsized version of the 16 × 16 patch with 3bit colors in parallel (i.e., 16 predictions of 512 colors), 3) regression on the full patch using L2 (i.e., 256 regressions on the 3 RGB channels). Surprisingly, we found that all worked quite well, though L2 was slightly worse. We report ﬁnal results only for option 1) because it has shown best few-shot performance. We also experimented with 15% corruption rate as used by Devlin et al. (2019) but results were also slightly worse on our few-shot metrics.

<!-- p14-b010 | type=body | col=-1 | bbox=108.0,598.0,504.0,640.9 -->
Lastly, we would like to remark that our instantiation of masked patch prediction doesn’t require such an enormous amount of pretraining nor a large dataset such as JFT in order to lead to similar performance gains on ImageNet classiﬁcation. That is, we observed diminishing returns on downstream performance after 100k pretraining steps, and see similar gains when pretraining on

<!-- p14-b011 | type=body | col=0 | bbox=108.0,641.9,149.8,651.8 -->
ImageNet.

<!-- p14-b012 | type=heading | col=0 | bbox=108.3,673.0,244.3,684.9 -->
### C ADDITIONAL RESULTS

<!-- p14-b013 | type=body | col=-1 | bbox=108.0,700.4,504.0,732.3 -->
We report detailed results corresponding to the ﬁgures presented in the paper. Table 5 corresponds to Figure 3 from the paper and shows transfer performance of different ViT models pre-trained on datasets of increasing size: ImageNet, ImageNet-21k, and JFT-300M. Table 6 corresponds to


<!-- ===== page 15 | columns=2 | gutters=[[312.0, 363.0]] -->
<!-- p15-b000 | type=table | col=-1 | bbox=116.2,86.2,498.3,297.6 -->
[table T5]
 |  | ViT-B/16 | ViT-B/32 | ViT-L/16 | ViT-L/32 | ViT-H/14
ImageNet | CIFAR-10 | 98.13 | 97.77 | 97.86 | 97.94 | -
 | CIFAR-100 | 87.13 | 86.31 | 86.35 | 87.07 | -
 | ImageNet | 77.91 | 73.38 | 76.53 | 71.16 | -
 | ImageNet ReaL | 83.57 | 79.56 | 82.19 | 77.83 | -
 | Oxford Flowers-102 | 89.49 | 85.43 | 89.66 | 86.36 | -
 | Oxford-IIIT-Pets | 93.81 | 92.04 | 93.64 | 91.35 | -
ImageNet-21k | CIFAR-10
CIFAR-100
ImageNet
ImageNet ReaL
Oxford Flowers-102
Oxford-IIIT-Pets | 98.95
91.67
83.97
88.35
99.38
94.43 | 98.79
91.97
81.28
86.63
99.11
93.02 | 99.16
93.44
85.15
88.40
99.61
94.73 | 99.13
93.04
80.99
85.65
99.19
93.09 | 99.27
93.82
85.13
88.70
99.51
94.82
JFT-300M | CIFAR-10
CIFAR-100
ImageNet
ImageNet ReaL
Oxford Flowers-102
Oxford-IIIT-Pets | 99.00
91.87
84.15
88.85
99.56
95.80 | 98.61
90.49
80.73
86.27
99.27
93.40 | 99.38
94.04
87.12
89.99
99.56
97.11 | 99.19
92.52
84.37
88.28
99.45
95.83 | 99.50
94.55
88.04
90.33
99.68
97.56

<!-- p15-b001 | type=caption | col=-1 | bbox=108.0,313.2,504.0,356.0 -->
Table 5: Top1 accuracy (in %) of Vision Transformer on various datasets when pre-trained on ImageNet, ImageNet-21k or JFT300M. These values correspond to Figure 3 in the main text. Models are ﬁne-tuned at 384 resolution. Note that the ImageNet results are computed without additional techniques (Polyak averaging and 512 resolution images) used to achieve results in Table 2.

<!-- p15-b002 | type=table | col=-1 | bbox=114.7,372.5,497.3,555.2 -->
[table T6]
name | Epochs | ImageNet | ImageNet ReaL | CIFAR-10 | CIFAR-100 | Pets | Flowers | exaFLOPs
ViT-B/32
ViT-B/16
ViT-L/32
ViT-L/16
ViT-L/16
ViT-H/14 | 7
7
7
7
14
14 | 80.73
84.15
84.37
86.30
87.12
88.08 | 86.27
88.85
88.28
89.43
89.99
90.36 | 98.61
99.00
99.19
99.38
99.38
99.50 | 90.49
91.87
92.52
93.46
94.04
94.71 | 93.40
95.80
95.83
96.81
97.11
97.11 | 99.27
99.56
99.45
99.66
99.56
99.71 | 55
224
196
783
1567
4262
ResNet50x1
ResNet50x2
ResNet101x1
ResNet152x1
ResNet152x2
ResNet152x2
ResNet200x3 | 7
7
7
7
7
14
14 | 77.54
82.12
80.67
81.88
84.97
85.56
87.22 | 84.56
87.94
87.07
87.96
89.69
89.89
90.15 | 97.67
98.29
98.48
98.82
99.06
99.24
99.34 | 86.07
89.20
89.17
90.22
92.05
91.92
93.53 | 91.11
93.43
94.08
94.17
95.37
95.75
96.32 | 94.26
97.02
95.95
96.94
98.62
98.75
99.04 | 50
199
96
141
563
1126
3306
R50x1+ViT-B/32
R50x1+ViT-B/16
R50x1+ViT-L/32
R50x1+ViT-L/16
R50x1+ViT-L/16 | 7
7
7
7
14 | 84.90
85.58
85.68
86.60
87.12 | 89.15
89.65
89.04
89.72
89.76 | 99.01
99.14
99.24
99.18
99.31 | 92.24
92.63
92.93
93.64
93.89 | 95.75
96.65
96.97
97.03
97.36 | 99.46
99.40
99.43
99.40
99.11 | 106
274
246
859
1668

<!-- p15-b003 | type=caption | col=-1 | bbox=108.0,569.9,504.0,590.8 -->
Table 6: Detailed results of model scaling experiments. These correspond to Figure 5 in the main paper. We show transfer accuracy on several datasets, as well as the pre-training compute (in ex-

<!-- p15-b004 | type=body | col=0 | bbox=108.0,591.8,146.5,601.8 -->
aFLOPs).

<!-- p15-b005 | type=caption | col=-1 | bbox=108.0,624.6,504.0,645.5 -->
Figure 5 from the paper and shows the transfer performance of ViT, ResNet, and hybrid models of varying size, as well as the estimated computational cost of their pre-training.

<!-- p15-b006 | type=heading | col=0 | bbox=108.3,664.3,253.8,676.3 -->
### D ADDITIONAL ANALYSES

<!-- p15-b007 | type=heading | col=0 | bbox=108.2,690.3,265.2,700.2 -->
#### D.1 SGD VS. ADAM FOR RESNETS

<!-- p15-b008 | type=body | col=-1 | bbox=108.0,711.4,504.0,732.3 -->
ResNets are typically trained with SGD and our use of Adam as optimizer is quite unconventional. Here we show the experiments that motivated this choice. Namely, we compare the ﬁne-tuning


<!-- ===== page 16 | columns=1 | gutters=[] -->
<!-- p16-b000 | type=table | col=-1 | bbox=202.6,86.2,409.4,169.1 -->
[table T7]
Dataset | ResNet50
Adam SGD | ResNet152x2
Adam SGD
ImageNet
CIFAR10
CIFAR100
Oxford-IIIT Pets
Oxford Flowers-102
Average | 77.54 78.24
97.67 97.46
86.07 85.17
91.11 91.00
94.26 92.06
89.33 88.79 | 84.97 84.37
99.06 99.07
92.05 91.06
95.37 94.79
98.62 99.32
94.01 93.72

<!-- p16-b001 | type=body | col=0 | bbox=166.1,160.4,445.9,192.8 -->
Average Table 7: Fine-tuning ResNet models pre-trained with Adam and SGD.

<!-- p16-b003 | type=figure | col=-1 | bbox=108.0,206.4,450.7,358.6 -->
![Figure 8: Scaling different model dimensions of the Vision Transformer.](figures/F8.png)

<!-- p16-b033 | type=caption | col=0 | bbox=161.3,348.6,450.7,358.6 -->
Figure 8: Scaling different model dimensions of the Vision Transformer.

<!-- p16-b034 | type=body | col=0 | bbox=108.0,381.5,504.0,446.3 -->
performance of two ResNets – 50x1 and 152x2 – pre-trained on JFT with SGD and Adam. For SGD, we use the hyperparameters recommended by Kolesnikov et al. (2020). Results are presented in Table 7. Adam pre-training outperforms SGD pre-training on most datasets and on average. This justiﬁes the choice of Adam as the optimizer used to pre-train ResNets on JFT. Note that the absolute numbers are lower than those reported by Kolesnikov et al. (2020), since we pre-train only for 7 epochs, not 30.

<!-- p16-b035 | type=body | col=0 | bbox=108.0,462.3,504.0,602.7 -->
D.2 TRANSFORMER SHAPE We ran ablations on scaling different dimensions of the Transformer architecture to ﬁnd out which are best suited for scaling to very large models. Figure 8 shows 5-shot performance on ImageNet for different conﬁgurations. All conﬁgurations are based on a ViT model with 8 layers, D = 1024, DMLP = 2048 and a patch size of 32, the intersection of all lines. We can see that scaling the depth results in the biggest improvements which are clearly visible up until 64 layers. However, diminishing returns are already visible after 16 layers. Interestingly, scaling the width of the network seems to result in the smallest changes. Decreasing the patch size and thus increasing the effective sequence length shows surprisingly robust improvements without introducing parameters. These ﬁndings suggest that compute might be a better predictor of performance than the number of parameters, and that scaling should emphasize depth over width if any. Overall, we ﬁnd that scaling all dimensions proportionally results in robust improvements.

<!-- p16-b036 | type=body | col=0 | bbox=108.0,618.7,504.0,682.5 -->
D.3 HEAD TYPE AND CLASS TOKEN In order to stay as close as possible to the original Transformer model, we made use of an additional [class] token, which is taken as image representation. The output of this token is then transformed into a class prediction via a small multi-layer perceptron (MLP) with tanh as non-linearity in the single hidden layer.

<!-- p16-b037 | type=body | col=0 | bbox=108.0,689.4,504.0,732.3 -->
This design is inherited from the Transformer model for text, and we use it throughout the main paper. An initial attempt at using only image-patch embeddings, globally average-pooling (GAP) them, followed by a linear classiﬁer—just like ResNet’s ﬁnal feature map—performed very poorly. However, we found that this is neither due to the extra token, nor to the GAP operation. Instead,


<!-- ===== page 17 | columns=1 | gutters=[] -->
<!-- p17-b000 | type=footnote | col=0 | bbox=179.1,83.0,185.4,92.2 -->
60

<!-- p17-b001 | type=formula | col=0 | bbox=211.9,90.9,264.2,109.1 -->
$$ CLS-Token, lr=8e-4 GAP, lr=8e-4 $$

<!-- p17-b003 | type=footnote | col=0 | bbox=179.1,100.4,185.4,109.7 -->
55

<!-- p17-b004 | type=formula | col=0 | bbox=211.9,108.8,247.0,118.0 -->
$$ GAP, lr=3e-4 $$

<!-- p17-b005 | type=footnote | col=0 | bbox=179.1,117.9,185.4,214.6 -->
50 45 40 35 30 25

<!-- p17-b006 | type=footnote | col=0 | bbox=187.0,210.6,190.1,219.9 -->
0

<!-- p17-b007 | type=footnote | col=0 | bbox=222.9,210.6,226.0,219.9 -->
1

<!-- p17-b008 | type=footnote | col=0 | bbox=258.8,210.6,261.9,219.9 -->
2

<!-- p17-b009 | type=footnote | col=0 | bbox=294.6,210.6,297.8,219.9 -->
3

<!-- p17-b010 | type=footnote | col=0 | bbox=330.5,210.6,333.7,219.9 -->
4

<!-- p17-b011 | type=footnote | col=0 | bbox=366.4,210.6,369.6,219.9 -->
5

<!-- p17-b012 | type=footnote | col=0 | bbox=402.3,210.6,405.5,219.9 -->
6

<!-- p17-b013 | type=footnote | col=0 | bbox=438.2,210.6,441.4,219.9 -->
7

<!-- p17-b014 | type=footnote | col=0 | bbox=287.6,217.8,340.8,228.4 -->
Epochs of training

<!-- p17-b015 | type=caption | col=0 | bbox=108.0,248.3,504.0,269.2 -->
Figure 9: Comparison of class-token and global average pooling classiﬁers. Both work similarly well, but require different learning-rates.

<!-- p17-b016 | type=table | col=-1 | bbox=166.6,285.9,445.4,341.7 -->
[table T8]
Pos. Emb. | Default/Stem | Every Layer | Every Layer-Shared
No Pos. Emb.
1-D Pos. Emb.
2-D Pos. Emb.
Rel. Pos. Emb. | 0.61382
0.64206
0.64001
0.64032 | N/A
0.63964
0.64046
N/A | N/A
0.64292
0.64022
N/A

<!-- p17-b017 | type=body | col=0 | bbox=108.0,334.0,504.0,378.5 -->
N/A Table 8: Results of the ablation study on positional embeddings with ViT-B/16 model evaluated on ImageNet 5-shot linear.

<!-- p17-b018 | type=body | col=0 | bbox=108.0,401.0,504.0,422.0 -->
the difference in performance is fully explained by the requirement for a different learning-rate, see Figure 9.

<!-- p17-b019 | type=body | col=0 | bbox=108.0,437.6,504.0,479.2 -->
D.4 POSITIONAL EMBEDDING We ran ablations on different ways of encoding spatial information using positional embedding. We tried the following cases:

<!-- p17-b020 | type=body | col=0 | bbox=135.4,490.3,504.0,526.8 -->
• Providing no positional information: Considering the inputs as a bag of patches. • 1-dimensional positional embedding: Considering the inputs as a sequence of patches in the raster order (default across all other experiments in this paper).

<!-- p17-b021 | type=body | col=0 | bbox=135.4,532.3,504.0,586.1 -->
• 2-dimensional positional embedding: Considering the inputs as a grid of patches in two dimensions. In this case, two sets of embeddings are learned, each for one of the axes, X-embedding, and Y -embedding, each with size D/2. Then, based on the coordinate on the path in the input, we concatenate the X and Y embedding to get the ﬁnal positional embedding for that patch.

<!-- p17-b022 | type=body | col=0 | bbox=135.4,591.5,504.0,689.2 -->
• Relative positional embeddings: Considering the relative distance between patches to encode the spatial information as instead of their absolute position. To do so, we use 1dimensional Relative Attention, in which we deﬁne the relative distance all possible pairs of patches. Thus, for every given pair (one as query, and the other as key/value in the attention mechanism), we have an offset pq −pk, where each offset is associated with an embedding. Then, we simply run extra attention, where we use the original query (the content of query), but use relative positional embeddings as keys. We then use the logits from the relative attention as a bias term and add it to the logits of the main attention (content-based attention) before applying the softmax.

<!-- p17-b023 | type=body | col=0 | bbox=108.0,700.4,504.0,732.3 -->
In addition to different ways of encoding spatial information, we also tried different ways of incorporating this information in our model. For the 1-dimensional and 2-dimensional positional embeddings, we tried three different cases: (1) add positional embeddings to the inputs right after


<!-- ===== page 18 | columns=2 | gutters=[[341.0, 368.0]] -->
<!-- p18-b000 | type=figure | col=-1 | bbox=108.0,81.9,504.0,234.8 -->
![Figure 10: Position embeddings of models trained with different hyperparameters.](figures/F9.png)

<!-- p18-b047 | type=caption | col=-1 | bbox=142.0,224.8,470.0,234.8 -->
Figure 10: Position embeddings of models trained with different hyperparameters.

<!-- p18-b048 | type=body | col=-1 | bbox=108.0,257.2,504.0,289.1 -->
the stem of them model and before feeding the inputs to the Transformer encoder (default across all other experiments in this paper); (2) learn and add positional embeddings to the inputs at the beginning of each layer; (3) add a learned positional embeddings to the inputs at the beginning of

<!-- p18-b049 | type=body | col=0 | bbox=108.0,290.1,248.2,300.1 -->
each layer (shared between layers).

<!-- p18-b050 | type=body | col=-1 | bbox=108.0,307.0,504.0,404.7 -->
Table 8 summarizes the results from this ablation study on a ViT-B/16 model. As we can see, while there is a large gap between the performances of the model with no positional embedding and models with positional embedding, there is little to no difference between different ways of encoding positional information. We speculate that since our Transformer encoder operates on patch-level inputs, as opposed to pixel-level, the differences in how to encode spatial information is less important. More precisely, in patch-level inputs, the spatial dimensions are much smaller than the original pixel-level inputs, e.g., 14 × 14 as opposed to 224 × 224, and learning to represent the spatial relations in this resolution is equally easy for these different positional encoding strategies. Even so, the speciﬁc pattern of position embedding similarity learned by the network depends on the training

<!-- p18-b051 | type=body | col=0 | bbox=108.0,405.7,224.4,415.6 -->
hyperparameters (Figure 10).

<!-- p18-b052 | type=figure | col=-1 | bbox=108.0,427.7,504.0,657.9 -->
![Figure 11: Size of attended area by head and network depth. Attention distance was computed for 128 example images by averaging the distance between the query pixel and all other pixels, weighted by the attention weight. Each dot shows the mean attention distance across images for one of 16](figures/F10.png)

<!-- p18-b071 | type=formula | col=1 | bbox=369.9,428.5,427.0,439.6 -->
$$ R50x1 + ViT-L/16 $$

<!-- p18-b085 | type=caption | col=-1 | bbox=108.0,626.0,504.0,657.9 -->
Figure 11: Size of attended area by head and network depth. Attention distance was computed for 128 example images by averaging the distance between the query pixel and all other pixels, weighted by the attention weight. Each dot shows the mean attention distance across images for one of 16

<!-- p18-b086 | type=body | col=0 | bbox=108.0,658.9,290.0,668.9 -->
heads at one layer. Image width is 224 pixels.

<!-- p18-b087 | type=body | col=0 | bbox=108.2,690.7,290.5,700.6 -->
D.5 EMPIRICAL COMPUTATIONAL COSTS

<!-- p18-b088 | type=body | col=-1 | bbox=108.0,711.4,504.0,732.3 -->
We are also interested in real-world speed of the architectures on our hardware, which is not always well predicted by theoretical FLOPs due to details like lane widths and cache sizes. For this purpose,


<!-- ===== page 19 | columns=3 | gutters=[[311.0, 317.0], [358.0, 377.0]] -->
<!-- p19-b000 | type=body | col=-1 | bbox=108.0,84.3,504.0,105.2 -->
we perform timing of inference speed for the main models of interest, on a TPUv3 accelerator; the difference between inference and backprop speed is a constant model-independent factor.

<!-- p19-b001 | type=caption | col=-1 | bbox=108.0,112.2,504.0,144.1 -->
Figure 12 (left) shows how many images one core can handle per second, across various input sizes. Every single point refers to the peak performance measured across a wide range of batch-sizes. As can be seen, the theoretical bi-quadratic scaling of ViT with image size only barely starts happening

<!-- p19-b002 | type=body | col=0 | bbox=108.0,145.0,296.4,155.0 -->
for the largest models at the largest resolutions.

<!-- p19-b003 | type=caption | col=-1 | bbox=108.0,162.0,504.0,193.9 -->
Figure 12 (right) shows this quantity for the same set of models. This shows that large ViT models have a clear advantage in terms of memory-efﬁciency over ResNet

<!-- p19-b004 | type=figure | col=-1 | bbox=108.0,162.0,504.0,377.8 -->
![Figure 12 (right) shows this quantity for the same set of models. This shows that large ViT models have a clear advantage in terms of memory-efﬁciency over ResNet](figures/F11.png)

<!-- p19-b006 | type=figure | col=-1 | bbox=108.0,215.5,504.0,417.0 -->
![Figure 12: Left: Real wall-clock timings of various architectures across input sizes. ViT models have speed comparable to similar ResNets. Right: Largest per-core batch-size ﬁtting on device with](figures/F12.png)

<!-- p19-b013 | type=formula | col=1 | bbox=330.1,224.2,357.1,244.2 -->
$$ ViT-B/16 ViT-L/16 $$

<!-- p19-b030 | type=caption | col=-1 | bbox=108.0,396.0,504.0,417.0 -->
Figure 12: Left: Real wall-clock timings of various architectures across input sizes. ViT models have speed comparable to similar ResNets. Right: Largest per-core batch-size ﬁtting on device with

<!-- p19-b031 | type=body | col=-1 | bbox=108.0,418.0,456.1,428.0 -->
various architectures across input sizes. ViT models are clearly more memory-efﬁcient.

<!-- p19-b032 | type=body | col=0 | bbox=108.2,453.2,215.1,463.1 -->
D.6 AXIAL ATTENTION

<!-- p19-b033 | type=body | col=-1 | bbox=108.0,474.1,504.0,560.8 -->
Axial Attention (Huang et al., 2020; Ho et al., 2019) is a simple, yet effective technique to run selfattention on large inputs that are organized as multidimensional tensors. The general idea of axial attention is to perform multiple attention operations, each along a single axis of the input tensor, instead of applying 1-dimensional attention to the ﬂattened version of the input. In axial attention, each attention mixes information along a particular axis, while keeping information along the other axes independent. Along this line, Wang et al. (2020b) proposed the AxialResNet model in which all the convolutions with kernel size 3 × 3 in a ResNet50 are replaced by axial self-attention, i.e. a row and column attention, augmented by relative positional encoding. We have implemented

<!-- p19-b034 | type=body | col=0 | bbox=108.0,560.5,248.7,571.8 -->
AxialResNet as a baseline model.3.

<!-- p19-b035 | type=body | col=-1 | bbox=108.0,578.8,504.0,610.6 -->
Moreover, we have modiﬁed ViT to process inputs in the 2-dimensional shape, instead of a 1dimensional sequence of patches, and incorporate Axial Transformer blocks, in which instead of a self-attention followed by an MLP, we have a a row-self-attention plus an MLP followed by a

<!-- p19-b036 | type=body | col=0 | bbox=108.0,611.6,249.1,621.6 -->
column-self-attention plus an MLP.

<!-- p19-b037 | type=body | col=-1 | bbox=108.0,628.6,504.0,671.4 -->
Figure 13, present the performance of Axial ResNet, Axial-ViT-B/32 and Axial-ViT-B/16 on ImageNet 5shot linear, when pretrained on JFT dataset, verses the pretraining compute, both in terms of number of FLOPs and inference time (example per seconds). As we can see, both Axial-ViT-B/32 and Axial-ViT-B/16 do better than their ViT-B counterpart in terms of performance, but it comes at

<!-- p19-b038 | type=body | col=-1 | bbox=108.0,681.7,504.0,722.1 -->
3Our implementation is based on the open-sourced PyTorch implementation in https://github.com/ csrhddlam/axial-deeplab. In our experiments, we reproduced the scores reported in (Wang et al., 2020b) in terms of accuracy, however, our implementation, similar to the open-source implementation, is very slow on TPUs. Therefore, we were not able to use it for extensive large-scale experiments. These may be

<!-- p19-b039 | type=body | col=0 | bbox=108.0,723.1,291.2,732.0 -->
unlocked by a carefully optimized implementation.


<!-- ===== page 20 | columns=2 | gutters=[[295.0, 376.0]] -->
<!-- p20-b000 | type=figure | col=-1 | bbox=108.0,81.9,504.0,260.6 -->
![Figure 13: Performance of Axial-Attention based models, in terms of top-1 accuracy on ImageNet](figures/F13.png)

<!-- p20-b032 | type=caption | col=-1 | bbox=108.0,250.7,504.0,260.6 -->
Figure 13: Performance of Axial-Attention based models, in terms of top-1 accuracy on ImageNet

<!-- p20-b033 | type=body | col=-1 | bbox=108.0,261.6,479.0,271.6 -->
5-shot linear, versus their speed in terms of number of FLOPs (left) and inference time (left).

<!-- p20-b034 | type=body | col=-1 | bbox=108.0,293.7,504.0,347.5 -->
the cost of more compute. This is because in Axial-ViT models, each Transformer block with global self-attention is replaced by two Axial Transformer blocks, one with row and one with column selfattention and although the sequence length that self-attention operates on is smaller in axial case, there is a extra MLP per Axial-ViT block. For the AxialResNet, although it looks reasonable in terms of accuracy/compute trade-off (Figure 13, left), the naive implementation is extremely slow

<!-- p20-b035 | type=body | col=0 | bbox=108.0,348.5,230.4,383.4 -->
on TPUs (Figure 13, right). D.7 ATTENTION DISTANCE

<!-- p20-b036 | type=body | col=-1 | bbox=108.0,394.0,504.0,458.8 -->
To understand how ViT uses self-attention to integrate information across the image, we analyzed the average distance spanned by attention weights at different layers (Figure 11). This “attention distance” is analogous to receptive ﬁeld size in CNNs. Average attention distance is highly variable across heads in lower layers, with some heads attending to much of the image, while others attend to small regions at or near the query location. As depth increases, attention distance increases for all heads. In the second half of the network, most heads attend widely across tokens.

<!-- p20-b037 | type=body | col=0 | bbox=108.2,473.8,211.8,483.8 -->
D.8 ATTENTION MAPS

<!-- p20-b038 | type=body | col=-1 | bbox=108.0,494.3,504.0,537.2 -->
To compute maps of the attention from the output token to the input space (Figures 6 and 14), we used Attention Rollout (Abnar & Zuidema, 2020). Brieﬂy, we averaged attention weights of ViT- L/16 across all heads and then recursively multiplied the weight matrices of all layers. This accounts for the mixing of attention across tokens through all layers.

<!-- p20-b039 | type=body | col=0 | bbox=108.2,552.2,227.0,562.2 -->
D.9 OBJECTNET RESULTS

<!-- p20-b040 | type=body | col=-1 | bbox=108.0,572.7,504.0,593.7 -->
We also evaluate our ﬂagship ViT-H/14 model on the ObjectNet benchmark following the evaluation setup in Kolesnikov et al. (2020), resulting in 82.1% top-5 accuracy and 61.7% top-1 accuracy.

<!-- p20-b041 | type=body | col=0 | bbox=108.2,608.7,227.3,618.7 -->
D.10 VTAB BREAKDOWN

<!-- p20-b042 | type=caption | col=-1 | bbox=108.0,629.2,366.1,639.2 -->
Table 9 shows the scores attained on each of the VTAB-1k tasks.


<!-- ===== page 21 | columns=2 | gutters=[[179.0, 409.0]] -->
<!-- p21-b000 | type=figure | col=-1 | bbox=108.0,134.7,504.0,677.3 -->
![Figure 14: Further example attention maps as in Figure 6 (random selection).](figures/F14.png)

<!-- p21-b129 | type=caption | col=-1 | bbox=152.2,667.4,459.8,677.3 -->
Figure 14: Further example attention maps as in Figure 6 (random selection).


<!-- ===== page 22 | columns=1 | gutters=[] -->
<!-- p22-b000 | type=caption | col=0 | bbox=183.5,362.4,425.4,372.4 -->
Table 9: Breakdown of VTAB-1k performance across tasks.

<!-- p22-b017 | type=body | col=0 | bbox=118.0,430.2,501.6,455.1 -->
ViT-H/14 (JFT) 95.3 85.5 75.2 99.7 97.2 65.0 88.9 83.3 96.7 91.4 76.6 91.7 63.8 53.1 79.4 63.3 84.5 33.2 51.2 77.6 ViT-L/16 (JFT) 95.4 81.9 74.3 99.7 96.7 63.5 87.4 83.6 96.5 89.7 77.1 86.4 63.1 49.7 74.5 60.5 82.2 36.2 51.1 76.3 ViT-L/16 (I21k) 90.8 84.1 74.1 99.3 92.7 61.0 80.9 82.5 95.6 85.2 75.3 70.3 56.1 41.9 74.7 64.9 79.9 30.5 41.7 72.7
