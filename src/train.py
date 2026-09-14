

import argparse
import csv
import math
import random
import time

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import precision_recall_fscore_support
from torch.utils.data import DataLoader

from config import (BATCH_SIZE, CHECKPOINT_DIR, DATASET_GOC_FILE, DROPOUT,
                    EARLY_STOP_PATIENCE, EPOCHS, LR, NUM_CLASSES,
                    RESULTS_DIR, SEED, WARMUP_EPOCHS, WEIGHT_DECAY)
from dataset import SkeletonWindowDataset
from stgcn import STGCN


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


@torch.no_grad()
def evaluate(model, loader, device, criterion):
    model.eval()
    total_loss, n = 0.0, 0
    all_pred, all_true = [], []
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        logits = model(x)
        loss = criterion(logits, y)
        total_loss += loss.item() * len(y)
        n += len(y)
        all_pred.append(logits.argmax(1).cpu().numpy())
        all_true.append(y.cpu().numpy())
    y_pred = np.concatenate(all_pred)
    y_true = np.concatenate(all_true)
    acc = (y_pred == y_true).mean()
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", pos_label=1, zero_division=0)
    return total_loss / max(n, 1), acc, prec, rec, f1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--lr", type=float, default=LR)
    args = parser.parse_args()

    set_seed(SEED)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Thiết bị: {device}")

    if not DATASET_GOC_FILE.exists():
        raise SystemExit(f"Chưa có {DATASET_GOC_FILE} — chạy lại "
                         "src/build_dataset.py (bản mới xuất cả 2 file).")
    d = np.load(DATASET_GOC_FILE)
    train_ds = SkeletonWindowDataset(d["X_train"], d["y_train"], augment=True)
    val_ds = SkeletonWindowDataset(d["X_val"], d["y_val"])
    print(f"Dataset train (ghim-gốc): {DATASET_GOC_FILE}")
    print(f"Train: {len(train_ds)} cửa sổ | Val: {len(val_ds)} cửa sổ")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                              num_workers=0, pin_memory=(device == "cuda"))
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False,
                            num_workers=0, pin_memory=(device == "cuda"))

    counts = np.bincount(d["y_train"], minlength=NUM_CLASSES).astype(np.float64)
    class_weights = torch.tensor(len(d["y_train"]) / (NUM_CLASSES * counts),
                                 dtype=torch.float32, device=device)
    print(f"Trọng số lớp [không té, té]: {class_weights.cpu().numpy().round(3)}")

    model = STGCN(num_classes=NUM_CLASSES, dropout=DROPOUT).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Số tham số ST-GCN: {n_params:,}")

    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr,
                                  weight_decay=WEIGHT_DECAY)

    def lr_lambda(epoch):
        if epoch < WARMUP_EPOCHS:
            return (epoch + 1) / WARMUP_EPOCHS
        t = (epoch - WARMUP_EPOCHS) / max(args.epochs - WARMUP_EPOCHS, 1)
        return 0.5 * (1 + math.cos(math.pi * t))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    history = []
    best_f1, best_epoch = -1.0, -1
    best_val_loss = float("inf")

    for epoch in range(args.epochs):
        model.train()
        t0 = time.time()
        total_loss, correct, n = 0.0, 0, 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(y)
            correct += (logits.argmax(1) == y).sum().item()
            n += len(y)
        scheduler.step()

        train_loss, train_acc = total_loss / n, correct / n
        val_loss, val_acc, val_prec, val_rec, val_f1 = evaluate(
            model, val_loader, device, criterion)

        history.append([epoch + 1, train_loss, train_acc, val_loss, val_acc,
                        val_prec, val_rec, val_f1])
        marker = ""
        improved = (val_f1 > best_f1 + 1e-6) or (
            abs(val_f1 - best_f1) <= 1e-6 and val_loss < best_val_loss)
        if improved:
            best_f1, best_epoch, best_val_loss = val_f1, epoch, val_loss
            torch.save({"model": model.state_dict(), "epoch": epoch + 1,
                        "val_f1": val_f1}, CHECKPOINT_DIR / "best.pt")
            marker = "  *lưu best*"
        print(f"Epoch {epoch+1:3d}/{args.epochs} | "
              f"loss {train_loss:.4f} acc {train_acc:.3f} | "
              f"val loss {val_loss:.4f} acc {val_acc:.3f} "
              f"P {val_prec:.3f} R {val_rec:.3f} F1 {val_f1:.3f} | "
              f"{time.time()-t0:.1f}s{marker}")

        if epoch - best_epoch >= EARLY_STOP_PATIENCE:
            print(f"Early stopping (val F1 không cải thiện {EARLY_STOP_PATIENCE} epoch).")
            break

    torch.save({"model": model.state_dict(), "epoch": len(history)},
               CHECKPOINT_DIR / "last.pt")

    with open(RESULTS_DIR / "train_history.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["epoch", "train_loss", "train_acc", "val_loss",
                         "val_acc", "val_precision", "val_recall", "val_f1"])
        writer.writerows(history)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        h = np.array(history)
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        axes[0].plot(h[:, 0], h[:, 1], label="train loss")
        axes[0].plot(h[:, 0], h[:, 3], label="val loss")
        axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("Loss"); axes[0].legend()
        axes[0].set_title("Loss")
        axes[1].plot(h[:, 0], h[:, 2], label="train acc")
        axes[1].plot(h[:, 0], h[:, 4], label="val acc")
        axes[1].plot(h[:, 0], h[:, 7], label="val F1 (té ngã)")
        axes[1].set_xlabel("Epoch"); axes[1].legend(); axes[1].set_title("Độ chính xác")
        fig.tight_layout()
        fig.savefig(RESULTS_DIR / "training_curves.png", dpi=120)
        print(f"Đã lưu biểu đồ: {RESULTS_DIR / 'training_curves.png'}")
    except Exception as e:
        print(f"Không vẽ được biểu đồ: {e}")

    print(f"\nTốt nhất: epoch {best_epoch+1}, val F1 = {best_f1:.4f}")
    print(f"Checkpoint: {CHECKPOINT_DIR / 'best.pt'}")


if __name__ == "__main__":
    main()
