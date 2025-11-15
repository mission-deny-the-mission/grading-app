# Feature Specification: Structured Grading Scheme with Multi-Point Evaluation

**Feature Branch**: `003-structured-grading-scheme`
**Created**: 2025-11-15
**Status**: Draft
**Input**: User description: "The system needs to be able to account for grading schemes that have multiple grading points and grading for each question or category in a paper. It needs to be able to produce grade and feedback that is structured and can be output in a format such as CSV, JSON, or similar."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create Multi-Point Grading Scheme (Priority: P1)

An instructor needs to create a grading scheme that defines how each question or section in a paper will be evaluated. The scheme includes multiple grading points (criteria) per question, each with specific point allocations.

**Why this priority**: This is foundational - without the ability to define grading schemes, no structured grading can occur. This is the minimum viable functionality that enables the core feature.

**Independent Test**: Can be fully tested by creating a grading scheme with multiple questions/categories, each having multiple grading criteria with point values, and verifying the scheme is saved and can be retrieved.

**Acceptance Scenarios**:

1. **Given** an instructor has access to create grading schemes, **When** they define a grading scheme with 5 questions where each question has 3 grading criteria (e.g., "Content Quality - 5 points", "Grammar - 3 points", "Structure - 2 points"), **Then** the system saves the complete scheme with all hierarchical relationships intact.

2. **Given** a grading scheme with nested criteria, **When** the instructor views the scheme, **Then** all questions, categories, and their associated grading points are displayed in a structured, easy-to-understand format.

3. **Given** a saved grading scheme, **When** the instructor edits point allocations for any criterion, **Then** the total possible points automatically recalculate and the changes are persisted.

---

### User Story 2 - Apply Grading Scheme to Student Submissions (Priority: P2)

An instructor needs to apply a pre-defined grading scheme to student submissions, evaluating each question/category against the defined criteria and providing grades and feedback for each grading point.

**Why this priority**: This builds on P1 by enabling actual grading using the defined schemes. It's independently valuable as it delivers the core grading functionality.

**Independent Test**: Can be tested by applying an existing grading scheme to a student submission, assigning points and feedback to each criterion, and verifying the evaluation is saved correctly.

**Acceptance Scenarios**:

1. **Given** a grading scheme with multiple criteria per question, **When** an instructor grades a student submission, **Then** they can assign points (up to the maximum defined) and text feedback for each individual criterion.

2. **Given** a partially completed grading session, **When** the instructor saves progress, **Then** all entered grades and feedback are preserved and can be resumed later.

3. **Given** completed grading for a submission, **When** the instructor reviews the evaluation, **Then** the system displays total points earned per question, per category, and overall, along with all feedback organized by criterion.

---

### User Story 3 - Export Grades and Feedback in Structured Formats (Priority: P3)

An instructor or administrator needs to export grading results in standardized formats (CSV, JSON) for record-keeping, analysis, or integration with learning management systems.

**Why this priority**: This enhances usability and integration but the core grading functionality works without it. It's independently valuable for reporting and data portability.

**Independent Test**: Can be tested by grading several submissions using a multi-point scheme and exporting the results in CSV and JSON formats, then verifying the exported data contains all grades, feedback, and hierarchical structure.

**Acceptance Scenarios**:

1. **Given** graded submissions with multi-point evaluations, **When** the instructor exports to CSV format, **Then** the file contains columns for student ID, question/category, criterion name, points earned, maximum points, and feedback text.

2. **Given** graded submissions with nested criteria, **When** the instructor exports to JSON format, **Then** the file preserves the hierarchical structure (questions → criteria → grades/feedback) and includes all metadata (student ID, submission date, grader, timestamps).

3. **Given** multiple submissions graded with the same scheme, **When** the instructor exports a batch report, **Then** the export includes aggregate statistics (average score per criterion, per question, overall) alongside individual submission details.

---

### Edge Cases

