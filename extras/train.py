import os
from pathlib import Path

import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator


IMG_SIZE = 224
BATCH_SIZE = 32
EPOCHS = 25
DATASET_DIR = Path("dataset_final")
REAL_DIR = DATASET_DIR / "real"
FAKE_DIR = DATASET_DIR / "fake"
MODEL_PATH = Path("models") / "anti_spoof.h5"


def validate_dataset_structure() -> None:
    missing_dirs = [str(path) for path in (DATASET_DIR, REAL_DIR, FAKE_DIR) if not path.exists()]
    if missing_dirs:
        raise FileNotFoundError(
            "Missing required dataset folders: "
            + ", ".join(missing_dirs)
            + ". Expected structure: dataset_final/real and dataset_final/fake."
        )

    real_images = [path for path in REAL_DIR.rglob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    fake_images = [path for path in FAKE_DIR.rglob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png"}]

    if not real_images or not fake_images:
        raise ValueError(
            "Both dataset_final/real and dataset_final/fake must contain image files before training."
        )

    fake_names = " ".join(path.name.lower() for path in fake_images)
    expected_fake_signals = {
        "screen": "phone or laptop screen attacks",
        "print": "printed photo attacks",
        "replay": "replay attack samples",
    }

    missing_signals = [
        description for keyword, description in expected_fake_signals.items() if keyword not in fake_names
    ]

    print(f"Found {len(real_images)} real images and {len(fake_images)} fake images.")
    if missing_signals:
        print("WARNING: Fake samples may be incomplete for strong anti-spoofing.")
        print("Please include:", ", ".join(missing_signals))
        print("Also add blur, reflections, and mixed-device captures where possible.")


def build_generators() -> tuple:
    datagen = ImageDataGenerator(
        rescale=1.0 / 255.0,
        validation_split=0.2,
        rotation_range=20,
        zoom_range=0.3,
        brightness_range=[0.4, 1.6],
        shear_range=0.2,
        horizontal_flip=True,
        fill_mode="nearest",
    )

    train = datagen.flow_from_directory(
        str(DATASET_DIR),
        target_size=(IMG_SIZE, IMG_SIZE),
        batch_size=BATCH_SIZE,
        class_mode="binary",
        subset="training",
        shuffle=True,
    )

    val = datagen.flow_from_directory(
        str(DATASET_DIR),
        target_size=(IMG_SIZE, IMG_SIZE),
        batch_size=BATCH_SIZE,
        class_mode="binary",
        subset="validation",
        shuffle=False,
    )

    print("Class Labels:", train.class_indices)
    if train.class_indices != {"fake": 0, "real": 1}:
        print("WARNING: Expected class mapping {'fake': 0, 'real': 1}.")

    return train, val


def build_model() -> tf.keras.Model:
    base = tf.keras.applications.MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,
        weights="imagenet",
    )
    base.trainable = False

    for layer in base.layers[-30:]:
        layer.trainable = True

    x = tf.keras.layers.GlobalAveragePooling2D()(base.output)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dense(256, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.5)(x)
    x = tf.keras.layers.Dense(64, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    output = tf.keras.layers.Dense(1, activation="sigmoid")(x)

    model = tf.keras.Model(inputs=base.input, outputs=output)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model


def main() -> None:
    os.makedirs(MODEL_PATH.parent, exist_ok=True)
    validate_dataset_structure()
    train, val = build_generators()
    model = build_model()
    model.summary()

    class_weight = {
        0: 1.0,   # fake
        1: 1.5,   # real
    }

    history = model.fit(
        train,
        validation_data=val,
        epochs=EPOCHS,
        class_weight=class_weight,
    )

    model.save(MODEL_PATH)

    final_train_accuracy = history.history["accuracy"][-1]
    final_val_accuracy = history.history["val_accuracy"][-1]

    print(f"Final training accuracy: {final_train_accuracy:.4f}")
    print(f"Final validation accuracy: {final_val_accuracy:.4f}")
    print(f"Model saved to: {MODEL_PATH}")


if __name__ == "__main__":
    main()
