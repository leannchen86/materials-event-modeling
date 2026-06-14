# Compute Notes

## Local M2

Use local runs for data inspection, plotting, and tiny smoke tests.

```bash
python scripts/preprocess_xrd.py --limit 100
python scripts/train_xrd_encoder.py --limit 100 --max-epochs 1
```

## Zeus

SSH:

```bash
ssh -A leann@zeus.diffbot.com
```

Detected GPUs:

- 1x NVIDIA A100 80GB PCIe
- 6x NVIDIA RTX 2080 Ti 11GB

Prefer the A100 for GPU runs when available:

```bash
CUDA_VISIBLE_DEVICES=0 python scripts/train_xrd_encoder.py --config configs/zeus_a100.yaml
```

Before launching a long job, check GPU occupancy with `nvidia-smi`. Fall back to an RTX
2080 Ti only if the A100 is busy, unsuitable, or the run is just a tiny CUDA smoke test.

Example GPU selection:

```bash
CUDA_VISIBLE_DEVICES=0 python scripts/train_xrd_encoder.py --config configs/zeus_a100.yaml
```

Sync the local repo to the Zeus workspace manually:

```bash
ssh -A leann@zeus.diffbot.com 'mkdir -p ~/zeus/materials-event-modeling'

rsync -az --delete \
  --exclude '.venv/' \
  --exclude 'data/raw/*' \
  --exclude 'data/interim/*' \
  --exclude 'data/processed/*' \
  --exclude 'outputs/' \
  --exclude 'checkpoints/' \
  --exclude 'runs/' \
  --exclude 'wandb/' \
  /Users/leannchen/github/materials-event-modeling/ \
  leann@zeus.diffbot.com:~/zeus/materials-event-modeling/
```
