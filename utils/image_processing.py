"""Image quality assessment utilities.

This module provides functions for image quality analysis including:
- Blur detection using Laplacian variance
- Resolution validation
- Image cropping detection
- File format validation
"""

import os
import uuid
from typing import Any, Dict

import cv2
import numpy as np


def detect_blur(image_path: str, threshold: float = 100.0) -> Dict[str, Any]:
    """Detect blur in an image using Laplacian variance.

    Args:
        image_path: Path to the image file
        threshold: Variance threshold below which image is considered blurry (default: 100.0)

    Returns:
        Dictionary containing:
            - is_blurry (bool): True if image is blurry
            - blur_score (float): Laplacian variance score (higher = sharper)
            - threshold (float): Threshold used for classification

    Raises:
        FileNotFoundError: If image file doesn't exist
        ValueError: If image cannot be read or is invalid
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Failed to read image: {image_path}")

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Calculate Laplacian variance
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    blur_score = float(laplacian.var())

    # Classify as blurry if below threshold
    is_blurry = blur_score < threshold

    return {"is_blurry": is_blurry, "blur_score": blur_score, "threshold": threshold}


def check_resolution(
    image_path: str, min_width: int = 800, min_height: int = 600, max_size_mb: float = 50
) -> Dict[str, Any]:
    """Check image resolution and file size.

    Args:
        image_path: Path to the image file
        min_width: Minimum acceptable width in pixels (default: 800)
        min_height: Minimum acceptable height in pixels (default: 600)
        max_size_mb: Maximum file size in MB (default: 50)

    Returns:
        Dictionary containing:
            - width (int): Image width in pixels
            - height (int): Image height in pixels
            - aspect_ratio (float): Width/height ratio
            - file_size_mb (float): File size in megabytes
            - meets_minimum (bool): True if meets minimum resolution
            - too_large (bool): True if exceeds maximum file size
            - is_valid (bool): True if all constraints satisfied

    Raises:
        FileNotFoundError: If image file doesn't exist
        ValueError: If image cannot be read or is invalid
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Check file size
    file_size_bytes = os.path.getsize(image_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    too_large = file_size_mb > max_size_mb

    # Load image and get dimensions
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Failed to read image: {image_path}")

    height, width = image.shape[:2]
    aspect_ratio = width / height if height > 0 else 0.0

    # Check if meets minimum resolution
    meets_minimum = width >= min_width and height >= min_height

    # Overall validity check
    is_valid = meets_minimum and not too_large

    return {
        "width": width,
        "height": height,
        "aspect_ratio": round(aspect_ratio, 2),
        "file_size_mb": round(file_size_mb, 2),
        "meets_minimum": meets_minimum,
        "too_large": too_large,
        "is_valid": is_valid,
    }


def check_completeness(image_path: str, border_size: int = 20, edge_threshold: int = 50) -> Dict[str, Any]:
    """Check if image appears cropped or incomplete using edge detection.

    Args:
        image_path: Path to the image file
        border_size: Size of border region to analyze in pixels (default: 20)
        edge_threshold: Threshold for Canny edge detection (default: 50)

    Returns:
        Dictionary containing:
            - edge_density (dict): Edge density percentage for each border
            - avg_edge_density (float): Average edge density across all borders
            - max_edge_density (float): Maximum edge density (most problematic border)
            - likely_cropped (bool): True if high edge density at borders
            - likely_incomplete (bool): True if uniform borders detected

    Raises:
        FileNotFoundError: If image file doesn't exist
        ValueError: If image cannot be read or is invalid
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Failed to read image: {image_path}")

    # Convert to grayscale and apply Canny edge detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, edge_threshold, edge_threshold * 2)

    height, width = edges.shape

    # Calculate edge density in each border region
    # Top border
    top_border = edges[:border_size, :]
    top_density = (np.count_nonzero(top_border) / top_border.size) * 100

    # Bottom border
    bottom_border = edges[-border_size:, :]
    bottom_density = (np.count_nonzero(bottom_border) / bottom_border.size) * 100

    # Left border
    left_border = edges[:, :border_size]
    left_density = (np.count_nonzero(left_border) / left_border.size) * 100

    # Right border
    right_border = edges[:, -border_size:]
    right_density = (np.count_nonzero(right_border) / right_border.size) * 100

    edge_density = {
        "top": round(top_density, 2),
        "bottom": round(bottom_density, 2),
        "left": round(left_density, 2),
        "right": round(right_density, 2),
    }

    # Calculate statistics
    densities = [top_density, bottom_density, left_density, right_density]
    avg_edge_density = sum(densities) / len(densities)
    max_edge_density = max(densities)

    # Heuristic: High edge density (>30%) at borders suggests incomplete capture
    likely_cropped = max_edge_density > 30.0

    # Check for uniform borders (all white or all black = incomplete)
    top_uniform = np.std(gray[:border_size, :]) < 5
    bottom_uniform = np.std(gray[-border_size:, :]) < 5
    left_uniform = np.std(gray[:, :border_size]) < 5
    right_uniform = np.std(gray[:, -border_size:]) < 5

    likely_incomplete = any([top_uniform, bottom_uniform, left_uniform, right_uniform])

    return {
        "edge_density": edge_density,
        "avg_edge_density": round(avg_edge_density, 2),
        "max_edge_density": round(max_edge_density, 2),
        "likely_cropped": likely_cropped,
        "likely_incomplete": likely_incomplete,
    }


class ScreenshotQualityChecker:
    """Unified image quality assessment combining blur, resolution, and completeness checks."""

    def __init__(
        self,
        blur_threshold: float = 100.0,
        min_width: int = 800,
        min_height: int = 600,
        max_size_mb: float = 50,
        border_size: int = 20,
        edge_threshold: int = 50,
    ):
        """Initialize quality checker with thresholds.

        Args:
            blur_threshold: Laplacian variance threshold for blur detection
            min_width: Minimum acceptable width in pixels
            min_height: Minimum acceptable height in pixels
            max_size_mb: Maximum file size in MB
            border_size: Border region size for completeness check
            edge_threshold: Edge detection threshold for completeness check
        """
        self.blur_threshold = blur_threshold
        self.min_width = min_width
        self.min_height = min_height
        self.max_size_mb = max_size_mb
        self.border_size = border_size
        self.edge_threshold = edge_threshold

    def assess_quality(self, image_path: str) -> Dict[str, Any]:
        """Perform comprehensive quality assessment on an image.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary containing:
                - overall_quality (str): excellent, good, poor, or rejected
                - passes_quality_check (bool): True if meets quality standards
                - blur_assessment (dict): Results from detect_blur()
                - resolution_assessment (dict): Results from check_resolution()
                - completeness_assessment (dict): Results from check_completeness()
                - issues (list): List of quality issues found
                - assessment_duration_ms (int): Processing time in milliseconds

        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If image cannot be read or is invalid
        """
        import time

        start_time = time.time()

        # Run all quality checks
        blur_results = detect_blur(image_path, threshold=self.blur_threshold)
        resolution_results = check_resolution(
            image_path, min_width=self.min_width, min_height=self.min_height, max_size_mb=self.max_size_mb
        )
        completeness_results = check_completeness(
            image_path, border_size=self.border_size, edge_threshold=self.edge_threshold
        )

        # Collect issues
        issues = []

        # Blur issues
        if blur_results["is_blurry"]:
            issues.append(
                f"Image is blurry (score: {blur_results['blur_score']:.2f}, " f"threshold: {blur_results['threshold']})"
            )

        # Resolution issues
        if not resolution_results["meets_minimum"]:
            issues.append(
                f"Resolution too low ({resolution_results['width']}x{resolution_results['height']}, "
                f"minimum: {self.min_width}x{self.min_height})"
            )

        if resolution_results["too_large"]:
            issues.append(
                f"File size too large ({resolution_results['file_size_mb']}MB, " f"maximum: {self.max_size_mb}MB)"
            )

        # Completeness issues
        if completeness_results["likely_cropped"]:
            max_border = max(completeness_results["edge_density"].items(), key=lambda x: x[1])
            issues.append(f"Image appears cropped ({max_border[0]} border has {max_border[1]:.1f}% edge density)")

        if completeness_results["likely_incomplete"]:
            issues.append("Image has uniform borders suggesting incomplete capture")

        # Determine overall quality
        critical_issues = [resolution_results["too_large"], blur_results["blur_score"] < 50]  # Very blurry

        moderate_issues = [
            blur_results["is_blurry"],
            not resolution_results["meets_minimum"],
            completeness_results["likely_cropped"],
            completeness_results["likely_incomplete"],
        ]

        if any(critical_issues):
            overall_quality = "rejected"
            passes_quality_check = False
        elif len([i for i in moderate_issues if i]) >= 3:
            overall_quality = "poor"
            passes_quality_check = False
        elif len([i for i in moderate_issues if i]) >= 1:
            overall_quality = "good"
            passes_quality_check = True
        else:
            overall_quality = "excellent"
            passes_quality_check = True

        # Calculate processing time
        duration_ms = int((time.time() - start_time) * 1000)

        return {
            "overall_quality": overall_quality,
            "passes_quality_check": passes_quality_check,
            "blur_assessment": blur_results,
            "resolution_assessment": resolution_results,
            "completeness_assessment": completeness_results,
            "issues": issues,
            "assessment_duration_ms": duration_ms,
        }
