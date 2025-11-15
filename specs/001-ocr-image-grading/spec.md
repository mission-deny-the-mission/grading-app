# Feature Specification: OCR and Image Content Evaluation for Grading

**Feature Branch**: `001-ocr-image-grading`
**Created**: 2025-11-14
**Status**: Draft
**Input**: User description: "Support for OCR tools such as DeepSeek OCR and VLM image support to allow reading and reviewing images submitted by students. Ideally we want to be able to evaluate the quality and content of screenshots and other things provided to be marked. This needs to somehow be integrated into the marking process."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extract Text from Student Screenshot Submissions (Priority: P1)

When students submit screenshots containing text (code snippets, terminal output, error messages), instructors need to evaluate both the visual presentation and the text content within those images. The system should automatically extract text from submitted images and make it available during the grading process.

**Why this priority**: This is the core capability that enables all other image evaluation scenarios. Without text extraction, graders cannot efficiently evaluate screenshot content and must manually read/transcribe from images.

**Independent Test**: Can be fully tested by uploading a screenshot containing text (e.g., code snippet) and verifying the extracted text appears in the grading interface. Delivers immediate value by making image text searchable and evaluable.

**Acceptance Scenarios**:

1. **Given** a student has submitted a screenshot containing code, **When** a grader views the submission, **Then** the system displays the extracted text alongside the original image
2. **Given** a submission contains multiple images with text, **When** the grader opens the submission, **Then** all images are processed and text is extracted from each
3. **Given** an image with poor quality or unclear text, **When** OCR processing occurs, **Then** the system indicates confidence level of the extraction
4. **Given** a screenshot with multiple text regions (code, comments, terminal output), **When** text is extracted, **Then** the system preserves the spatial layout and context of different text regions

---

### User Story 2 - Evaluate Image Quality and Completeness (Priority: P2)

Students sometimes submit screenshots that are cropped, blurry, or don't show the required content. Graders need to quickly assess whether submitted images meet quality standards and contain all required elements before spending time on detailed evaluation.

**Why this priority**: Automates a common grading bottleneck. Manual quality checks are time-consuming, and poor submissions require re-submission cycles that delay grading.

**Independent Test**: Can be tested by submitting various image qualities (blurry, properly focused, cropped, complete) and verifying the system provides quality assessments. Delivers value by flagging problematic submissions early.

**Acceptance Scenarios**:

1. **Given** a student submits a blurry screenshot, **When** the system analyzes the image, **Then** it flags the submission with a quality warning indicating low sharpness
2. **Given** a marking scheme requires specific UI elements to be visible, **When** an image is submitted, **Then** the system detects whether expected elements are present
3. **Given** a screenshot is heavily cropped, **When** quality assessment runs, **Then** the system warns that content may be incomplete
4. **Given** multiple screenshots of varying quality, **When** displayed in the grading interface, **Then** each shows a quality indicator (high/medium/low)

---

### User Story 3 - Content-Based Automated Assessment (Priority: P3)

For certain types of submissions (terminal output, error messages, specific UI states), graders need to verify that expected content appears in screenshots. The system should be able to check for presence of specific text patterns or visual elements and apply marking criteria automatically.

**Why this priority**: Enables partial automation of repetitive grading tasks. While not essential for MVP, it significantly reduces grading time for standardized screenshot submissions.

**Independent Test**: Can be tested by defining marking criteria (e.g., "screenshot must contain text 'Server started on port 3000'") and verifying the system correctly identifies presence/absence. Delivers value by automating repetitive content checks.

**Acceptance Scenarios**:

1. **Given** a marking scheme defines required text patterns, **When** a student submits a screenshot, **Then** the system automatically checks for those patterns and applies points
2. **Given** expected UI elements are specified in criteria, **When** an image is evaluated, **Then** the system detects presence of those elements
3. **Given** a submission must show specific error messages, **When** OCR extracts text, **Then** the system matches against expected error patterns
4. **Given** partial matches or variations of expected content, **When** automated assessment runs, **Then** the system indicates confidence level and allows manual review

---

### User Story 4 - Batch Process Multiple Image Submissions (Priority: P4)

When grading assignments with multiple image submissions per student, graders need all images to be pre-processed and analyzed before starting manual review. The system should handle bulk processing efficiently without requiring graders to wait.

**Why this priority**: Performance optimization that becomes important at scale but isn't critical for initial functionality.

**Independent Test**: Can be tested by submitting an assignment with 10+ images and verifying all are processed within acceptable time. Delivers value by ensuring smooth grading workflow.

**Acceptance Scenarios**:

