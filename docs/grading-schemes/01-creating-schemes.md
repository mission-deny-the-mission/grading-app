# Creating a Grading Scheme

This guide walks you through creating a structured grading scheme from scratch.

## Prerequisites

- Access to the grading app
- Understanding of your grading rubric requirements

## Step-by-Step Guide

### 1. Navigate to Grading Schemes

From the main navigation bar, click **Grading Schemes**.

### 2. Click "Create Scheme"

You'll see a button labeled **+ Create Scheme** in the top right corner.

### 3. Fill in Scheme Details

#### Scheme Name (Required)
- **Purpose**: Unique identifier for your rubric
- **Example**: "ENGL101 Essay Rubric Fall 2025"
- **Tips**:
  - Include course code, assignment type, and semester
  - Must be unique across all schemes
  - Use descriptive names for easy searching

#### Description (Optional)
- **Purpose**: Additional context about the scheme
- **Example**: "Rubric for argumentative essay assignments covering thesis, evidence, and conclusion"
- **Tips**:
  - Explain what assignments this scheme is for
  - Note any special grading considerations

#### Category (Optional)
- **Purpose**: Group related schemes
- **Example**: "Essays", "Projects", "Exams"
- **Tips**:
  - Use consistent categories for filtering
  - Makes schemes easier to find later

### 4. Add Questions

Questions are the main sections of your rubric (e.g., "Introduction", "Body", "Conclusion").

#### Click "Add Question"

This adds a new question card to your scheme.

#### Fill in Question Details

**Question Title** (Required)
- Short, descriptive name
- Example: "Introduction"

**Description** (Optional)
- What you're evaluating in this section
- Example: "Hook, thesis statement, and roadmap"

**Points**
- Auto-calculated from criteria
- You don't enter this directly

### 5. Add Criteria to Questions

Criteria are specific evaluation points within each question.

#### Click "Add Criterion" within a question

#### Fill in Criterion Details

**Criterion Name** (Required)
- Specific aspect being evaluated
- Example: "Thesis Statement"

**Description** (Optional)
- What constitutes good performance
- Example: "Clear, arguable claim that previews main points"

**Max Points** (Required)
- Maximum points for this criterion
- Must be greater than 0
- Supports decimals (e.g., 2.5)
- Example: 10

### 6. Build Your Complete Rubric

Continue adding questions and criteria until your rubric is complete.

#### Example Structure

```
Scheme: "ENGL101 Essay Rubric Fall 2025" (100 points total)

Question 1: "Introduction" (25 points)
├── Criterion: "Hook/Engagement" (10 points)
│   Description: "Compelling opening that draws reader in"
├── Criterion: "Thesis Statement" (10 points)
│   Description: "Clear, arguable claim that previews main points"
└── Criterion: "Structure" (5 points)
    Description: "Logical organization and roadmap"

Question 2: "Body Content" (50 points)
├── Criterion: "Evidence Quality" (25 points)
│   Description: "Relevant, credible sources properly cited"
├── Criterion: "Analysis Depth" (20 points)
│   Description: "Thorough explanation connecting evidence to thesis"
└── Criterion: "Organization" (5 points)
    Description: "Clear topic sentences and transitions"

Question 3: "Conclusion" (15 points)
├── Criterion: "Summary" (7.5 points)
│   Description: "Effective recap of main points"
└── Criterion: "Impact" (7.5 points)
    Description: "Broader implications or call to action"

Question 4: "Writing Quality" (10 points)
├── Criterion: "Grammar & Mechanics" (5 points)
│   Description: "Correct grammar, punctuation, spelling"
└── Criterion: "Style & Clarity" (5 points)
    Description: "Clear, concise, appropriate academic tone"
```

Total: 100 points (automatically calculated)

### 7. Review Your Scheme

Before saving:
- ✅ Check all questions have titles
- ✅ Check all criteria have names and positive points
- ✅ Verify total points match your intended scale
- ✅ Review descriptions for clarity

### 8. Save the Scheme

Click **Create Scheme** to save.

You'll see a success notification and be redirected to the scheme detail page.

## Tips for Effective Schemes

### Point Distribution

**Recommended Ranges:**
- Total Scheme: 10-100 points (most common: 100)
- Questions: 10-50 points each
- Criteria: 5-25 points each

**Why These Ranges:**
- Easier mental math for graders
- Clearer point increments
- More intuitive percentages

### Number of Components

**Recommended:**
- Questions: 3-6 per scheme
- Criteria: 2-5 per question
- Total Criteria: 8-20 per scheme

**Why:**
- Balances detail with practicality
- Prevents grader fatigue
- Provides adequate differentiation

### Using Fractional Points

Fractional points (e.g., 2.5, 7.5) are useful when:
- You want finer gradation (e.g., 2.5 = "partially meets expectation")
- Total scheme points don't divide evenly
- You're converting from a different scale

**Example:**
```
Criterion: "Evidence Quality" (7.5 points)
├── Excellent (7.5): Multiple credible sources, well-integrated
├── Good (6.0): Adequate sources, mostly well-used
├── Fair (4.5): Some sources, could be better integrated
├── Poor (2.5): Few sources, poorly integrated
└── Inadequate (0): No credible sources
```

## Common Pitfalls to Avoid

❌ **Vague Criterion Names**
- Bad: "Content", "Quality"
- Good: "Thesis Statement", "Evidence Quality"

❌ **Inconsistent Point Values**
- Bad: 17 points, 23 points, 8 points
- Good: 15 points, 25 points, 10 points

❌ **Too Many Criteria**
- Bad: 30 criteria (grading fatigue)
- Good: 10-15 criteria (focused evaluation)

❌ **Missing Descriptions**
- Bad: No description
- Good: "Clear, arguable claim that previews main points"

❌ **Unbalanced Questions**
- Bad: Q1: 5 points, Q2: 90 points, Q3: 5 points
- Good: Q1: 25 points, Q2: 50 points, Q3: 25 points

## Next Steps

After creating your scheme:
1. **Test it**: Grade 1-2 sample submissions to verify it works as intended
2. **Adjust**: Edit the scheme if needed before bulk grading
3. **Clone**: Create variations for similar assignments
4. **Apply**: Use it to grade actual submissions

## See Also

- [Grading Submissions](02-grading-submissions.md) - How to apply schemes to grade submissions
- [Exporting Results](03-export-analysis.md) - Export and analyze grading data
- [API Reference](04-api-reference.md) - API endpoints for schemes
