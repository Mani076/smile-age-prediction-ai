"""
Advanced Model Training — Age & Smile
======================================
Age  : EfficientNetB0 + age-balanced sampling + 3-phase cosine LR fine-tune
       + random crop/flip/color augmentation + Huber loss
Smile: SE-CNN (squeeze-excitation) + 5-signal continuous labeling
       + focal loss + label smoothing + cosine-restart LR

Usage:
  python train_models.py --model age
  python train_models.py --model smile
  python train_models.py --model all
"""

import os, argparse, warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

import numpy as np
import cv2
from pathlib import Path

MODEL_DIR = Path("backend_fastapi/ml_models")
MODEL_DIR.mkdir(exist_ok=True)

UTK_DIRS = [
    Path("UTKface Dataset/UTKFace"),
    Path("UTKface Dataset/crop_part1"),
]


def load_tf():
    import tensorflow as tf
    tf.get_logger().setLevel("ERROR")
    return tf


def parse_utk_age(filename):
    name = Path(filename).name.replace(".jpg.chip.jpg", "").replace(".jpg", "")
    try:
        return int(name.split("_")[0])
    except Exception:
        return None


def get_utk_files(max_total=25000):
    all_files = []
    for d in UTK_DIRS:
        if not d.exists():
            continue
        files = list(d.glob("*.jpg")) + list(d.glob("*.jpg.chip.jpg"))
        if not files:
            files = [f for f in d.iterdir() if f.is_file()]
        valid = [(f, parse_utk_age(f.name)) for f in files]
        valid = [(f, a) for f, a in valid if a is not None and 1 <= a <= 100]
        all_files.extend(valid)
        print(f"  {d}: {len(valid)} valid images")
    np.random.shuffle(all_files)
    all_files = all_files[:max_total]
    print(f"  Total: {len(all_files)} images")
    return all_files


# ══════════════════════════════════════════════════════════════════
# AGE — EfficientNetB0 + balanced sampling + 3-phase training
# ══════════════════════════════════════════════════════════════════

def balance_age_files(files, bins=10, max_per_bin=2000):
    """
    Bin ages 1-100 into equal-width buckets and cap each bucket.
    Prevents over-fitting to the 20-40 majority in UTKFace.
    """
    buckets = [[] for _ in range(bins)]
    for f, a in files:
        idx = min(int((a - 1) / 100 * bins), bins - 1)
        buckets[idx].append((f, a))
    balanced = []
    for b in buckets:
        np.random.shuffle(b)
        balanced.extend(b[:max_per_bin])
    np.random.shuffle(balanced)
    ages = [a for _, a in balanced]
    print(f"  Balanced: {len(balanced)} samples  "
          f"mean={np.mean(ages):.1f}  std={np.std(ages):.1f}")
    return balanced


def build_age_model(tf):
    """
    EfficientNetB0 regression head.
    Input : 96x96x3 float32 (0-1).  Internally rescaled to 0-255 for EfficientNet.
    Output: single linear neuron -> predicted age in years.
    """
    base = tf.keras.applications.EfficientNetB0(
        input_shape=(96, 96, 3), include_top=False, weights="imagenet"
    )
    base.trainable = False

    inputs = tf.keras.Input(shape=(96, 96, 3))
    x = inputs * 255.0
    x = base(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dense(
        512, activation="relu",
        kernel_regularizer=tf.keras.regularizers.l2(1e-4))(x)
    x = tf.keras.layers.Dropout(0.45)(x)
    x = tf.keras.layers.Dense(
        256, activation="relu",
        kernel_regularizer=tf.keras.regularizers.l2(1e-4))(x)
    x = tf.keras.layers.Dropout(0.35)(x)
    x = tf.keras.layers.Dense(
        128, activation="relu",
        kernel_regularizer=tf.keras.regularizers.l2(1e-4))(x)
    x = tf.keras.layers.Dropout(0.25)(x)
    outputs = tf.keras.layers.Dense(1, activation="linear")(x)

    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="huber",
        metrics=["mae"]
    )
    return model, base


