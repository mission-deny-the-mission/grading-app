# Feature Specification: Marking Schemes as Files

**Feature Branch**: `005-marking-schema-as-file`
**Created**: 2025-11-17
**Status**: Draft
**Input**: User description: "The ability to save and load marking schemes as files in a standard format. To be able to upload a marking scheme or rubric in document format and convert it to one of these standard formats that can be auto-marked by reading the document and interpreting it using an LLM model into the right format for automated marking."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Save and Export Marking Schemes to File (Priority: P1)

Educators create marking schemes within the grading application and need to save them as files so they can be reused, shared with colleagues, or archived. This enables portability and ensures marking schemes are preserved independently of the application database.

**Why this priority**: This is foundational - without the ability to export, schemes cannot be shared or persisted as portable files, making all downstream features impossible.

**Independent Test**: Can be fully tested by creating a marking scheme in the UI and exporting it to a standard file format, then verifying the file contains the complete marking scheme data.

**Acceptance Scenarios**:

1. **Given** a completed marking scheme exists in the system, **When** user selects "Export" or "Save as File", **Then** the system generates a file in a standard format (JSON) containing the complete marking scheme
2. **Given** a marking scheme has been exported, **When** the file is opened in a text editor, **Then** the structure is human-readable and follows consistent formatting
3. **Given** multiple versions of a marking scheme exist, **When** user exports them, **Then** each file can be identified by date, version number, or explicit naming

---

### User Story 2 - Load and Import Marking Schemes from File (Priority: P1)

Educators need to load previously saved marking schemes from files back into the application, either to resume work, reuse schemes across courses, or import schemes from other sources.

**Why this priority**: Equally foundational with export - together they enable the complete save/load cycle. Without loading, exported files have no purpose.

**Independent Test**: Can be fully tested by importing a previously exported marking scheme file and verifying all data is restored correctly in the application.

**Acceptance Scenarios**:

1. **Given** a marking scheme file exists, **When** user selects "Import" or "Load from File", **Then** the system reads the file and recreates the marking scheme in the application
2. **Given** an imported marking scheme, **When** it is displayed in the editor, **Then** all criteria, weightings, and descriptors match the original export
3. **Given** a file with invalid format or corrupted data, **When** user attempts to import, **Then** the system displays a clear error message explaining what is wrong

---

### User Story 3 - Upload Document-Based Rubrics and Convert to Standard Format (Priority: P2)

Educators often receive marking rubrics in document formats (PDF, Word, image) from their institution or colleagues. They need to upload these documents and have them automatically converted to a standard format that can be used for automated marking.

**Why this priority**: High value but requires document parsing and LLM interpretation - more complex than basic save/load. Enables workflow where physical/scanned rubrics are converted to digital.

**Independent Test**: Can be fully tested by uploading a document rubric and verifying the system produces a valid standard format file without manual editing required.

**Acceptance Scenarios**:

1. **Given** a user has a rubric document (PDF, DOC, or image), **When** they upload it via "Import from Document", **Then** the system accepts the file and processes it
2. **Given** a document has been uploaded, **When** the LLM analysis completes, **Then** a marking scheme in standard format is generated automatically
3. **Given** a complex multi-page rubric document, **When** it is processed, **Then** all criteria, levels, and descriptions are captured in the standard format
4. **Given** the LLM conversion is complete, **When** user reviews the result, **Then** they can edit or approve the generated scheme before saving
5. **Given** a document with ambiguous or unclear rubric information, **When** processed, **Then** the system flags uncertain conversions for user review before accepting

---

### User Story 4 - Reuse Marking Schemes Across Assignments (Priority: P2)

Once a marking scheme is saved as a file, educators want to reuse it for multiple assignments without recreating it manually. They can load the same scheme for different courses or years.

**Why this priority**: Increases efficiency and consistency - directly addresses educator productivity, but depends on save/load functionality being complete.

**Independent Test**: Can be fully tested by loading a saved scheme file to create two separate assignments and verifying both assignments use the identical criteria.

**Acceptance Scenarios**:

1. **Given** a marking scheme file has been created, **When** user imports it for a new assignment, **Then** the system creates a new assignment with the imported scheme intact
2. **Given** multiple assignments use the same scheme file, **When** the scheme is loaded into different contexts, **Then** each maintains the original scheme data without cross-contamination

---

### User Story 5 - Share Marking Schemes with Individual Users (Web Version) (Priority: P2)

Educators using the web version need to share their marking schemes with specific colleagues so they can use, adapt, or review them. Sharing should support configurable permissions so the scheme owner can control what recipients can do.

**Why this priority**: Enables collaborative marking workflows and knowledge sharing within institutions. Web-version specific to leverage multi-user capabilities.

**Independent Test**: Can be fully tested by creating a marking scheme, sharing it with a specific user with defined permissions, and verifying the recipient can access and use it according to those permissions.

**Acceptance Scenarios**:

1. **Given** a user owns a marking scheme, **When** they select "Share" and specify a recipient username/email with permissions, **Then** the recipient receives access to the scheme
2. **Given** a scheme is shared with view-only permissions, **When** the recipient accesses it, **Then** they can see and use it but cannot edit the scheme
3. **Given** a scheme is shared with editable permissions, **When** the recipient accesses it, **Then** they can modify it (either creating their own copy or editing shared version, depending on implementation)
4. **Given** a scheme owner revokes access, **When** the recipient attempts to access the scheme, **Then** access is denied and they receive a notification

---

### User Story 6 - Share Marking Schemes with Groups (Web Version) (Priority: P3)

In addition to sharing with individuals, educators need to share marking schemes with groups (departments, course teams, or custom groups) to enable efficient distribution to multiple colleagues at once and maintain consistency across teams.

**Why this priority**: Enhances team efficiency and collaboration. Depends on basic sharing being complete. Requires group management infrastructure.

**Independent Test**: Can be fully tested by sharing a marking scheme with a group and verifying all group members gain access with the specified permissions.

**Acceptance Scenarios**:

1. **Given** a user owns a marking scheme and a group exists, **When** they select "Share" and specify a group with permissions, **Then** all group members receive access to the scheme
2. **Given** a new user is added to a group that has access to shared schemes, **When** they join the group, **Then** they automatically gain access to all schemes shared with that group
3. **Given** a user is removed from a group, **When** they are removed, **Then** they lose access to schemes shared with that group (unless also shared individually)

---

### Edge Cases

- What happens when a user attempts to import a marking scheme file that is missing required fields or is corrupted?
- How does the system handle document uploads that are very large (>50MB) or in unsupported formats?
- What happens when an LLM conversion partially fails or produces ambiguous results?
- How does the system prevent duplicate or conflicting scheme imports?
- What happens if a document contains multiple rubrics or inconsistent formatting?
- What happens when a shared scheme is deleted by the owner - do recipients lose access immediately?
- How does the system handle circular sharing scenarios or permission conflicts?
- What happens when a recipient with editable permissions modifies a shared scheme - does it affect the owner's copy?

## Requirements *(mandatory)*

### Functional Requirements

**Save/Load/Document Conversion (All Versions)**

- **FR-001**: System MUST allow users to export a marking scheme to JSON file format
- **FR-002**: System MUST allow users to import a marking scheme from a JSON file and restore it into the application
- **FR-003**: System MUST validate imported marking scheme files for completeness and correct structure before accepting them
- **FR-004**: System MUST provide an "Import from Document" feature that accepts document files (PDF, Word, images)
- **FR-005**: System MUST use an LLM to analyze document-based rubrics and convert them to standard format
- **FR-006**: System MUST present the LLM-generated marking scheme to the user for review before final acceptance
- **FR-007**: System MUST allow users to manually edit a marking scheme converted from a document before saving
- **FR-008**: System MUST preserve all marking scheme components (criteria, descriptors, weightings, point values) when saving/loading
- **FR-009**: System MUST display clear error messages when import fails, indicating the specific problem (missing fields, invalid format, etc.)
- **FR-010**: System MUST support document formats including PDF, Word documents (.docx), and images (PNG, JPG)
- **FR-011**: System MUST flag ambiguous or uncertain conversions from documents for user review

**Sharing (Web Version Only)**