- What happens when a grading scheme is modified after submissions have already been graded using the original scheme? (Should maintain version history or flag affected submissions)
- How does the system handle fractional points or partial credit within a criterion (e.g., 2.5 out of 5 points)?
- What happens when exporting very large datasets (e.g., 1000+ students with 50+ criteria each) - are there file size or performance limitations?
- How does the system handle missing or incomplete grades (e.g., instructor only graded 3 out of 5 questions) during export?
- What happens if two instructors attempt to grade the same submission simultaneously with different grading schemes?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow creation of grading schemes that contain multiple questions or categories
- **FR-002**: System MUST support multiple grading criteria (grading points) per question/category, each with a defined maximum point value
- **FR-003**: System MUST support hierarchical organization of grading components (scheme → questions/categories → criteria)
- **FR-004**: System MUST calculate and display total possible points for each question/category and for the overall grading scheme
- **FR-005**: System MUST allow instructors to assign points (from 0 to maximum) for each criterion when grading a submission
- **FR-006**: System MUST allow instructors to provide text feedback for each individual grading criterion
- **FR-007**: System MUST automatically calculate total points earned per question, per category, and overall for each graded submission
- **FR-008**: System MUST persist all grading data including points and feedback for each criterion
- **FR-009**: System MUST support export of grading results in CSV format with columns for student, question/category, criterion, points, and feedback
- **FR-010**: System MUST support export of grading results in JSON format preserving hierarchical structure
- **FR-011**: System MUST support fractional point values (e.g., 2.5 out of 5 points) for partial credit
- **FR-012**: System MUST prevent assignment of points exceeding the defined maximum for any criterion
- **FR-013**: System MUST support saving partially completed grading sessions for later continuation
- **FR-014**: System MUST associate each graded submission with the specific version of the grading scheme used
- **FR-015**: Exported data MUST include metadata (student identifiers, timestamps, grader information, scheme version)

### Key Entities

- **Grading Scheme**: Represents a reusable template defining how papers should be evaluated. Contains a name, description, creation/modification timestamps, and a collection of questions/categories. Tracks total possible points across all components.

- **Question/Category**: A major section within a grading scheme (e.g., "Question 1", "Grammar Section", "Methodology"). Contains a title, optional description, display order, and a collection of grading criteria. Has a calculated total possible points from its criteria.

- **Grading Criterion**: An individual evaluation point within a question/category (e.g., "Argument Clarity - 10 points", "Citation Quality - 5 points"). Contains a name, description, maximum point value, and belongs to exactly one question/category.

- **Graded Submission**: Represents a student's work that has been evaluated. Links to a specific grading scheme version, student identifier, grader identifier, submission timestamp, grading timestamp, and contains a collection of criterion evaluations.

- **Criterion Evaluation**: The actual grade and feedback for one criterion on one submission. Contains points awarded (0 to maximum), optional text feedback, and links to both the grading criterion and the graded submission.

- **Export Configuration**: Settings for generating structured output. Includes format type (CSV, JSON), fields to include, filtering options, and aggregation preferences.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Instructors can create a complete grading scheme with at least 10 questions and 3 criteria per question in under 15 minutes
- **SC-002**: Instructors can grade a single submission using a multi-point scheme (20+ criteria) in under 10 minutes including all feedback
- **SC-003**: System successfully exports grading data for 100+ students with 50+ criteria each in under 30 seconds
- **SC-004**: Exported CSV and JSON files maintain 100% data accuracy (all points and feedback preserved) when re-imported or validated
- **SC-005**: 95% of grading sessions can be saved and resumed without data loss
- **SC-006**: Point calculations (totals per question, per category, overall) are accurate to 2 decimal places for 100% of submissions
- **SC-007**: Grading schemes with 50+ criteria can be created, modified, and applied without system performance degradation (operations complete in under 3 seconds)

## Assumptions

- The system already has a concept of "submissions" or "student work" that can be graded
- User authentication and authorization are handled by existing systems
- The system supports standard numerical grading (not letter grades, though conversion could be added later)
- Grading schemes are typically reused across multiple submissions (not one-off)
- Default export encoding is UTF-8 for international character support
- Standard decimal precision (2 decimal places) is sufficient for point calculations
- Grading is performed by authenticated users (instructors/TAs) with appropriate permissions
- The system handles timezone conversions for timestamps in exports