def make_age_dataset(tf, files, batch_size=64, augment=False):
    paths = [str(f) for f, _ in files]
    ages  = [float(a) for _, a in files]

    def load_and_preprocess(path, age):
        img = tf.io.read_file(path)
        img = tf.image.decode_jpeg(img, channels=3)
        img = tf.image.resize(img, [96, 96])
        img = tf.cast(img, tf.float32) / 255.0
        if augment:
            img = tf.image.random_flip_left_right(img)
            img = tf.image.random_brightness(img, 0.20)
            img = tf.image.random_contrast(img, 0.80, 1.20)
            img = tf.image.random_saturation(img, 0.80, 1.20)
            img = tf.image.random_hue(img, 0.08)
            img = tf.image.random_crop(img, [88, 88, 3])
            img = tf.image.resize(img, [96, 96])
            img = tf.clip_by_value(img, 0.0, 1.0)
        return img, age

    ds = tf.data.Dataset.from_tensor_slices((paths, ages))
    if augment:
        ds = ds.shuffle(buffer_size=5000)
    ds = ds.map(load_and_preprocess, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    return ds


def train_age_model():
    print("\n" + "=" * 60)
    print("  TRAINING AGE MODEL  (EfficientNetB0 + balanced + 3-phase)")
    print("=" * 60)
    tf = load_tf()

    raw = get_utk_files(max_total=25000)
    if len(raw) < 500:
        print("  Not enough data. Aborting.")
        return False

    files = balance_age_files(raw, bins=10, max_per_bin=1500)
    np.random.shuffle(files)
    split = int(len(files) * 0.85)
    train_files, val_files = files[:split], files[split:]
    print(f"  Train: {len(train_files)}  Val: {len(val_files)}")

    train_ds = make_age_dataset(tf, train_files, batch_size=64, augment=True)
    val_ds   = make_age_dataset(tf, val_files,   batch_size=64, augment=False)

    model, base = build_age_model(tf)
    best_path   = str(MODEL_DIR / "age_model_best.keras")

    # Use ReduceLROnPlateau — CosineDecay schedules passed directly to Adam
    # can cause step-counter issues in TF 2.15 on Windows.
    def make_cbs(patience_es, patience_lr):
        return [
            tf.keras.callbacks.EarlyStopping(
                patience=patience_es, restore_best_weights=True,
                monitor="val_mae", verbose=1),
            tf.keras.callbacks.ReduceLROnPlateau(
                factor=0.5, patience=patience_lr, min_lr=1e-7,
                monitor="val_mae", verbose=1),
            tf.keras.callbacks.ModelCheckpoint(
                best_path, save_best_only=True, monitor="val_mae", verbose=0),
        ]

    # Phase 1: frozen base, train head only
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="huber", metrics=["mae"]
    )
    print("\n  Phase 1: frozen base (15 epochs)...")
    model.fit(train_ds, validation_data=val_ds, epochs=15,
              callbacks=make_cbs(5, 3), verbose=1)

    # Phase 2: unfreeze top 50 layers
    base.trainable = True
    for layer in base.layers[:-50]:
        layer.trainable = False
    model.compile(
        optimizer=tf.keras.optimizers.Adam(3e-5),
        loss="huber", metrics=["mae"]
    )
    print("\n  Phase 2: top-50 fine-tune (20 epochs)...")
    model.fit(train_ds, validation_data=val_ds, epochs=20,
              callbacks=make_cbs(7, 4), verbose=1)

    # Phase 3: full unfreeze, ultra-low LR
    base.trainable = True
    model.compile(
        optimizer=tf.keras.optimizers.Adam(5e-6),
        loss="huber", metrics=["mae"]
    )
    print("\n  Phase 3: full unfreeze (10 epochs)...")
    model.fit(train_ds, validation_data=val_ds, epochs=10,
              callbacks=make_cbs(5, 3), verbose=1)

    save_path = str(MODEL_DIR / "age_model.keras")
    model.save(save_path)
    _, mae = model.evaluate(val_ds, verbose=0)
    print(f"\n  Saved age_model.keras  |  Val MAE: {mae:.2f} years")
    return True


