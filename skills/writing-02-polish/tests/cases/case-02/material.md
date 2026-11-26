Attention Improves Sample Efficiency in Low-Resource Settings

Abstract. We study whether attention mechanism improves sample efficiency when labeled data are scarce. Across 12 runs on three datasets, the attention model may reduce validation error by 18.4% (p<0.001) relative to a strong baseline [3]. The gain persists when only 5% of the labels are available [7].

This pattern is a important signal for practitioners who deploy small models. We train all models for 40 epochs with a batch size of 64 and a learning rate of 0.001. The attention model is applied to the encoder only. We do not tune the decoder, so the comparison isolates the encoder change. Results may not transfer to sequence-to-sequence tasks.
