"""
extract_ceo_frames.py
=====================
Downloads an earnings call video (YouTube URL or local file) and extracts
high-quality, frontal CEO face frames suitable for dark circle / eye bag analysis.

Pipeline
--------
1. Download video via yt-dlp (skipped if local file provided).
2. Sample one frame every N seconds (configurable, default: 5s).
3. Run MediaPipe FaceMesh on each sampled frame.
4. Keep frames that pass quality filters:
   - At least one face detected
   - Face bounding box covers ≥ MIN_FACE_FRACTION of frame height
   - Head yaw (left-right rotation) within ±YAW_THRESHOLD degrees
   - Head pitch (up-down tilt) within ±PITCH_THRESHOLD degrees
5. Deduplicate: skip frames too similar to the last saved frame (MSE threshold).
6. Save accepted frames as JPEG files with metadata in the filename.

Usage
-----
    # From a YouTube URL:
    python extract_ceo_frames.py --url "https://www.youtube.com/watch?v=XXXX" --out ./frames

    # From a local video file:
    python extract_ceo_frames.py --file earnings_call.mp4 --out ./frames

    # Adjust sampling rate (1 frame every 10 seconds):
    python extract_ceo_frames.py --url "..." --out ./frames --interval 10

    # After extraction, run the scorer on all frames:
    # python dark_circle_score.py --image ./frames/frame_0045s.jpg

Dependencies
------------
    pip install yt-dlp mediapipe opencv-python-headless numpy
"""

import argparse
import os
import subprocess
import sys
import tempfile
import cv2
import mediapipe as mp
import numpy as np

# ---------------------------------------------------------------------------
# Quality filter parameters (tune as needed)
# ---------------------------------------------------------------------------
SAMPLE_INTERVAL_SEC   = 5      # Extract one frame every N seconds
MIN_FACE_FRACTION     = 0.15   # Face height must be ≥ 15% of frame height
YAW_THRESHOLD_DEG     = 20     # Max horizontal head rotation (degrees)
PITCH_THRESHOLD_DEG   = 20     # Max vertical head tilt (degrees)
MSE_DEDUP_THRESHOLD   = 150    # Skip frame if MSE vs last saved < this value
                                # (lower = more aggressive dedup)
OUTPUT_RESOLUTION     = (720, 1280)  # (height, width) to resize frames to (0 = keep original)