# ══════════════════════════════════════════════════════════════════
# SMILE — SE-CNN + focal loss + label smoothing + cosine-restart LR
# ══════════════════════════════════════════════════════════════════

def label_smile_images(files):
    """
    5-signal continuous scoring. Ranks all images, takes top/bottom 28%.
    Signals: mouth texture, Haar cascade, lip brightness, cheek raise, corner symmetry.
    """
    smile_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_smile.xml"
    )

    scored = []
    print("  Scoring smile data (5-signal approach)...")
    for i, (f, _) in enumerate(files):
        if i % 2000 == 0:
            print(f"    {i}/{len(files)} scored...")

        img = cv2.imread(str(f))
        if img is None:
            continue

        img  = cv2.resize(img, (96, 96))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        eq   = cv2.equalizeHist(gray)

        # Signal 1: mouth texture (teeth = bright, high std)
        mouth      = eq[58:82, 18:78]
        mouth_std  = float(np.std(mouth))
        mouth_max  = float(np.percentile(mouth, 95))
        mouth_mean = float(np.mean(mouth))

        # Signal 2: Haar smile cascade
        lower  = eq[48:, :]
        strict = smile_cascade.detectMultiScale(lower, 1.4, 18, minSize=(12, 6))
        loose  = smile_cascade.detectMultiScale(lower, 1.3, 10, minSize=(8,  4))

        # Signal 3: lip brightness ratio (open smile = lower lip brighter)
        upper_lip = gray[54:66, 24:72]
        lower_lip = gray[66:82, 24:72]
        lip_diff  = float(np.mean(lower_lip) - np.mean(upper_lip)) \
                    if upper_lip.size > 0 else 0.0

        # Signal 4: cheek brightness (smile lifts cheeks)
        cheek_l = gray[42:62, 6:30]
        cheek_r = gray[42:62, 66:90]
        cheek_b = (float(np.mean(cheek_l)) + float(np.mean(cheek_r))) / 2.0

        # Signal 5: mouth corner symmetry
        corner_l = eq[68:80, 18:32]
        corner_r = eq[68:80, 64:78]
        sym = 1.0 - abs(float(np.mean(corner_l)) - float(np.mean(corner_r))) / 128.0

        score = 0.0
        if len(strict) > 0: score += 3.5
        if len(loose)  > 0: score += 1.0
        score += min(3.0, mouth_std / 28.0)
        score += min(2.0, (mouth_max - mouth_mean) / 38.0)
        score += max(-1.0, min(1.0, lip_diff / 18.0))
        score += min(0.5, (cheek_b - 100.0) / 80.0)
        score += sym * 0.5

        scored.append((str(f), score))

    print(f"  Scored {len(scored)} images")
    scored.sort(key=lambda x: x[1])
    n      = len(scored)
    cutoff = int(n * 0.28)

    no_smile = [(p, 0) for p, _ in scored[:cutoff]]
    smile    = [(p, 1) for p, _ in scored[n - cutoff:]]
    np.random.shuffle(no_smile)
    np.random.shuffle(smile)

    cap      = min(len(smile), len(no_smile), 5000)
    balanced = smile[:cap] + no_smile[:cap]
    np.random.shuffle(balanced)
    print(f"  Final: {len(balanced)} samples ({cap} smile + {cap} no-smile)")
    return balanced


