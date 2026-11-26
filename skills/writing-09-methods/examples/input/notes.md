# Run notes

Hardware: 4 x NVIDIA V100 GPUs with 32GB memory each.
Framework: PyTorch 2.1.0.
Dataset: GLUE benchmark, version 2.0, split into 80% train, 10% validation and 10% test.
Baseline: BERT-base, trained under the same budget as our model.
Command: python train.py --config config.json --seed 42
