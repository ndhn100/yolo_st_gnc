

import argparse
import time

import numpy as np
import torch
from sklearn.metrics import (classification_report, confusion_matrix,
                             precision_recall_fscore_support)
from torch.utils.data import DataLoader

from config import (ACTIVITY_NAMES, CHECKPOINT_DIR, CLASS_NAMES, DATASET_FILE,
                    NUM_CLASSES, RESULTS_DIR)
from dataset import SkeletonWindowDataset
from stgcn import STGCN


@torch.no_grad()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["test", "val"], default="test")
    parser.add_argument("--checkpoint", default=str(CHECKPOINT_DIR / "best.pt"))
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    d = np.load(DATASET_FILE)
    X, y = d[f"X_{args.split}"], d[f"y_{args.split}"]
    activities = d[f"activity_{args.split}"]
    subjects = d[f"subject_{args.split}"]
    print(f"Đánh giá split '{args.split}': {len(y)} cửa sổ, "
          f"subjects {sorted(set(subjects.tolist()))}")

    model = STGCN(num_classes=NUM_CLASSES).to(device)
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=True)
    model.load_state_dict(ckpt["model"])
    model.eval()
    print(f"Checkpoint: {args.checkpoint} (epoch {ckpt.get('epoch', '?')})")

    loader = DataLoader(SkeletonWindowDataset(X, y), batch_size=128)
    all_pred, all_prob = [], []
    for xb, _ in loader:
        logits = model(xb.to(device))
        prob = torch.softmax(logits, dim=1)[:, 1]
        all_pred.append(logits.argmax(1).cpu().numpy())
        all_prob.append(prob.cpu().numpy())
    y_pred = np.concatenate(all_pred)
    y_prob = np.concatenate(all_prob)

    acc = (y_pred == y).mean()
    prec, rec, f1, _ = precision_recall_fscore_support(
        y, y_pred, average="binary", pos_label=1, zero_division=0)

    print("\n===== KẾT QUẢ =====")
    print(f"Accuracy : {acc:.4f}")
    print(f"Precision: {prec:.4f}   (té ngã)")
    print(f"Recall   : {rec:.4f}   (té ngã — độ nhạy)")
    print(f"F1-score : {f1:.4f}   (té ngã)")
    print("\n" + classification_report(y, y_pred, target_names=CLASS_NAMES,
                                       zero_division=0))

    cm = confusion_matrix(y, y_pred)
    print("Confusion matrix [hàng=thực tế, cột=dự đoán]:")
    print(cm)

    print("\nĐộ chính xác theo hoạt động:")
    for act in sorted(set(activities.tolist())):
        mask = activities == act
        a = (y_pred[mask] == y[mask]).mean()
        print(f"  Activity {act:2d} ({ACTIVITY_NAMES.get(act, '?'):<28}): "
              f"{a:.3f}  ({mask.sum()} cửa sổ)")

    x1 = torch.from_numpy(X[:1]).to(device)
    for _ in range(10):
        model(x1)
    if device == "cuda":
        torch.cuda.synchronize()
    t0 = time.time()
    n_rep = 100
    for _ in range(n_rep):
        model(x1)
    if device == "cuda":
        torch.cuda.synchronize()
    latency_ms = (time.time() - t0) / n_rep * 1000
    print(f"\nĐộ trễ suy luận ST-GCN: {latency_ms:.2f} ms/cửa sổ ({device})")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5, 4.5))
        im = ax.imshow(cm, cmap="Blues")
        ax.set_xticks([0, 1], CLASS_NAMES)
        ax.set_yticks([0, 1], CLASS_NAMES)
        ax.set_xlabel("Dự đoán"); ax.set_ylabel("Thực tế")
        ax.set_title(f"Confusion matrix ({args.split}) — Acc {acc:.3f}")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                        color="white" if cm[i, j] > cm.max() / 2 else "black",
                        fontsize=14)
        fig.colorbar(im)
        fig.tight_layout()
        out_png = RESULTS_DIR / f"confusion_matrix_{args.split}.png"
        fig.savefig(out_png, dpi=120)
        print(f"Đã lưu: {out_png}")
    except Exception as e:
        print(f"Không vẽ được confusion matrix: {e}")

    err_idx = np.where(y_pred != y)[0]
    if len(err_idx):
        import csv
        err_csv = RESULTS_DIR / f"errors_{args.split}.csv"
        with open(err_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["subject", "activity", "trial", "y_true", "y_pred", "p_fall"])
            for i in err_idx:
                w.writerow([subjects[i], activities[i], d[f"trial_{args.split}"][i],
                            y[i], y_pred[i], f"{y_prob[i]:.3f}"])
        print(f"Đã lưu {len(err_idx)} mẫu sai: {err_csv}")


if __name__ == "__main__":
    main()