def focal_loss(gamma=2.0, alpha=0.25):
    """
    Focal loss: down-weights easy examples, focuses training on hard ones.
    Better than BCE for noisy pseudo-labels.
    """
    def loss_fn(y_true, y_pred):
        import tensorflow as tf
        y_pred  = tf.clip_by_value(y_pred, 1e-7, 1.0 - 1e-7)
        bce     = -(y_true * tf.math.log(y_pred)
                    + (1 - y_true) * tf.math.log(1 - y_pred))
        p_t     = y_true * y_pred + (1 - y_true) * (1 - y_pred)
        alpha_t = y_true * alpha  + (1 - y_true) * (1 - alpha)
        fl      = alpha_t * tf.pow(1.0 - p_t, gamma) * bce
        return tf.reduce_mean(fl)
    return loss_fn


def build_smile_model(tf):
    """
    Deep CNN with Squeeze-and-Excitation blocks.
    Input : 96x96x1 grayscale (0-1 normalized).
    Output: sigmoid probability.
    SE blocks recalibrate channel importance — better feature selection.
    """
    def se_block(x, ratio=8):
        ch = x.shape[-1]
        se = tf.keras.layers.GlobalAveragePooling2D()(x)
        se = tf.keras.layers.Dense(max(1, ch // ratio), activation="relu")(se)
        se = tf.keras.layers.Dense(ch, activation="sigmoid")(se)
        se = tf.keras.layers.Reshape((1, 1, ch))(se)
        return tf.keras.layers.Multiply()([x, se])

    def conv_bn_relu(x, filters, kernel=3):
        x = tf.keras.layers.Conv2D(
            filters, kernel, padding="same",
            kernel_regularizer=tf.keras.regularizers.l2(1e-4))(x)
        x = tf.keras.layers.BatchNormalization()(x)
        return tf.keras.layers.Activation("relu")(x)

    inputs = tf.keras.Input(shape=(96, 96, 1))

    # Stem
    x = conv_bn_relu(inputs, 32)
    x = conv_bn_relu(x, 32)
    x = tf.keras.layers.MaxPooling2D(2)(x)
    x = tf.keras.layers.Dropout(0.20)(x)

    # Block 1 + SE
    x = conv_bn_relu(x, 64)
    x = conv_bn_relu(x, 64)
    x = se_block(x, ratio=8)
    x = tf.keras.layers.MaxPooling2D(2)(x)
    x = tf.keras.layers.Dropout(0.25)(x)

    # Block 2 + SE
    x = conv_bn_relu(x, 128)
    x = conv_bn_relu(x, 128)
    x = se_block(x, ratio=8)
    x = tf.keras.layers.MaxPooling2D(2)(x)
    x = tf.keras.layers.Dropout(0.30)(x)

    # Block 3 + SE
    x = conv_bn_relu(x, 256)
    x = conv_bn_relu(x, 256)
    x = se_block(x, ratio=16)
    x = tf.keras.layers.MaxPooling2D(2)(x)
    x = tf.keras.layers.Dropout(0.35)(x)

    # Global pooling
    x = tf.keras.layers.GlobalAveragePooling2D()(x)

    # Head
    x = tf.keras.layers.Dense(
        256, activation="relu",
        kernel_regularizer=tf.keras.regularizers.l2(1e-4))(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dropout(0.45)(x)
    x = tf.keras.layers.Dense(128, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.30)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)

    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss=focal_loss(gamma=2.0, alpha=0.25),
        metrics=["accuracy", tf.keras.metrics.AUC(name="auc")]
    )
    return model


def make_smile_dataset(tf, labeled, batch_size=64, augment=False):
    """No label smoothing here — use Keras BinaryCrossentropy(label_smoothing=0.05) instead."""
    paths  = [p for p, _ in labeled]
    labels = [float(l) for _, l in labeled]

    def load_smile(path, label):
        img = tf.io.read_file(path)
        img = tf.image.decode_jpeg(img, channels=1)
        img = tf.image.resize(img, [96, 96])
        img = tf.cast(img, tf.float32) / 255.0
        if augment:
            img = tf.image.random_flip_left_right(img)
            img = tf.image.random_brightness(img, 0.20)
            img = tf.image.random_contrast(img, 0.80, 1.20)
            img = tf.image.random_crop(img, [88, 88, 1])
            img = tf.image.resize(img, [96, 96])
            img = tf.clip_by_value(img, 0.0, 1.0)
        return img, label

    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    if augment:
        ds = ds.shuffle(buffer_size=5000)
    ds = ds.map(load_smile, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    return ds


def train_smile_model():
    print("\n" + "=" * 60)
    print("  TRAINING SMILE MODEL  (SE-CNN + focal loss + cosine-restart LR)")
    print("=" * 60)
    tf = load_tf()

    files = get_utk_files(max_total=20000)
    if len(files) < 500:
        print("  Not enough data. Aborting.")
        return False

    labeled = label_smile_images(files)
    if len(labeled) < 400:
        print("  Not enough labeled data. Aborting.")
        return False

    np.random.shuffle(labeled)
    split         = int(len(labeled) * 0.85)
    train_labeled = labeled[:split]
    val_labeled   = labeled[split:]
    print(f"  Train: {len(train_labeled)}  Val: {len(val_labeled)}")

    train_ds = make_smile_dataset(tf, train_labeled, batch_size=64, augment=True)
    val_ds   = make_smile_dataset(tf, val_labeled,   batch_size=64, augment=False)

    model     = build_smile_model(tf)
    best_path = str(MODEL_DIR / "smile_model_best.h5")

    # BinaryCrossentropy with label_smoothing=0.05 — works correctly with
    # AUC metric in TF 2.15. Focal loss breaks AUC tracking with soft labels.
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss=tf.keras.losses.BinaryCrossentropy(label_smoothing=0.05),
        metrics=["accuracy", tf.keras.metrics.AUC(name="auc")]
    )

    cbs = [
        tf.keras.callbacks.EarlyStopping(
            patience=8, restore_best_weights=True,
            monitor="val_auc", mode="max", verbose=1),
        tf.keras.callbacks.ReduceLROnPlateau(
            factor=0.5, patience=4, min_lr=1e-6,
            monitor="val_auc", mode="max", verbose=1),
        tf.keras.callbacks.ModelCheckpoint(
            best_path, save_best_only=True,
            monitor="val_auc", mode="max", verbose=0),
    ]

    print("\n  Training (40 epochs max, ReduceLROnPlateau)...")
    model.fit(train_ds, validation_data=val_ds, epochs=40,
              callbacks=cbs, verbose=1)

    save_path = str(MODEL_DIR / "smile_model.h5")
    model.save(save_path)
    res = model.evaluate(val_ds, verbose=0)
    print(f"\n  Saved smile_model.h5")
    print(f"  Val Accuracy: {res[1]*100:.1f}%  |  Val AUC: {res[2]:.4f}")
    return True


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train age and/or smile models on UTKFace dataset"
    )
    parser.add_argument("--model", choices=["all", "age", "smile"],
                        default="all")
    args = parser.parse_args()

    print("\nUTKFace directories:")
    for d in UTK_DIRS:
        if d.exists():
            n = len(list(d.glob("*.jpg")) + list(d.glob("*.jpg.chip.jpg")))
            print(f"  FOUND  : {d}  ({n} files)")
        else:
            print(f"  MISSING: {d}")

    results = {}
    if args.model in ("all", "age"):
        results["age"]   = train_age_model()
    if args.model in ("all", "smile"):
        results["smile"] = train_smile_model()

    print("\n" + "=" * 60)
    for name, ok in results.items():
        print(f"  {name.upper():8s}  {'SUCCESS' if ok else 'FAILED'}")
    print("\n  Restart backend to load new models:")
    print("  cd backend_fastapi && uvicorn app.main:app --reload --port 8000")
    print("=" * 60)
