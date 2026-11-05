# """
# Drishti AI v2
# Assistive vision for visually impaired users.
#
# Features
#   - Real-time object detection with direction + distance alerts
#   - Press R : read text in front of the camera aloud (OCR, English + Hindi)
#   - Press S : speak a summary of everything currently visible
#   - Press M : mute / unmute automatic alerts
#   - Press Q : quit
#
# Install:
#     pip install ultralytics opencv-python pyttsx3 easyocr
# (easyocr downloads its language models on first use, so allow internet once)
# """
#
# import time
# import threading
# import queue
# from collections import Counter
#
# import cv2
# import pyttsx3
# from ultralytics import YOLO
# import easyocr
#
# # ---------- Settings ----------
# MODEL_NAME = "yolov8n.pt"
# CONFIDENCE = 0.5
# SPEAK_COOLDOWN = 4
# CAMERA_INDEX = 0
# OCR_LANGS = ["en", "hi"]       # add more, e.g. "te" for Telugu, "ta" for Tamil
#
# # ---------- Speech (own thread so the video never freezes) ----------
# speech_queue = queue.Queue()
#
#
# def speech_worker():
#     engine = pyttsx3.init()
#     engine.setProperty("rate", 165)
#     while True:
#         text = speech_queue.get()
#         if text is None:
#             break
#         engine.say(text)
#         engine.runAndWait()
#
#
# threading.Thread(target=speech_worker, daemon=True).start()
#
#
# def speak(text, force=False):
#     if force or speech_queue.qsize() < 2:
#         speech_queue.put(text)
#
#
# # ---------- Helpers ----------
# def get_direction(x_center, frame_width):
#     if x_center < frame_width / 3:
#         return "on your left"
#     if x_center > 2 * frame_width / 3:
#         return "on your right"
#     return "ahead"
#
#
# def get_distance(box_height, frame_height):
#     """Rough estimate: bigger box = closer. Replace with MiDaS for real depth."""
#     ratio = box_height / frame_height
#     if ratio > 0.6:
#         return "very close"
#     if ratio > 0.3:
#         return "near"
#     return "far"
#
#
# def summarize(detections):
#     """detections: list of (label, direction, distance)."""
#     if not detections:
#         return "I don't see anything clearly."
#     counts = Counter(label for label, _, _ in detections)
#     parts = [f"{n} {label}" if n > 1 else f"a {label}" for label, n in counts.items()]
#     return "I can see " + ", ".join(parts) + "."
#
#
# def read_text(reader, frame):
#     """Run OCR on the current frame in a background thread."""
#     def work():
#         speak("Reading text", force=True)
#         results = reader.readtext(frame, detail=0, paragraph=True)
#         text = " ".join(results).strip()
#         speak(text if text else "No readable text found", force=True)
#
#     threading.Thread(target=work, daemon=True).start()
#
#
# # ---------- Main ----------
# def main():
#     model = YOLO(MODEL_NAME)
#     reader = easyocr.Reader(OCR_LANGS, gpu=False)
#     cap = cv2.VideoCapture(CAMERA_INDEX)
#     if not cap.isOpened():
#         print("Could not open camera.")
#         return
#
#     last_spoken = {}
#     muted = False
#     speak("Drishti AI started. Press R to read text, S for summary.", force=True)
#
#     while True:
#         ok, frame = cap.read()
#         if not ok:
#             break
#
#         h, w = frame.shape[:2]
#         results = model(frame, conf=CONFIDENCE, verbose=False)[0]
#
#         detections = []
#         alerts = []
#         for box in results.boxes:
#             x1, y1, x2, y2 = map(int, box.xyxy[0])
#             label = model.names[int(box.cls[0])]
#             direction = get_direction((x1 + x2) / 2, w)
#             distance = get_distance(y2 - y1, h)
#             detections.append((label, direction, distance))
#
#             cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
#             cv2.putText(frame, f"{label} {distance}", (x1, y1 - 8),
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
#
#             if distance in ("near", "very close"):
#                 alerts.append((distance == "very close",
#                                f"{label} {distance} {direction}"))
#
#         # Automatic alerts (most urgent first)
#         if not muted:
#             alerts.sort(reverse=True)
#             now = time.time()
#             for _, msg in alerts[:2]:
#                 if now - last_spoken.get(msg, 0) > SPEAK_COOLDOWN:
#                     speak(msg)
#                     last_spoken[msg] = now
#
#         status = "MUTED" if muted else "LIVE"
#         cv2.putText(frame, f"{status} | R:read S:summary M:mute Q:quit", (10, 25),
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
#         cv2.imshow("Drishti AI v2", frame)
#
#         key = cv2.waitKey(1) & 0xFF
#         if key == ord("q"):
#             break
#         elif key == ord("r"):
#             read_text(reader, frame.copy())
#         elif key == ord("s"):
#             speak(summarize(detections), force=True)
#         elif key == ord("m"):
#             muted = not muted
#             speak("Alerts muted" if muted else "Alerts on", force=True)
#
#     cap.release()
#     cv2.destroyAllWindows()
#     speech_queue.put(None)
#
#
# if __name__ == "__main__":
#     main()