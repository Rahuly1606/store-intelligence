"""
Staff classification module.

Uses a simple colour heuristic on the upper body region to detect
staff uniforms. Configured via the pipeline config YAML.
"""

import logging
from typing import List

import cv2
import numpy as np

logger = logging.getLogger("staff")


class StaffClassifier:
    """
    Classifies a person as staff based on uniform colour.

    Parameters
    ----------
    color_lower : list of int
        HSV lower bound (3 values).
    color_upper : list of int
        HSV upper bound (3 values).
    threshold : float
        Fraction of upper‑body pixels that must match the colour range.
    """

    def __init__(
        self,
        color_lower: List[int],
        color_upper: List[int],
        threshold: float = 0.3,
    ) -> None:
        self.lower = np.array(color_lower, dtype=np.uint8)
        self.upper = np.array(color_upper, dtype=np.uint8)
        self.threshold = threshold

    def is_staff(self, frame: np.ndarray, bbox: List[int]) -> bool:
        """
        Returns True if the person in the bounding box is staff.

        Parameters
        ----------
        frame : np.ndarray
            BGR image.
        bbox : list of int
            [x1, y1, x2, y2].

        Returns
        -------
        bool
        """
        x1, y1, x2, y2 = bbox
        # Crop the upper third of the bounding box
        crop = frame[y1: y1 + (y2 - y1) // 3, x1:x2]
        if crop.size == 0:
            return False

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower, self.upper)
        ratio = np.count_nonzero(mask) / mask.size
        return ratio >= self.threshold