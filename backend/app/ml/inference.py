"""ML inference module for CarePulse. Fallback-safe."""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

FALLBACK_PROBS = {"LOW": 0.34, "MODERATE": 0.33, "HIGH": 0.33}
CLASS_NAMES = ["LOW", "MODERATE", "HIGH"]


class MLInference:
    def __init__(self):
        self._model = None
        self._ready = False
        self.model_version: str = "none"

    def load_model(self, path: str) -> bool:
        """Load model from joblib file. Returns True if successful."""
        try:
            import joblib
            if not os.path.exists(path):
                logger.warning("ml.model_not_found", path=path)
                return False
            self._model = joblib.load(path)
            self._ready = True
            self.model_version = os.path.basename(path).replace(".joblib", "")
            logger.info("ml.model_loaded", path=path, version=self.model_version)
            return True
        except Exception as exc:
            logger.error("ml.model_load_failed", error=str(exc), path=path)
            self._model = None
            self._ready = False
            return False

    def is_ready(self) -> bool:
        return self._ready and self._model is not None

    def predict(self, features: np.ndarray) -> dict:
        """Predict risk class. Returns fallback on any error."""
        if not self.is_ready():
            return {
                "probabilities": FALLBACK_PROBS.copy(),
                "predicted_class": None,
                "confidence": 0.50,
                "status": "fallback",
            }

        try:
            # Handle 1D input
            if features.ndim == 1:
                features = features.reshape(1, -1)

            # Replace NaN/inf
            features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)

            proba = self._model.predict_proba(features)[0]
            classes = self._model.classes_
            class_probs = {str(c): float(p) for c, p in zip(classes, proba)}

            # Ensure all classes present
            for cls in CLASS_NAMES:
                if cls not in class_probs:
                    class_probs[cls] = 0.0

            predicted_class = max(class_probs, key=class_probs.get)
            confidence = class_probs[predicted_class]

            return {
                "probabilities": class_probs,
                "predicted_class": predicted_class,
                "confidence": confidence,
                "status": "ready",
            }
        except Exception as exc:
            logger.error("ml.predict_failed", error=str(exc))
            return {
                "probabilities": FALLBACK_PROBS.copy(),
                "predicted_class": None,
                "confidence": 0.50,
                "status": "fallback",
            }


# Singleton
ml_inference = MLInference()
