Attention Improves Sample Efficiency in Low-Resource Settings

Abstract. We study whether an attention mechanism improves sample efficiency when labeled data are scarce. Across 12 runs on three datasets, the attention mechanism reduced validation error by 18.4% (p<0.001) relative to a strong baseline [3]. The gain persists when only 5% of labels are available, although the effect is weaker for very small models [7].

We train all models for 40 epochs with a batch size of 64 and a learning rate of 0.001. The attention mechanism is applied to the encoder only. We do not tune the decoder, so the comparison isolates the encoder change. Results may not transfer to sequence-to-sequence tasks, where cross-attention interacts with the proposed change.