- **FR-012**: System MUST provide a "Share" interface allowing users to share marking schemes with specific individuals (web version only)
- **FR-013**: System MUST provide a "Share" interface allowing users to share marking schemes with groups (web version only)
- **FR-014**: System MUST support configurable sharing permissions: View-Only, Editable, and Copy
- **FR-015**: System MUST record who a scheme is shared with and what permissions were granted
- **FR-016**: System MUST display shared schemes in the recipient's scheme list with indication of sharing status and permissions
- **FR-017**: System MUST allow scheme owners to revoke access to shared schemes at any time
- **FR-018**: System MUST notify recipients when a scheme is shared with them (web version only)
- **FR-019**: System MUST prevent recipients without edit permissions from modifying a shared scheme
- **FR-020**: System MUST track modifications to shared schemes and show editing history (web version only)

### Key Entities *(include if feature involves data)*

- **MarkingScheme**: Represents a complete rubric with criteria, descriptors, point values, and weightings. Can be saved/loaded as a file. Has an owner (user) for web version sharing.
- **Criterion**: Individual grading criteria within a marking scheme (e.g., "Clarity of Expression"). Has descriptors for different performance levels.
- **Descriptor**: Text describing what a specific performance level looks like for a criterion (e.g., "Clear and well-organized" for a high level).
- **SchemeFile**: Persisted file representation of a marking scheme in JSON format.
- **DocumentUpload**: Temporary representation of a user-provided rubric document pending LLM conversion.
- **LLMConversionResult**: Output from LLM analysis of a document, containing extracted marking scheme information.
- **SchemeShare** (Web Only): Represents a sharing relationship between a marking scheme and a user or group, including permission level and sharing timestamp.
- **UserGroup** (Web Only): Represents a group of users that can be granted access to marking schemes collectively.
- **SharePermission** (Web Only): Enumeration of permission levels (View-Only, Editable, Copy) for shared schemes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

**Save/Load/Document Conversion**

- **SC-001**: Users can export a marking scheme and re-import it without any loss of data or functionality
- **SC-002**: Document-based rubrics can be converted to standard format with 85% accuracy (verified by user review)
- **SC-003**: Imported marking schemes are usable for assignment grading without manual correction required (for well-formatted documents)
- **SC-004**: System processes document uploads under 10MB in less than 30 seconds from upload to LLM result presentation
- **SC-005**: 95% of import attempts with valid standard format files succeed without errors
- **SC-006**: Educators report reduced time to set up new assignments when reusing saved schemes (target: 50% reduction vs. manual creation)

**Sharing (Web Version)**

- **SC-007**: Shared marking schemes appear in recipient's scheme list within 5 seconds of sharing
- **SC-008**: Users can share a scheme with up to 50 individual users and/or groups in a single action
- **SC-009**: Permission restrictions are enforced correctly - view-only recipients cannot modify schemes, editable recipients can make changes
- **SC-010**: Access revocation takes effect immediately - revoked users lose access within 1 second of owner's action
- **SC-011**: 90% of shared schemes are used by recipients within 7 days of sharing
- **SC-012**: Educators using group sharing report 40% reduction in time needed to distribute schemes to teams

## Assumptions

- Standard format is **JSON** for save/load functionality (human-readable, widely supported, integrates with existing Flask/Python ecosystem)
- LLM integration uses existing API provider infrastructure (from feature 002-api-provider-security)
- Document processing supports common rubric layouts; extremely complex or non-standard layouts may require manual conversion
- File storage uses local filesystem for desktop version (from feature 004-desktop-app) and database for web version
- Web version uses existing multi-user authentication system (from feature 004-optional-auth-system)
- Maximum document file size is 50MB for initial implementation
- Groups are managed separately; this feature assumes group management infrastructure exists or will be created alongside
- Sharing is web-version only; desktop version remains single-user focused
- Edit permissions for shared schemes create modifications that affect the shared version (not automatic copies)

## Dependencies

- **004-desktop-app**: Local filesystem storage capability for file import/export
- **002-api-provider-security**: LLM API integration for document analysis
- **003-structured-grading-scheme**: Existing marking scheme data model
- **004-optional-auth-system**: Multi-user authentication for web version sharing