1. **Given** a submission contains 10 screenshots, **When** the grader opens it, **Then** all images are already processed with extracted text available
2. **Given** multiple students submit simultaneously, **When** OCR processing occurs, **Then** the system queues and processes images without blocking the grading interface
3. **Given** a large batch of submissions to grade, **When** processing begins, **Then** graders can see progress indicators for image analysis
4. **Given** some images fail to process, **When** a grader views the submission, **Then** failed images are clearly marked with error details

---

### Edge Cases

- What happens when an image contains no text (diagram, graph, hand-drawn sketch)?
- How does the system handle images with mixed languages or special characters?
- What happens when OCR processing fails or times out?
- How are very large images (high resolution screenshots) handled for processing performance?
- What happens when a student submits a non-image file (PDF, video) where image content was expected?
- How does the system handle images with overlapping text regions or complex layouts?
- What happens when extracted text contains sensitive information that shouldn't be stored?
- How are images with low contrast or unusual color schemes processed?
- What happens when the same image is submitted multiple times across different assignments?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST extract text content from submitted image files (PNG, JPG, JPEG, GIF, BMP, WebP)
- **FR-002**: System MUST preserve the original submitted image file alongside any extracted data
- **FR-003**: System MUST provide confidence scores for OCR extraction quality
- **FR-004**: System MUST detect and flag low-quality images (blur, low resolution, poor contrast)
- **FR-005**: System MUST process images asynchronously without blocking the grading interface
- **FR-006**: System MUST handle OCR processing failures gracefully and provide error information to graders
- **FR-007**: System MUST support batch processing of multiple images within a single submission
- **FR-008**: Graders MUST be able to view both original images and extracted text side-by-side
- **FR-009**: System MUST preserve spatial layout information when extracting text from multiple regions
- **FR-010**: System MUST allow marking schemes to define image content validation criteria
- **FR-011**: System MUST automatically evaluate submissions against defined image content criteria
- **FR-012**: System MUST provide manual override for automated image content assessments
- **FR-013**: System MUST indicate when images are still being processed vs. processing complete
- **FR-014**: System MUST support marking rubrics that include image quality as an assessment factor
- **FR-015**: System MUST handle images containing Latin alphabet text (English and European languages) for OCR extraction
- **FR-016**: System MUST retain extracted text and quality metrics for the same duration as the original submission
- **FR-017**: System MUST support images up to 50MB in file size

### Key Entities

- **Image Submission**: A file submitted by a student as part of an assignment, including original file, format, dimensions, and submission timestamp
- **Extracted Content**: Text and metadata extracted from an image, including OCR confidence scores, detected text regions, spatial coordinates, and processing timestamp
- **Image Quality Assessment**: Analysis results for an image including sharpness score, resolution metrics, completeness indicators, and quality warnings
- **Content Validation Criteria**: Rules defined in a marking scheme for expected image content, including required text patterns, UI elements, or visual features
- **Automated Assessment Result**: Outcome of applying content validation criteria to a submission, including matched criteria, confidence scores, and points awarded

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Graders can access extracted text from image submissions within 5 seconds of opening a submission
- **SC-002**: System accurately extracts text from screenshots with 90%+ confidence for clear, standard-quality images
- **SC-003**: 95% of images are processed and ready for grading within 30 seconds of submission
- **SC-004**: Image quality warnings reduce re-submission requests by 40% by catching poor quality submissions early
- **SC-005**: Grading time for assignments with screenshot submissions decreases by 25% through automated text extraction and quality assessment
- **SC-006**: Automated content validation correctly identifies expected patterns in 85%+ of submissions without false positives
- **SC-007**: System handles 100 concurrent image processing requests without degradation in response time
- **SC-008**: 99% of supported image formats are successfully processed without errors

## Assumptions

- OCR processing will use cloud-based or self-hosted services with API access
- Primary use case is screenshots of text content (code, terminal output, UI) rather than handwritten content
- Image submissions are primarily from desktop/laptop screenshots at standard resolutions (1920x1080 or similar)
- Processing latency of 10-30 seconds per image is acceptable for asynchronous processing
- Graders have sufficient display resolution to view original images and extracted text simultaneously
- Student submissions will contain Latin alphabet text (English and European languages) with occasional code/technical content
- OCR system will focus on Latin character recognition, not requiring support for non-Latin scripts (e.g., Chinese, Arabic, Cyrillic)
- Maximum file size of 50MB per image supports high-resolution screenshots and multi-screen captures
- Extracted text and quality data will be retained for the same duration as the submission itself, with automatic cleanup when submissions are deleted
- Manual grading workflow remains primary, with automation providing assistance rather than replacement
