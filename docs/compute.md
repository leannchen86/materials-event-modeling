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

Use RTX 2080 Ti devices for early CUDA debugging and small/medium model runs. Reserve
the A100 for larger pretraining runs after preprocessing, checkpointing, and evaluation
are known to work.

Example GPU selection:

```bash
CUDA_VISIBLE_DEVICES=4 python scripts/train_xrd_encoder.py --config configs/zeus_2080ti.yaml
```

Sync the local repo to the Zeus workspace:

```bash
bash scripts/sync_to_zeus.sh
```
