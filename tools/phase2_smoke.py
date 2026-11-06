"""SLT Phase 2 Visual Perception Diagnostic and Telemetry Smoke Test."""
from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path
from time import perf_counter_ns
from typing import Any

import cv2

from slt_core.perception.geometry import compute_hand_geometry
from slt_core.perception.mediapipe_hand import (
    MediaPipeHandConfig,
    MediaPipeHandPerception,
)
from slt_core.perception.motion import MotionAnalyzer
from slt_core.perception.overlay import draw_hand_overlay
from slt_core.sources.camera import CameraSource
from slt_core.sources.video import VideoSource


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SLT Phase 2 Visual Perception and Tracking Diagnostic Tool."
    )
    parser.add_argument(
        "--source",
        choices=("camera", "video"),
        required=True,
        help="Input source type: live camera or video file.",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=0,
        help="Camera device index (default: 0).",
    )
    parser.add_argument(
        "--video",
        type=str,
        default=None,
        help="Path to input video file (required when --source=video).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="models/mediapipe/hand_landmarker.task",
        help="Path to hand_landmarker.task model artifact.",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help="Path to model manifest.json for checksum verification (optional).",
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help="Display live GUI window with captured frames.",
    )
    parser.add_argument(
        "--overlay",
        action="store_true",
        help="Render 21 anatomical landmarks and tracking overlay.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Maximum frames to process before exiting (optional).",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=30,
        help="Frames between telemetry status outputs (default: 30).",
    )
    return parser.parse_args()


def run_smoke_test() -> int:
    args = parse_args()

    # 1. Initialize Frame Source
    source: Any
    if args.source == "camera":
        print(f"[SOURCE] Opening camera index {args.camera_index}...")
        source = CameraSource(camera_index=args.camera_index)
        print(f"[SOURCE] Camera opened successfully: {source.source_id}")
    else:
        if not args.video:
            print("[ERROR] --video argument is required when --source=video.")
            return 1
        video_path = Path(args.video).resolve()
        print(f"[SOURCE] Opening video file: {video_path}...")
        source = VideoSource(file_path=video_path)
        print(f"[SOURCE] Video container opened successfully: {source.source_id}")

    # 2. Initialize Perception Engine
    model_path = Path(args.model).resolve()
    print(f"[PERCEPTION] Initializing MediaPipe Hand Landmarker with: {model_path}...")
    manifest_arg = Path(args.manifest).resolve() if args.manifest else None

    detector = MediaPipeHandPerception(
        model_path=model_path,
        config=MediaPipeHandConfig(max_hands=2),
        manifest_path=manifest_arg,
    )
    print(f"[PERCEPTION] Model verified and initialized. SHA-256: {detector.model_sha256[:16]}...")

    motion_analyzer = MotionAnalyzer()

    # Telemetry metrics
    latencies_ms: deque[float] = deque(maxlen=300)
    window_start = perf_counter_ns()
    window_frames = 0
    detected_hand_frames = 0
    total_hand_observations = 0
    total_frames = 0

    print("\n--- INICIANDO PROCESAMIENTO --- (Presiona 'Q' en la ventana para salir)")

    try:
        while True:
            packet = source.read()
            if packet is None:
                print("\n[SOURCE] Fin del flujo de fotogramas (End of Stream).")
                break

            total_frames += 1

            # Execute perception inference
            t0 = perf_counter_ns()
            perception = detector.detect(packet)
            inference_ms = (perf_counter_ns() - t0) / 1_000_000.0

            latencies_ms.append(inference_ms)
            window_frames += 1

            if perception.hands:
                detected_hand_frames += 1
                total_hand_observations += len(perception.hands)

                # Exercise geometry extraction
                for hand in perception.hands:
                    _ = compute_hand_geometry(hand)

            # Exercise motion analysis
            _ = motion_analyzer.update(perception)

            # Print telemetry periodically
            if window_frames >= args.log_every:
                elapsed_sec = (perf_counter_ns() - window_start) / 1_000_000_000.0
                fps = window_frames / elapsed_sec if elapsed_sec > 0 else 0.0
                sorted_lats = sorted(latencies_ms)
                p50 = sorted_lats[int(0.50 * (len(sorted_lats) - 1))] if sorted_lats else 0.0
                p95 = sorted_lats[int(0.95 * (len(sorted_lats) - 1))] if sorted_lats else 0.0
                hand_rate = detected_hand_frames / window_frames if window_frames > 0 else 0.0

                print(
                    f"Frame {total_frames:5d} | FPS: {fps:5.1f} | Latencia P50: {p50:5.1f} ms | "
                    f"P95: {p95:5.1f} ms | Manos: {len(perception.hands)} | "
                    f"Tasa detección: {hand_rate:5.1%}"
                )

                window_start = perf_counter_ns()
                window_frames = 0
                detected_hand_frames = 0

            # Render display if requested
            if args.display:
                if args.overlay and perception.hands:
                    display_img = draw_hand_overlay(packet.image, perception)
                else:
                    display_img = packet.image

                cv2.imshow("SLT Phase 2 Smoke Test", display_img)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:  # 'q' or ESC
                    print("\n[USER] Salida solicitada por el usuario.")
                    break

            if args.max_frames and total_frames >= args.max_frames:
                print(f"\n[INFO] Límite de {args.max_frames} fotogramas alcanzado.")
                break

    finally:
        source.close()
        detector.close()
        if args.display:
            cv2.destroyAllWindows()

    print("\n--- RESUMEN FINAL ---")
    print(f"Total fotogramas procesados: {total_frames}")
    print(f"Total observaciones de manos: {total_hand_observations}")
    if latencies_ms:
        sorted_all = sorted(latencies_ms)
        p50_total = sorted_all[int(0.50 * (len(sorted_all) - 1))]
        p95_total = sorted_all[int(0.95 * (len(sorted_all) - 1))]
        print(f"Latencia global P50: {p50_total:.2f} ms | P95: {p95_total:.2f} ms")
    print("Recursos liberados correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_smoke_test())
