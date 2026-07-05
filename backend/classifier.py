import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import librosa
import csv

print("Loading YAMNet model... (first run may take a minute)")
YAMNET_MODEL = hub.load("https://tfhub.dev/google/yamnet/1")
print("YAMNet loaded successfully.")


def load_class_names():
    class_map_path = YAMNET_MODEL.class_map_path().numpy().decode("utf-8")
    class_names = []
    with tf.io.gfile.GFile(class_map_path) as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            class_names.append(row[2])
    return class_names

CLASS_NAMES = load_class_names()

# ---------- Map YAMNet's raw labels to specific, human-friendly names ----------
# Each entry: list of raw YAMNet labels -> one clean display name.
LABEL_GROUPS = {
    "Dog Bark": ["Bark", "Bow-wow", "Dog", "Howl", "Growling", "Yip"],
    "Baby Crying": ["Baby cry, infant cry", "Crying, sobbing", "Whimper"],
    "Gunshot": ["Gunshot, gunfire", "Machine gun", "Fusillade", "Artillery fire"],
    "Glass Breaking": ["Glass", "Shatter", "Breaking"],
    "Fire Alarm": ["Fire alarm", "Smoke detector, smoke alarm"],
    "Siren": ["Siren", "Civil defense siren", "Police car (siren)", "Ambulance (siren)", "Fire engine, fire truck (siren)"],
    "Door Knock": ["Knock", "Door"],
    "Footsteps": ["Walk, footsteps", "Run"],
    "Engine Sound": ["Engine", "Engine starting", "Idling", "Accelerating, revving, vroom", "Car"],
    "Vehicle Horn": ["Vehicle horn, car horn, honking", "Car alarm", "Truck", "Air horn, truck horn"],
    "Rain": ["Rain", "Rain on surface", "Raindrop", "Rainstorm"],
    "Thunder": ["Thunder", "Thunderstorm"],
    "Human Speech": ["Speech", "Conversation", "Male speech, man speaking", "Female speech, woman speaking", "Child speech, kid speaking", "Narration, monologue"],
    "Clapping": ["Clapping", "Applause"],
    "Keyboard Typing": ["Typing", "Computer keyboard", "Typewriter"],
    "Machine Noise": ["Machine", "Mechanisms", "Motor vehicle (road)", "Hum"],
    "Drilling": ["Drill", "Power tool"],
    "Construction Sound": ["Jackhammer", "Hammer", "Sawing", "Wood"],
    "Bird Chirping": ["Bird", "Bird vocalization, bird call, bird song", "Chirp, tweet"],
    "Cat Meowing": ["Cat", "Meow", "Purr"],
    "Television": ["Television", "Radio"],
    "Music": ["Music", "Musical instrument", "Song", "Singing"],
    "Laughter": ["Laughter", "Giggle", "Chuckle, chortle", "Belly laugh"],
    "Cough": ["Cough", "Sneeze", "Throat clearing"],
    "Doorbell": ["Doorbell", "Ding-dong"],
    "Alarm Clock": ["Alarm clock", "Alarm", "Buzzer"],
    "Wind": ["Wind", "Wind noise (microphone)"],
    "Water Running": ["Water", "Water tap, faucet", "Pour", "Stream"],
    "Phone Ringing": ["Telephone bell ringing", "Ringtone", "Telephone"],
    "Snoring": ["Snoring"],
    "Human Speech (background)": ["Babble", "Chatter"],
}

# Build a reverse lookup: raw YAMNet label -> clean display name
RAW_TO_CLEAN = {}
for clean_name, raw_labels in LABEL_GROUPS.items():
    for raw in raw_labels:
        RAW_TO_CLEAN[raw.lower()] = clean_name


def clean_label(raw_label: str) -> str:
    """Converts a raw YAMNet label into a specific, friendly display name if we have a mapping."""
    return RAW_TO_CLEAN.get(raw_label.lower(), raw_label)


CRITICAL_KEYWORDS = [
    "gunshot", "gunfire", "explosion", "fire alarm", "smoke detector",
    "siren", "glass", "scream", "alarm",
]


def is_critical(label: str) -> bool:
    label_lower = label.lower()
    return any(keyword in label_lower for keyword in CRITICAL_KEYWORDS)


def load_audio_16k_mono(file_path: str) -> np.ndarray:
    waveform, _ = librosa.load(file_path, sr=16000, mono=True)
    return waveform.astype(np.float32)


def classify_audio(filename: str = None, file_path: str = None) -> list[dict]:
    if file_path is None:
        raise ValueError("file_path is required for real classification")

    waveform = load_audio_16k_mono(file_path)
    scores, embeddings, spectrogram = YAMNET_MODEL(waveform)
    scores_np = scores.numpy()
    mean_scores = scores_np.mean(axis=0)

    # Look through the top 30 raw predictions to find ones we have a specific mapping for
    top_indices = np.argsort(mean_scores)[::-1][:30]

    seen_labels = set()
    results = []
    for idx in top_indices:
        raw_label = CLASS_NAMES[idx]

        # Only accept labels we have an explicit, specific mapping for.
        # This filters out vague parent categories like "Animal" or "Domestic animals, pets".
        if raw_label.lower() not in RAW_TO_CLEAN:
            continue

        confidence = float(mean_scores[idx]) * 100
        display_label = RAW_TO_CLEAN[raw_label.lower()]

        if display_label in seen_labels:
            continue
        seen_labels.add(display_label)

        results.append({
            "label": display_label,
            "confidence": round(confidence, 1),
            "critical": is_critical(display_label),
        })

    # Keep only confident, specific detections
    filtered = [r for r in results if r["confidence"] >= 8.0]
    if not filtered and results:
        filtered = [results[0]]
    if not filtered:
        filtered = [{"label": "Unrecognized Sound", "confidence": 0.0, "critical": False}]

    return filtered[:3]


def classify_live_tick() -> dict | None:
    import random
    SOUND_CLASSES_DEMO = ["Dog Bark", "Human Speech", "Music", "Engine Sound", "Water Running", "Laughter"]
    if random.random() < 0.35:
        return None
    label = random.choice(SOUND_CLASSES_DEMO)
    confidence = round(random.uniform(70.0, 99.5), 1)
    return {"label": label, "confidence": confidence, "critical": is_critical(label)}