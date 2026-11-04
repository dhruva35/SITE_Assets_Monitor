import os, random, shutil
from pathlib import Path

def main():
    random.seed(42)
    ds_root = Path("data/datasets/containers")
    train_img = ds_root / "train" / "images"
    train_lbl = ds_root / "train" / "labels"
    val_img = ds_root / "val" / "images"
    val_lbl = ds_root / "val" / "labels"

    for p in [train_img, train_lbl, val_img, val_lbl]:
        p.mkdir(parents=True, exist_ok=True)

    all_imgs = sorted(list((ds_root / "images").glob("*.jpg")))
    indices = list(range(len(all_imgs)))
    random.shuffle(indices)

    split = int(0.85 * len(indices))
    train_idx = set(indices[:split])

    for i, img_p in enumerate(all_imgs):
        lbl_p = ds_root / "labels" / f"{img_p.stem}.txt"
        if i in train_idx:
            shutil.copy(img_p, train_img / img_p.name)
            if lbl_p.exists():
                shutil.copy(lbl_p, train_lbl / lbl_p.name)
        else:
            shutil.copy(img_p, val_img / img_p.name)
            if lbl_p.exists():
                shutil.copy(lbl_p, val_lbl / lbl_p.name)

    yaml_content = f"""path: {ds_root.resolve().as_posix()}
train: train/images
val: val/images
names:
  0: container
"""
    with open(ds_root / "data.yaml", "w") as f:
        f.write(yaml_content)

    n_train = len(list(train_img.glob('*.jpg')))
    n_val = len(list(val_img.glob('*.jpg')))
    print(f"Dataset split complete: {n_train} train images, {n_val} val images")
    print(f"data.yaml path: {(ds_root / 'data.yaml').resolve()}")

if __name__ == "__main__":
    main()

