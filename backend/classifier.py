import numpy as np
import librosa
import csv
import os
import urllib.request
import tflite_runtime.interpreter as tflite

MODEL_PATH = "/tmp/yamnet.tflite"
CLASS_MAP_PATH = "/tmp/yamnet_class_map.csv"

MODEL_URL = "https://tfhub.dev/google/lite-model/yamnet/tflite/1?lite-format=tflite"
CLASS_MAP_URL = "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv"


def ensure_downloaded(url: str, path: str):
    if not os.path.exists(path):
        print(f"Downloading {path}...")
        urllib.request.urlretrieve(url, path)
        print(f"Downloaded {path}")


print("Loading lightweight YAMNet (TFLite)...")
ensure_downloaded(MODEL_URL, MODEL_PATH)
ensure_downloaded(CLASS_MAP_URL, CLASS_MAP_PATH)

INTERPRETER = tflite.Interpreter(model_path=MODEL_PATH)
INTERPRETER.allocate_tensors()
INPUT_DETAILS = INTERPRETER.get_input_details()
OUTPUT_DETAILS = INTERPRETER.get_output_details()
FRAME_SIZE = INPUT_DETAILS[0]["shape"][0]  # 15600 samples (~0.975s at 16kHz)

print("YAMNet (TFLite) loaded successfully.")


def load_class_names():
    class_names = []
    with open(CLASS_MAP_PATH) as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            class_names.append(row[2])
    return class_names

CLASS_NAMES = load_class_names()

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

RAW_TO_CLEAN = {}
for clean_name, raw_labels in LABEL_GROUPS.items():
    for raw in raw_labels:
        RAW_TO_CLEAN[raw.lower()] = clean_name

CRITICAL_KEYWORDS = [
    "gunshot", "gunfire", "explosion", "fire alarm", "smoke detector",
    "siren", "glass", "scream", "alarm",
]


def is_critical(label: str) -> bool:
    return any(k in label.lower() for k in CRITICAL_KEYWORDS)


def load_audio_16k_mono(file_path: str) -> np.ndarray:
    waveform, _ = librosa.load(file_path, sr=16000, mono=True)
    return waveform.astype(np.float32)


def run_yamnet_tflite(waveform: np.ndarray) -> np.ndarray:
    """
    Runs the TFLite YAMNet model over the waveform in fixed-size frames
    and returns averaged class scores.
    """
    num_frames = max(1, len(waveform) // FRAME_SIZE)
    all_scores = []

    for i in range(num_frames):
        start = i * FRAME_SIZE
        frame = waveform[start:start + FRAME_SIZE]
        if len(frame) < FRAME_SIZE:
            frame = np.pad(frame, (0, FRAME_SIZE - len(frame)))

        INTERPRETER.set_tensor(INPUT_DETAILS[0]["index"], frame)
        INTERPRETER.invoke()
        scores = INTERPRETER.get_tensor(OUTPUT_DETAILS[0]["index"])
        all_scores.append(scores[0])

    return np.mean(all_scores, axis=0)


def classify_audio(filename: str = None, file_path: str = None) -> list[dict]:
    if file_path is None:
        raise ValueError("file_path is required for real classification")

    waveform = load_audio_16k_mono(file_path)
    mean_scores = run_yamnet_tflite(waveform)

    top_indices = np.argsort(mean_scores)[::-1][:30]

    seen_labels = set()
    results = []
    for idx in top_indices:
        raw_label = CLASS_NAMES[idx]
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