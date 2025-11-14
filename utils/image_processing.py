"""Image quality assessment utilities.

This module provides functions for image quality analysis including:
- Blur detection using Laplacian variance
- Resolution validation
- Image cropping detection
- File format validation
"""

import cv2
import numpy as np
import os
import uuid
