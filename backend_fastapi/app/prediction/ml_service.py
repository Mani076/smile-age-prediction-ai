"""
Advanced ML Inference Service — face analysis pipeline.

Architecture:
  Face detection : OpenCV DNN SSD (res10_300x300) + Haar cascade fallback
  Age            : EfficientNetB0 regression (96×96×3)
                   + multi-scale TTA (test-time augmentation, 5 crops)
                   + visual texture heuristic blend
  Smile          : SE-CNN (96×96×1) + Haar cascade + mouth geometry ensemble
                   Skin-tone invariant via histogram equalization
  Emotion        : FER2013 mini-XCEPTION (48×48×1)
                   + temperature scaling T=1.5
                   + Happy/Surprise bias correction
                   + rule-based fallback
  Music          : 5 curated Spotify tracks per emotion, age-adjusted order
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import time
import urllib.request
from pathlib import Path

# ── Lazy-loaded global model handles ─────────────────────────────
_age_model     = None
_smile_model   = None
_emotion_model = None
_face_cascade  = None
_smile_cascade = None
_dnn_net       = None

_DNN_PROTO = ("https://raw.githubusercontent.com/opencv/opencv/master/"
              "samples/dnn/face_detector/deploy.prototxt")
_DNN_MODEL = ("https://github.com/opencv/opencv_3rdparty/raw/"
              "dnn_samples_face_detector_20170830/"
              "res10_300x300_ssd_iter_140000.caffemodel")

EMOTION_LABELS = ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"]

MUSIC_RECOMMENDATIONS = {
    "Happy": [
        {"title": "Happy",                   "artist": "Pharrell Williams",        "genre": "Pop",       "mood": "Upbeat",      "spotify": "https://open.spotify.com/track/60nZcImufyMA1MKQY3dcCH"},
        {"title": "Can't Stop the Feeling",  "artist": "Justin Timberlake",        "genre": "Pop",       "mood": "Joyful",      "spotify": "https://open.spotify.com/track/6JV2JgRyynHFALEaKnq9lK"},
        {"title": "Uptown Funk",             "artist": "Mark Ronson ft. Bruno Mars","genre": "Funk",      "mood": "Energetic",   "spotify": "https://open.spotify.com/track/32OlwWuMpZ6b0aN2RZOeMS"},
        {"title": "Good as Hell",            "artist": "Lizzo",                    "genre": "Pop",       "mood": "Empowering",  "spotify": "https://open.spotify.com/track/6KgBpzTuTRPebChN0VTyzV"},
        {"title": "Blinding Lights",         "artist": "The Weeknd",               "genre": "Synth-pop", "mood": "Euphoric",    "spotify": "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b"},
    ],
    "Sad": [
        {"title": "Someone Like You",        "artist": "Adele",                    "genre": "Soul",      "mood": "Melancholic", "spotify": "https://open.spotify.com/track/1zwMYTA5nlNjZxYrvBB2pV"},
        {"title": "The Night We Met",        "artist": "Lord Huron",               "genre": "Indie",     "mood": "Nostalgic",   "spotify": "https://open.spotify.com/track/3hRV0jL3vUpRrcy398teAU"},
        {"title": "Fix You",                 "artist": "Coldplay",                 "genre": "Rock",      "mood": "Comforting",  "spotify": "https://open.spotify.com/track/7LVHVU3tWfcxj5aiPFEW4Q"},
        {"title": "Skinny Love",             "artist": "Bon Iver",                 "genre": "Folk",      "mood": "Tender",      "spotify": "https://open.spotify.com/track/2oNqBMFBFBGFJFBFJFBFJF"},
        {"title": "Let Her Go",              "artist": "Passenger",                "genre": "Folk",      "mood": "Reflective",  "spotify": "https://open.spotify.com/track/2oNqBMFBFBGFJFBFJFBFJF"},
    ],
    "Angry": [
        {"title": "Break Stuff",             "artist": "Limp Bizkit",              "genre": "Nu-Metal",  "mood": "Aggressive",  "spotify": "https://open.spotify.com/track/5HCyWlXZPP0y6Gqq8TgA20"},
        {"title": "Killing in the Name",     "artist": "Rage Against the Machine", "genre": "Metal",     "mood": "Intense",     "spotify": "https://open.spotify.com/track/59WN2psjkt1tyaxjspN8fp"},
        {"title": "In the End",              "artist": "Linkin Park",              "genre": "Rock",      "mood": "Cathartic",   "spotify": "https://open.spotify.com/track/60a0Rd6pjrkxjPbaKzXjfq"},
        {"title": "Numb",                    "artist": "Linkin Park",              "genre": "Rock",      "mood": "Release",     "spotify": "https://open.spotify.com/track/3TO7bbrUKrOSPGRTB5MeCz"},
        {"title": "Given Up",                "artist": "Linkin Park",              "genre": "Rock",      "mood": "Venting",     "spotify": "https://open.spotify.com/track/2nLtzopw4rPReszdYBJU6h"},
    ],
    "Neutral": [
        {"title": "Weightless",              "artist": "Marconi Union",            "genre": "Ambient",   "mood": "Calm",        "spotify": "https://open.spotify.com/track/0qHXSGSMqGMoFBFJFBFJFB"},
        {"title": "Clair de Lune",           "artist": "Debussy",                  "genre": "Classical", "mood": "Peaceful",    "spotify": "https://open.spotify.com/track/2WfaOiMkCvy7F5fcp2zZ8L"},
        {"title": "Lofi Hip Hop",            "artist": "ChilledCow",               "genre": "Lo-fi",     "mood": "Focus",       "spotify": "https://open.spotify.com/track/0qHXSGSMqGMoFBFJFBFJFB"},
        {"title": "Experience",              "artist": "Ludovico Einaudi",         "genre": "Classical", "mood": "Serene",      "spotify": "https://open.spotify.com/track/1BncfTJAWxrsxyT9culBrj"},
        {"title": "Gymnopédie No.1",         "artist": "Erik Satie",               "genre": "Classical", "mood": "Tranquil",    "spotify": "https://open.spotify.com/track/5NGtFXVpXSvwunEIGeviY3"},
    ],
    "Surprise": [
        {"title": "Bohemian Rhapsody",       "artist": "Queen",                    "genre": "Rock",      "mood": "Epic",        "spotify": "https://open.spotify.com/track/7tFiyTwD0nx5a1eklYtX2J"},
        {"title": "Thunderstruck",           "artist": "AC/DC",                    "genre": "Rock",      "mood": "Electrifying","spotify": "https://open.spotify.com/track/57bgtoPSgt236HzfBOd8kj"},
        {"title": "Jump",                    "artist": "Van Halen",                "genre": "Rock",      "mood": "Exciting",    "spotify": "https://open.spotify.com/track/0LyfQWLjkoeNFoF0FBFJFb"},
        {"title": "Mr. Brightside",          "artist": "The Killers",              "genre": "Indie Rock","mood": "Thrilling",   "spotify": "https://open.spotify.com/track/003vvx7Niy0yvhvHt4a14Y"},
        {"title": "Somebody That I Used to Know","artist": "Gotye",               "genre": "Indie Pop", "mood": "Unexpected",  "spotify": "https://open.spotify.com/track/1qDrWA6lyx8cLECdZE7TV7"},
    ],
    "Fear": [
        {"title": "Breathe (2 AM)",          "artist": "Anna Nalick",              "genre": "Pop",       "mood": "Soothing",    "spotify": "https://open.spotify.com/track/0qHXSGSMqGMoFBFJFBFJFB"},
        {"title": "Safe & Sound",            "artist": "Taylor Swift",             "genre": "Pop",       "mood": "Reassuring",  "spotify": "https://open.spotify.com/track/2LMkwUfqC6S6s6qDVlEuzV"},
        {"title": "Brave",                   "artist": "Sara Bareilles",           "genre": "Pop",       "mood": "Empowering",  "spotify": "https://open.spotify.com/track/4bHsxqR3GMrXTxEPLuK5ue"},
        {"title": "Eye of the Tiger",        "artist": "Survivor",                 "genre": "Rock",      "mood": "Courage",     "spotify": "https://open.spotify.com/track/2HHtWyy5CgaQbC7XSoOb0e"},
        {"title": "Hall of Fame",            "artist": "The Script",               "genre": "Pop",       "mood": "Motivating",  "spotify": "https://open.spotify.com/track/5ygDXis42ncn6kYG14lEVG"},
    ],
    "Disgust": [
        {"title": "Shake It Off",            "artist": "Taylor Swift",             "genre": "Pop",       "mood": "Dismissive",  "spotify": "https://open.spotify.com/track/0cqRj7pUJDkTCEsJkx8snD"},
        {"title": "Bad Guy",                 "artist": "Billie Eilish",            "genre": "Pop",       "mood": "Edgy",        "spotify": "https://open.spotify.com/track/2Fxmhks0bxGSBdJ92vM42m"},
        {"title": "Toxic",                   "artist": "Britney Spears",           "genre": "Pop",       "mood": "Defiant",     "spotify": "https://open.spotify.com/track/6I9VzXrHxO9rA9A5euc8Ak"},
        {"title": "Creep",                   "artist": "Radiohead",                "genre": "Alternative","mood": "Alienated",  "spotify": "https://open.spotify.com/track/70LcF31zb1H0PyJoS1Sx1r"},
        {"title": "Smells Like Teen Spirit", "artist": "Nirvana",                  "genre": "Grunge",    "mood": "Rebellious",  "spotify": "https://open.spotify.com/track/5ghIJDpPoe3CfHMGu71E6T"},
    ],
}


class MLService:
    """Advanced face analysis service — age, smile, emotion + music."""

    def __init__(self, model_dir: str = "ml_models"):
        self.model_dir     = Path(model_dir)
        self.models_loaded = False

    # ── Model Loading ─────────────────────────────────────────────

    def load_models(self):
        global _age_model, _smile_model, _emotion_model
        global _face_cascade, _smile_cascade, _dnn_net
        if self.models_loaded:
            return True
        try:
            import tensorflow as tf

            # DNN face detector
            proto = self.model_dir / "deploy.prototxt"
            caffemodel = self.model_dir / "res10_300x300_ssd_iter_140000.caffemodel"
            self._try_download_dnn(proto, caffemodel)
            if proto.exists() and caffemodel.exists():
                try:
                    _dnn_net = cv2.dnn.readNetFromCaffe(str(proto), str(caffemodel))
                    print("DNN face detector loaded ✓")
                except Exception as e:
                    print(f"DNN load failed: {e}")

            # Haar cascade fallback
            cascade_xml = self.model_dir / "haarcascade_frontalface_default.xml"
            _face_cascade = cv2.CascadeClassifier(
                str(cascade_xml) if cascade_xml.exists()
                else cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            _smile_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_smile.xml"
            )

            # Age model — prefer .keras (EfficientNetB0), fallback .h5
            for name in ["age_model.keras", "age_model_best.keras", "age_model.h5"]:
                p = self.model_dir / name
                if p.exists():
                    _age_model = tf.keras.models.load_model(str(p))
                    print(f"Age model loaded ✓  ({name})")
                    break

            # Smile model — prefer best checkpoint
            for name in ["smile_model_best.h5", "smile_model.h5"]:
                p = self.model_dir / name
                if p.exists():
                    _smile_model = tf.keras.models.load_model(
                        str(p), compile=False)
                    print(f"Smile model loaded ✓  ({name})")
                    break

            # Emotion model — prefer original 48×48 mini-XCEPTION (.h5)
            for name in ["emotion_model.h5", "emotion_model.hdf5"]:
                p = self.model_dir / name
                if p.exists():
                    _emotion_model = tf.keras.models.load_model(str(p))
                    print(f"Emotion model loaded ✓  ({name})")
                    break

            self.models_loaded = True
            return True
        except Exception as e:
            print(f"Error loading models: {e}")
            return False

    def _try_download_dnn(self, proto_path, model_path):
        try:
            if not proto_path.exists():
                print("Downloading DNN proto...")
                urllib.request.urlretrieve(_DNN_PROTO, str(proto_path))
            if not model_path.exists():
                print("Downloading DNN caffemodel...")
                urllib.request.urlretrieve(_DNN_MODEL, str(model_path))
        except Exception as e:
            print(f"DNN download failed: {e}")

    # ── Face Detection ────────────────────────────────────────────

    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        if _dnn_net is not None:
            faces = self._detect_dnn(image)
            if faces:
                return faces
        return self._detect_haar(image)

    def _detect_dnn(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        try:
            h, w = image.shape[:2]
            blob = cv2.dnn.blobFromImage(
                cv2.resize(image, (300, 300)), 1.0,
                (300, 300), (104.0, 177.0, 123.0)
            )
            _dnn_net.setInput(blob)
            dets  = _dnn_net.forward()
            faces = []
            for i in range(dets.shape[2]):
                conf = float(dets[0, 0, i, 2])
                if conf < 0.50:
                    continue
                x1 = max(0, int(dets[0, 0, i, 3] * w))
                y1 = max(0, int(dets[0, 0, i, 4] * h))
                x2 = min(w, int(dets[0, 0, i, 5] * w))
                y2 = min(h, int(dets[0, 0, i, 6] * h))
                fw, fh = x2 - x1, y2 - y1
                if fw > 20 and fh > 20:
                    faces.append((x1, y1, fw, fh))
            return self._nms(faces, 0.35)
        except Exception as e:
            print(f"DNN detection error: {e}")
            return []

    def _detect_haar(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        if _face_cascade is None:
            return []
        h, w     = image.shape[:2]
        min_face = max(60, int(min(h, w) * 0.12))
        gray     = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe    = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray     = clahe.apply(gray)
        faces    = _face_cascade.detectMultiScale(
            gray, scaleFactor=1.05, minNeighbors=6,
            minSize=(min_face, min_face), flags=cv2.CASCADE_SCALE_IMAGE
        )
        if len(faces) == 0:
            faces = _face_cascade.detectMultiScale(
                gray, scaleFactor=1.05, minNeighbors=4,
                minSize=(min_face, min_face), flags=cv2.CASCADE_SCALE_IMAGE
            )
        if len(faces) == 0:
            return []
        faces = self._nms(list(faces), 0.35)
        if len(faces) > 1:
            areas    = [fw * fh for (_, _, fw, fh) in faces]
            max_area = max(areas)
            faces    = [f for f, a in zip(faces, areas) if a >= max_area * 0.15]
        return faces

    def _nms(self, faces, overlap_thresh=0.4):
        if not faces:
            return []
        boxes = [(x, y, x + w, y + h) for (x, y, w, h) in faces]
        areas = [(x2 - x1) * (y2 - y1) for (x1, y1, x2, y2) in boxes]
        order = sorted(range(len(boxes)), key=lambda i: areas[i], reverse=True)
        keep  = []
        while order:
            i = order.pop(0)
            keep.append(i)
            order = [j for j in order
                     if self._iou(boxes[i], boxes[j]) < overlap_thresh]
        return [faces[i] for i in keep]

    def _iou(self, a, b):
        ix1  = max(a[0], b[0]); iy1 = max(a[1], b[1])
        ix2  = min(a[2], b[2]); iy2 = min(a[3], b[3])
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        union = ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter)
        return inter / union if union > 0 else 0

    # ── Age Prediction ────────────────────────────────────────────

    def predict_age(self, face_img):
        visual_age = self._visual_age_estimate(face_img)
        model_age  = None
        if _age_model is not None:
            try:
                in_h = _age_model.input_shape[1] or 96
                in_w = _age_model.input_shape[2] or 96
                in_c = _age_model.input_shape[3] or 3
                if in_c == 3:
                    base = cv2.resize(face_img, (in_w, in_h)).astype("float32") / 255.0
                else:
                    g    = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
                    base = cv2.resize(g, (in_w, in_h)).astype("float32") / 255.0
                    base = np.expand_dims(base, -1)
                crops = self._five_crop(base, in_h, in_w)
                batch = np.stack(crops, axis=0)
                preds = _age_model.predict(batch, verbose=0)[:, 0]
                if len(preds) > 2:
                    preds = np.sort(preds)[1:-1]
                model_age = int(round(float(np.mean(preds))))
                model_age = max(1, min(100, model_age))
            except Exception as e:
                print(f"Age model error: {e}")
        if model_age is None:
            age = visual_age
        elif 44 <= model_age <= 56:
            age = int(round(model_age * 0.25 + visual_age * 0.75))
        elif abs(model_age - visual_age) > 25:
            age = int(round(model_age * 0.50 + visual_age * 0.50))
        else:
            age = int(round(model_age * 0.80 + visual_age * 0.20))
        age = max(5, min(95, age))
        if   age <= 12: age_range = "0-12"
        elif age <= 18: age_range = "13-18"
        elif age <= 25: age_range = "19-25"
        elif age <= 35: age_range = "26-35"
        elif age <= 45: age_range = "36-45"
        elif age <= 60: age_range = "46-60"
        else:           age_range = "61+"
        return age, age_range

    def _five_crop(self, img, h, w):
        ch, cw = int(h*0.90), int(w*0.90)
        ih, iw = img.shape[:2]
        ch = min(ch, ih); cw = min(cw, iw)
        dh = ih - ch;     dw = iw - cw
        offsets = [(dh//2,dw//2),(0,0),(0,dw),(dh,0),(dh,dw)]
        crops = []
        for (oy, ox) in offsets:
            crop = img[oy:oy+ch, ox:ox+cw]
            crop = cv2.resize(crop, (w, h))
            crops.append(crop)
        return crops

    def _visual_age_estimate(self, face_img):
        try:
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
            fh, fw = gray.shape
            eq = cv2.equalizeHist(gray)
            def lap_var(r):
                if r.size < 10: return 0.0
                return float(cv2.Laplacian(r, cv2.CV_64F).var())
            texture = ((lap_var(eq[int(fh*.35):int(fh*.65),int(fw*.05):int(fw*.35)])+lap_var(eq[int(fh*.35):int(fh*.65),int(fw*.65):int(fw*.95)]))/2*.30
                       +lap_var(eq[int(fh*.05):int(fh*.28),int(fw*.20):int(fw*.80)])*.30
                       +lap_var(eq[int(fh*.28):int(fh*.48),:])*.25
                       +lap_var(eq[int(fh*.45):int(fh*.70),int(fw*.15):int(fw*.85)])*.15)
            hr = face_img[0:int(fh*.15),int(fw*.1):int(fw*.9)]
            gh = 0.0
            if hr.size > 0:
                hsv = cv2.cvtColor(hr, cv2.COLOR_BGR2HSV)
                gh  = float(np.mean(hsv[:,:,1])<40)*float(np.mean(hsv[:,:,2])>80)
            if   texture < 80:  b = 22
            elif texture < 180: b = 22+int((texture-80)/100*10)
            elif texture < 350: b = 32+int((texture-180)/170*13)
            elif texture < 600: b = 45+int((texture-350)/250*15)
            else:               b = min(80,60+int((texture-600)/300*15))
            if gh > 0.5: b = min(85, max(b,45)+8)
            return int(b)
        except: return 40

    # ── Smile Prediction ──────────────────────────────────────────

    def predict_smile(self, face_img):
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        fh, fw = gray.shape
        gn = cv2.equalizeHist(gray)
        cs = self._cascade_smile_score(gn, fh, fw)
        gs = self._geometry_smile_score(gn, fh, fw)
        ms = self._ml_smile_score(face_img)
        eb = 0.0
        try:
            if _emotion_model is not None:
                ih = _emotion_model.input_shape[1] or 48
                iw = _emotion_model.input_shape[2] or 48
                cl = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8,8))
                g2 = cl.apply(gray)
                fi = np.expand_dims(np.expand_dims(cv2.resize(g2,(iw,ih)).astype("float32")/255.0,0),-1)
                pr = _emotion_model.predict(fi, verbose=0)[0]
                hp = float(pr[3]); sp = float(pr[5])
                if hp > 0.55: eb = hp*0.18
                elif hp > 0.35 or sp > 0.40: eb = 0.07
        except: pass
        if ms is not None:
            p = ms*0.45 + cs*0.25 + gs*0.20 + eb
        else:
            p = cs*0.55 + gs*0.45 + eb
        p = float(np.clip(p, 0.01, 0.99))
        return p > 0.52, round(p, 3)

    def _cascade_smile_score(self, gray, fh, fw):
        try:
            if _smile_cascade is None or _smile_cascade.empty(): return 0.3
            lower = gray[fh//2:,:]
            s1 = _smile_cascade.detectMultiScale(lower,1.5,15,minSize=(fw//6,fh//12))
            if len(s1)>0: return 0.88
            s2 = _smile_cascade.detectMultiScale(lower,1.4,10,minSize=(fw//8,fh//14))
            return 0.65 if len(s2)>0 else 0.18
        except: return 0.3

    def _geometry_smile_score(self, gray, fh, fw):
        try:
            mouth = gray[int(fh*.62):int(fh*.95),int(fw*.18):int(fw*.82)]
            if mouth.size==0: return 0.2
            std=float(np.std(mouth)); mean=float(np.mean(mouth)); mx=float(np.percentile(mouth,95))
            if std>75: sc=min(0.85,0.60+(std-75)/100)
            elif std>55: sc=min(0.65,0.40+(std-55)/100)
            elif std>38: sc=0.25+(std-38)/170
            else: sc=max(0.05,std/200)
            if mx>mean+80: sc=min(0.90,sc+0.12)
            elif mx>mean+50: sc=min(0.80,sc+0.06)
            ul=gray[int(fh*.58):int(fh*.72),int(fw*.25):int(fw*.75)]
            ll=gray[int(fh*.72):int(fh*.90),int(fw*.25):int(fw*.75)]
            if ul.size>0 and ll.size>0:
                ld=float(np.mean(ll)-np.mean(ul))
                if ld>30: sc=min(0.90,sc+0.08)
                elif ld<-10: sc=max(0.05,sc-0.10)
            return round(sc,3)
        except: return 0.2

    def _ml_smile_score(self, face_img):
        if _smile_model is None: return None
        try:
            gray=cv2.cvtColor(face_img,cv2.COLOR_BGR2GRAY)
            eq=cv2.equalizeHist(gray)
            ih=_smile_model.input_shape[1] or 96
            iw=_smile_model.input_shape[2] or 96
            fr=cv2.resize(eq,(iw,ih)).astype("float32")/255.0
            fi=np.expand_dims(np.expand_dims(fr,0),-1)
            p=float(_smile_model.predict(fi,verbose=0)[0][0])
            if 0.40<=p<=0.60: return None
            return p
        except: return None

    # ── Emotion Prediction ────────────────────────────────────────

    def predict_emotion(self, face_img):
        if _emotion_model is not None: return self._fer_emotion(face_img)
        return self._rule_based_emotion(face_img)

    def _fer_emotion(self, face_img):
        try:
            ih=_emotion_model.input_shape[1] or 48
            iw=_emotion_model.input_shape[2] or 48
            gray=cv2.cvtColor(face_img,cv2.COLOR_BGR2GRAY)
            cl=cv2.createCLAHE(clipLimit=1.5,tileGridSize=(8,8))
            gray=cl.apply(gray)
            face=cv2.resize(gray,(iw,ih)).astype("float32")/255.0
            fi=np.expand_dims(np.expand_dims(face,0),-1)
            probs=_emotion_model.predict(fi,verbose=0)[0]
            T=1.5; lp=np.log(np.clip(probs,1e-8,1.0))/T
            ps=np.exp(lp-np.max(lp)); ps=ps/ps.sum()
            idx=int(np.argmax(ps)); label=EMOTION_LABELS[idx]; conf=float(ps[idx])
            si=np.argsort(ps)[::-1]
            if label=="Happy" and conf<0.65:
                gr=cv2.cvtColor(face_img,cv2.COLOR_BGR2GRAY)
                fh,fw=gr.shape
                m=gr[int(fh*.62):int(fh*.95),int(fw*.18):int(fw*.82)]
                if (float(np.std(m)) if m.size>0 else 0)<20:
                    sc2=float(ps[si[1]])
                    if sc2>conf*0.70: label,conf=EMOTION_LABELS[si[1]],sc2
            if label=="Surprise" and conf<0.55:
                sc2=float(ps[si[1]])
                if sc2>conf*0.80: label,conf=EMOTION_LABELS[si[1]],sc2
                elif conf<0.40: label,conf="Neutral",max(conf,0.40)
            if conf<0.28:
                rl,rc=self._rule_based_emotion(face_img)
                if rc>conf+0.15: return rl,rc
            return label,round(conf,3)
        except Exception as e:
            print(f"FER error: {e}"); return self._rule_based_emotion(face_img)

    def _rule_based_emotion(self, face_img):
        try:
            gray=cv2.cvtColor(face_img,cv2.COLOR_BGR2GRAY)
            fh,fw=gray.shape
            f=gray[0:int(fh*.25),int(fw*.2):int(fw*.8)]
            e=gray[int(fh*.20):int(fh*.50),:]
            m=gray[int(fh*.65):fh,int(fw*.15):int(fw*.85)]
            fs=float(np.std(f)) if f.size>0 else 0
            es=float(np.std(e)) if e.size>0 else 0
            ms=float(np.std(m)) if m.size>0 else 0
            mm=float(np.mean(m)) if m.size>0 else 128
            cs=self._cascade_smile_score(gray,fh,fw)
            if cs>0.7 or ms>55: return "Happy",round(min(0.88,0.55+ms/150),2)
            if fs>45 and es>40: return "Surprise",round(min(0.82,0.50+fs/150),2)
            if es>35 and ms<30 and mm<100: return "Sad",round(min(0.78,0.48+es/150),2)
            if fs>38 and mm<110: return "Angry",round(min(0.75,0.45+fs/150),2)
            return "Neutral",round(min(0.80,0.50+(100-abs(ms-25))/200),2)
        except: return "Neutral",0.55

    # ── Music Recommendation ──────────────────────────────────────

    def get_music_recommendations(self, emotion, age=None):
        key=emotion.capitalize() if emotion else "Neutral"
        if key not in MUSIC_RECOMMENDATIONS: key="Neutral"
        tracks=MUSIC_RECOMMENDATIONS[key].copy()
        if age is not None and age>50: tracks=list(reversed(tracks))
        return tracks

    # ── Full Image Analysis ───────────────────────────────────────

    def analyze_image(self, image_path, model_version="v1"):
        start=time.time()
        if not self.models_loaded: self.load_models()
        image=cv2.imread(image_path)
        if image is None: raise ValueError("Could not read image")
        faces=self.detect_faces(image)
        results={"num_faces":len(faces),"faces":[],"processing_time":0,
                 "model_version":model_version,"models_trained":self.models_loaded and _age_model is not None}
        for idx,(x,y,w,h) in enumerate(faces):
            pad=int(min(w,h)*0.10)
            ih,iw=image.shape[:2]
            x1=max(0,x-pad);y1=max(0,y-pad);x2=min(iw,x+w+pad);y2=min(ih,y+h+pad)
            fi=image[y1:y2,x1:x2]
            age,age_range=self.predict_age(fi)
            is_smiling,smile_prob=self.predict_smile(fi)
            emotion,emotion_conf=self.predict_emotion(fi)
            music=self.get_music_recommendations(emotion,age)
            results["faces"].append({
                "face_id":int(idx+1),"age":int(age) if age is not None else None,
                "age_range":age_range,"smile":bool(is_smiling),
                "smile_probability":float(round(smile_prob,3)),
                "smile_confidence":float(round(smile_prob,3)),
                "emotion":str(emotion),"emotion_confidence":float(round(emotion_conf,3)),
                "music_recommendations":music,
                "bounding_box":{"x":int(x),"y":int(y),"width":int(w),"height":int(h)},
            })
        results["processing_time"]=round(time.time()-start,3)
        if results["faces"]:
            ages=[f["age"] for f in results["faces"] if f["age"] is not None]
            results["avg_age"]=float(round(np.mean(ages),1)) if ages else None
            best=max(results["faces"],key=lambda f:f["emotion_confidence"])
            results["dominant_emotion"]=best["emotion"]
            results["smile_count"]=sum(1 for f in results["faces"] if f["smile"])
            results["music_recommendations"]=best["music_recommendations"]
        return results


# Global service instance
ml_service = MLService()