# Landmark indices used to estimate head pose
# Using nose tip, chin, eye corners, and mouth corners
POSE_LANDMARKS = {
    "nose_tip":      1,
    "chin":          199,
    "left_eye":      33,
    "right_eye":     263,
    "left_mouth":    61,
    "right_mouth":   291,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def download_video(url: str, out_dir: str) -> str:
    """Download video using yt-dlp, return path to downloaded file."""
    print(f"[INFO] Downloading video from: {url}")
    out_template = os.path.join(out_dir, "video.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", out_template,
        "--no-playlist",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed:\n{result.stderr}")

    # Find the downloaded file
    for f in os.listdir(out_dir):
        if f.startswith("video") and f.endswith(".mp4"):
            return os.path.join(out_dir, f)

    raise FileNotFoundError("yt-dlp ran but no .mp4 file found in output dir.")


def get_face_landmarks(face_mesh, image_bgr):
    """Run MediaPipe FaceMesh and return the first face's landmarks, or None."""
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    result = face_mesh.process(rgb)
    if not result.multi_face_landmarks:
        return None
    return result.multi_face_landmarks[0]


def estimate_yaw_pitch(landmarks, img_w, img_h):
    """
    Rough yaw / pitch estimation from 2D landmark positions.
    Returns (yaw_deg, pitch_deg).
    - Yaw:   left-right rotation. 0 = frontal. Negative = face turned left.
    - Pitch: up-down tilt.        0 = level.   Negative = looking down.
    """
    def pt(idx):
        lm = landmarks.landmark[idx]
        return np.array([lm.x * img_w, lm.y * img_h])

    left_eye   = pt(POSE_LANDMARKS["left_eye"])
    right_eye  = pt(POSE_LANDMARKS["right_eye"])
    nose_tip   = pt(POSE_LANDMARKS["nose_tip"])
    chin       = pt(POSE_LANDMARKS["chin"])

    # Eye midpoint
    eye_mid = (left_eye + right_eye) / 2.0

    # Yaw: nose offset from eye midpoint (horizontal)
    eye_width   = np.linalg.norm(right_eye - left_eye) + 1e-6
    nose_offset = nose_tip[0] - eye_mid[0]
    yaw_deg     = np.degrees(np.arctan2(nose_offset, eye_width))

    # Pitch: nose offset below eye midpoint vs face height
    face_height  = np.linalg.norm(chin - eye_mid) + 1e-6
    vert_offset  = nose_tip[1] - eye_mid[1]
    pitch_deg    = np.degrees(np.arctan2(vert_offset, face_height)) - 15  # ~15° natural offset

    return yaw_deg, pitch_deg


def face_bbox_fraction(landmarks, img_w, img_h):
    """Return face height as a fraction of the frame height."""
    ys = [lm.y for lm in landmarks.landmark]
    face_h = (max(ys) - min(ys)) * img_h
    return face_h / img_h


def frame_mse(a, b):
    """Mean squared error between two same-size grayscale images."""
    a_gray = cv2.cvtColor(cv2.resize(a, (160, 90)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    b_gray = cv2.cvtColor(cv2.resize(b, (160, 90)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    return float(np.mean((a_gray - b_gray) ** 2))


# ---------------------------------------------------------------------------
# Main extraction loop
# ---------------------------------------------------------------------------

def extract_frames(video_path: str, out_dir: str, interval_sec: float) -> list:
    """
    Extract quality CEO frames from video_path.
    Returns list of saved file paths.
    """
    os.makedirs(out_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps       = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps
    step      = max(1, int(fps * interval_sec))

    print(f"[INFO] Video: {os.path.basename(video_path)}")
    print(f"[INFO] Duration: {duration_sec:.0f}s  |  FPS: {fps:.1f}  |  Sampling every {interval_sec}s ({step} frames)")

    mp_face_mesh = mp.solutions.face_mesh
    saved_frames = []
    last_saved   = None
    frame_idx    = 0
    saved_count  = 0
    skipped_no_face = 0
    skipped_angle   = 0
    skipped_small   = 0
    skipped_dedup   = 0

    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
    ) as face_mesh:

        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break

            timestamp_sec = frame_idx / fps
            img_h, img_w  = frame.shape[:2]

            # --- Face detection ---
            landmarks = get_face_landmarks(face_mesh, frame)
            if landmarks is None:
                skipped_no_face += 1
                frame_idx += step
                continue

            # --- Face size filter ---
            fraction = face_bbox_fraction(landmarks, img_w, img_h)
            if fraction < MIN_FACE_FRACTION:
                skipped_small += 1
                frame_idx += step
                continue

            # --- Head pose filter ---
            yaw, pitch = estimate_yaw_pitch(landmarks, img_w, img_h)
            if abs(yaw) > YAW_THRESHOLD_DEG or abs(pitch) > PITCH_THRESHOLD_DEG:
                skipped_angle += 1
                frame_idx += step
                continue

            # --- Deduplication ---
            if last_saved is not None and frame_mse(frame, last_saved) < MSE_DEDUP_THRESHOLD:
                skipped_dedup += 1
                frame_idx += step
                continue

            # --- Save frame ---
            fname = f"frame_{int(timestamp_sec):05d}s_yaw{yaw:+.0f}_pitch{pitch:+.0f}.jpg"
            fpath = os.path.join(out_dir, fname)

            save_frame = frame
            if OUTPUT_RESOLUTION != (0, 0):
                target_h, target_w = OUTPUT_RESOLUTION
                # Only downscale, never upscale
                if img_h > target_h or img_w > target_w:
                    save_frame = cv2.resize(frame, (target_w, target_h))

            cv2.imwrite(fpath, save_frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            saved_frames.append(fpath)
            last_saved = frame
            saved_count += 1

            frame_idx += step

    cap.release()

    print(f"\n[DONE] Saved {saved_count} frames → {out_dir}")
    print(f"       Skipped — no face: {skipped_no_face} | too small: {skipped_small} | "
          f"bad angle: {skipped_angle} | duplicate: {skipped_dedup}")

    return saved_frames


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract clean CEO face frames from earnings call videos."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url",  help="YouTube (or other) video URL")
    group.add_argument("--file", help="Path to a local video file")

    parser.add_argument("--out",      default="./ceo_frames", help="Output directory for frames (default: ./ceo_frames)")
    parser.add_argument("--interval", type=float, default=SAMPLE_INTERVAL_SEC,
                        help=f"Seconds between sampled frames (default: {SAMPLE_INTERVAL_SEC})")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    if args.url:
        tmp_dir    = tempfile.mkdtemp()
        video_path = download_video(args.url, tmp_dir)
    else:
        video_path = args.file
        if not os.path.exists(video_path):
            print(f"[ERROR] File not found: {video_path}", file=sys.stderr)
            sys.exit(1)

    saved = extract_frames(video_path, args.out, args.interval)

    if saved:
        print(f"\nNext step — score all extracted frames:")
        print(f"  for f in {args.out}/*.jpg; do python dark_circle_score.py --image \"$f\"; done")
    else:
        print("\n[WARNING] No frames passed the quality filters. Try:")
        print("  --interval 2   (sample more frequently)")
        print("  Or check that the video actually shows the CEO's face clearly.")


if __name__ == "__main__":
    main()
