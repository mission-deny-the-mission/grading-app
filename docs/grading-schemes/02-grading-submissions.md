# Grading Submissions with a Scheme

This guide explains how to apply a grading scheme to submissions and enter grades.

## Prerequisites

- A grading scheme has been created
- Submissions exist in the system

## Overview

Grading with a scheme involves:
1. Selecting a submission to grade
2. Choosing which scheme to apply
3. Evaluating each criterion
4. Saving grades (draft or final)

## Step-by-Step Grading Process

### 1. Access the Submission

Navigate to the submission you want to grade:
- From the Jobs list
- From the Batches view
- Directly via submission ID

### 2. Apply a Grading Scheme

#### Option A: From Submission View
1. Click "Apply Grading Scheme"
2. Select your scheme from the dropdown
3. Click "Begin Grading"

#### Option B: From Grading Schemes
1. Navigate to Grading Schemes
2. Find your scheme
3. Click "Grade Submissions"
4. Select the submission

### 3. The Grading Interface

You'll see:
- **Submission Info**: Student name, submission reference
- **Scheme Structure**: Questions and criteria organized hierarchically
- **Score Tracker**: Current total and percentage (updates live)
- **Form Controls**: Save Draft, Submit Final

### 4. Evaluate Each Criterion

For each criterion:

#### Enter Points Awarded
- Type the score in the points field
- Range: 0 to maximum points for that criterion
- Decimals supported (e.g., 7.5)
- **Validation**:
  - ✅ Points must be ≥ 0
  - ✅ Points must be ≤ max_points
  - ❌ Negative points not allowed
  - ❌ Points over maximum not allowed

#### Add Feedback (Optional)
- Explain the score given
- Note strengths and areas for improvement
- Examples:
  - "Excellent thesis statement - clear and arguable"
  - "Good evidence but needs more analysis connecting to thesis"
  - "Grammar issues detract from clarity"

### 5. Monitor Progress

The score tracker shows:
- **Points Earned**: Sum of all criterion scores entered
- **Total Possible**: Sum of all criterion maximum points
- **Percentage**: (Earned / Possible) × 100

Example:
```
Score: 87.5 / 100 points (87.5%)
```

### 6. Save Your Work

#### Save as Draft
- Click "Save Draft"
- Saves progress without marking complete
- Student doesn't see results yet
- Can resume grading later

#### Mark Complete
- Click "Submit Grades"
- Finalizes the grading
- Marks submission as complete
- Student can view results (if configured)

## Example Grading Session

### Scheme Structure
```
Essay Rubric Fall 2025 (100 points)

Question 1: Introduction (25 points)
├── Hook/Engagement (10 points)
├── Thesis Statement (10 points)
└── Structure (5 points)

Question 2: Body Content (50 points)
├── Evidence Quality (25 points)
├── Analysis Depth (20 points)
└── Organization (5 points)

Question 3: Conclusion (15 points)
├── Summary (7.5 points)
└── Impact (7.5 points)

Question 4: Writing Quality (10 points)
├── Grammar & Mechanics (5 points)
└── Style & Clarity (5 points)
```

### Sample Evaluation

**Student: Jane Doe**
**Submission: Essay #123**

| Criterion | Max | Awarded | Feedback |
|-----------|-----|---------|----------|
| Hook/Engagement | 10 | 8.0 | Good opening question, could be stronger |
| Thesis Statement | 10 | 9.5 | Excellent - clear and specific |
| Structure | 5 | 5.0 | Well organized roadmap |
| Evidence Quality | 25 | 22.0 | Strong sources, one citation issue |
| Analysis Depth | 20 | 18.0 | Good analysis, could go deeper on source 3 |
| Organization | 5 | 4.5 | Good flow, one awkward transition |
| Summary | 7.5 | 7.0 | Effective recap of main points |
| Impact | 7.5 | 6.5 | Good closing, could be more impactful |
| Grammar & Mechanics | 5 | 4.5 | Few minor errors |
| Style & Clarity | 5 | 5.0 | Excellent academic tone |

**Total: 90.0 / 100 (90.0%)**

## Advanced Features

### Concurrent Grading Protection

If two graders try to grade the same submission:
- First to save wins
- Second grader sees conflict notification
- Can review and re-submit if needed
- Prevents data loss from simultaneous edits

**How it works**: Optimistic locking via `evaluation_version` field

### Fractional Points

Entering fractional points:
```
- 7.5 points (allowed)
- 2.25 points (allowed)
- 0.5 points (allowed)
- -1 points (NOT allowed)
- 10.5 when max is 10 (NOT allowed)
```

### Keyboard Shortcuts (Future Enhancement)

Planned shortcuts:
- `Tab`: Move to next criterion
- `Enter`: Save and next
- `Ctrl+S`: Save draft
- `Ctrl+Enter`: Submit final

## Best Practices

### Grading Workflow

1. **Read First, Grade Second**
   - Review entire submission before scoring
   - Note initial impressions
   - Then assign specific scores

2. **Start with Obvious Criteria**
   - Grade easiest criteria first (e.g., grammar)
   - Build momentum
   - Difficult criteria last (e.g., analysis depth)

3. **Use Consistent Standards**
   - Define what each score range means
   - Apply same standards to all students
   - Reference example submissions

4. **Save Drafts Frequently**
   - Save after completing each question
   - Prevents data loss
   - Allows breaks in grading

5. **Provide Actionable Feedback**
   - Specific, not generic
   - Balanced (strengths + improvements)
   - Focused on learning

### Feedback Examples

❌ **Poor Feedback**: "Good" or "Needs work"

✅ **Better Feedback**:
- "Strong thesis statement - clearly arguable and specific. Consider adding transition to body."
- "Evidence is relevant but needs more analysis. Explain how Source 2 supports your claim."
- "Grammar issue: subject-verb agreement in paragraph 3, sentence 2."

### Managing Large Batches

When grading many submissions:

1. **Block Time**: Set aside dedicated grading blocks
2. **Batch Similar Scores**: Grade all "excellent" first, then "good", etc.
3. **Take Breaks**: Every 10 submissions, take a 5-minute break
4. **Track Progress**: Use drafts to track which are partially complete
5. **Review Outliers**: Double-check unusually high/low scores

## Troubleshooting

### Issue: "Points cannot be negative"
**Solution**: Enter 0 or higher for all criteria

### Issue: "Error saving grades"
**Possible Causes**:
- Network connection lost
- Submission locked by another grader
- Invalid point values

**Solution**:
- Check internet connection
- Verify points are within valid range
- Try saving draft first
- Contact administrator if persists

### Issue: Scheme not appearing
**Solution**:
- Verify scheme exists and is not deleted
- Check that submission has valid scheme_id
- Refresh page

### Issue: Lost progress
**Prevention**:
- Save drafts frequently
- Don't close tab during grading
- Browser may cache some data

## Next Steps

After grading submissions:
1. **Review Statistics**: See [Exporting and Analyzing Results](03-export-analysis.md)
2. **Export Data**: Download grades in CSV/JSON format
3. **Adjust Scheme**: Modify scheme for future assignments if needed

## See Also

- [Creating Schemes](01-creating-schemes.md) - How to create grading schemes
- [Exporting Results](03-export-analysis.md) - Export and analyze data
- [API Reference](04-api-reference.md) - Grading API endpoints
