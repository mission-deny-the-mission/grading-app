# Exporting and Analyzing Grading Results

This guide covers how to export grading data and analyze usage statistics.

## Prerequisites

- A grading scheme with completed submissions
- Graded submissions exist in the system

## Export Formats

The system supports two export formats:
1. **CSV** - Spreadsheet format for Excel, Google Sheets, etc.
2. **JSON** - Structured data for custom processing

## Exporting Grades

### From Scheme Statistics Page

1. Navigate to **Grading Schemes**
2. Click on a scheme to view details
3. Click **Statistics** button
4. Choose export format:
   - **Export CSV**: Download spreadsheet
   - **Export JSON**: Download structured data

### Export Options

#### Include/Exclude Incomplete Grades

**Query Parameter**: `?include_incomplete=false`

- **Default**: Includes all submissions (complete and incomplete)
- **Filtered**: Add `?include_incomplete=false` to URL
- **Use Case**: Export only finalized grades for reporting

Example URLs:
```
/api/export/schemes/123?format=csv&include_incomplete=false
/api/export/schemes/123?format=json&include_incomplete=true
```

## CSV Export Format

### Structure

The CSV export provides a flat, row-per-evaluation structure:

```csv
Student ID,Student Name,Submission ID,Question,Criterion,Points Earned,Max Points,Percentage,Feedback,Graded By,Graded At
STU001,John Doe,456,Introduction,Thesis Statement,9.5,10,95.0%,Excellent thesis,prof@example.com,2025-11-15 10:30:00
STU001,John Doe,456,Introduction,Hook,8.0,10,80.0%,Good opening,prof@example.com,2025-11-15 10:30:00
STU001,John Doe,456,Body Content,Evidence Quality,22.0,25,88.0%,Strong sources,prof@example.com,2025-11-15 10:30:00
...
```

### Column Definitions

| Column | Description | Example |
|--------|-------------|---------|
| Student ID | Student identifier | "STU001" |
| Student Name | Student full name | "John Doe" |
| Submission ID | Unique submission reference | "456" |
| Question | Question title | "Introduction" |
| Criterion | Criterion name | "Thesis Statement" |
| Points Earned | Score given | 9.5 |
| Max Points | Maximum possible | 10 |
| Percentage | (Earned/Max) × 100 | 95.0% |
| Feedback | Grader feedback | "Excellent thesis" |
| Graded By | Grader email/ID | "prof@example.com" |
| Graded At | Timestamp | "2025-11-15 10:30:00" |

### Using CSV Data

#### In Excel/Google Sheets

**Pivot Tables**:
- Rows: Student Name
- Values: SUM of Points Earned
- Filters: Question, Criterion

**Analysis Examples**:
```excel
=AVERAGE(F:F)  // Average points earned across all criteria
=COUNTIF(H:H,">90%")  // Count submissions scoring >90%
=SUMIF(A:A,"STU001",F:F)  // Total points for specific student
```

**Charts**:
- Student performance distribution (histogram)
- Average scores by criterion (bar chart)
- Score trends over time (line chart)

#### In R

```r
# Load data
grades <- read.csv("scheme-export.csv")

# Summary statistics
summary(grades$Points.Earned)

# Average by criterion
aggregate(Points.Earned ~ Criterion, data=grades, FUN=mean)

# Student totals
student_totals <- aggregate(Points.Earned ~ Student.ID, data=grades, FUN=sum)

# Visualization
library(ggplot2)
ggplot(grades, aes(x=Criterion, y=Points.Earned)) +
  geom_boxplot() +
  theme(axis.text.x = element_text(angle=45, hjust=1))
```

#### In Python/Pandas

```python
import pandas as pd

# Load data
df = pd.read_csv('scheme-export.csv')

# Summary statistics
print(df['Points Earned'].describe())

# Average by criterion
criterion_avg = df.groupby('Criterion')['Points Earned'].mean()

# Student performance
student_scores = df.groupby('Student ID').agg({
    'Points Earned': 'sum',
    'Max Points': 'sum'
})
student_scores['Percentage'] = (
    student_scores['Points Earned'] / student_scores['Max Points'] * 100
)

# Identify struggling students
struggling = student_scores[student_scores['Percentage'] < 70]
print(struggling)
```

## JSON Export Format

### Structure

The JSON export provides hierarchical, submission-based structure:

```json
{
  "metadata": {
    "scheme_id": "123",
    "scheme_name": "Essay Rubric Fall 2025",
    "total_submissions": 25,
    "export_date": "2025-11-15T10:00:00Z",
    "scheme_version": 1
  },
  "submissions": [
    {
      "student_id": "STU001",
      "student_name": "John Doe",
      "submission_id": "456",
      "total_points_earned": 87.5,
      "total_points_possible": 100,
      "percentage_score": 87.5,
      "is_complete": true,
      "graded_by": "prof@example.com",
      "graded_at": "2025-11-15T10:30:00Z",
      "evaluations": [
        {
          "question_title": "Introduction",
          "criterion_name": "Thesis Statement",
          "criterion_id": "789",
          "points_awarded": 9.5,
          "max_points": 10,
          "feedback": "Excellent thesis statement - clear and arguable",
          "percentage": 95.0
        },
        // ... more evaluations
      ]
    },
    // ... more submissions
  ],
  "statistics": {
    "average_score": 82.3,
    "median_score": 84.0,
    "min_score": 45.5,
    "max_score": 98.0,
    "std_deviation": 12.4
  }
}
```

### Using JSON Data

#### In JavaScript/Node.js

```javascript
const fs = require('fs');
const data = JSON.parse(fs.readFileSync('scheme-export.json'));

// Find top performers
const topStudents = data.submissions
  .filter(s => s.percentage_score >= 90)
  .map(s => ({ name: s.student_name, score: s.percentage_score }))
  .sort((a, b) => b.score - a.score);

console.log('Top Performers:', topStudents);

// Identify weak areas
const criteriaScores = {};
data.submissions.forEach(sub => {
  sub.evaluations.forEach(eval => {
    if (!criteriaScores[eval.criterion_name]) {
      criteriaScores[eval.criterion_name] = [];
    }
    criteriaScores[eval.criterion_name].push(eval.percentage);
  });
});

// Calculate averages
const averages = Object.entries(criteriaScores).map(([criterion, scores]) => ({
  criterion,
  average: scores.reduce((a, b) => a + b, 0) / scores.length
})).sort((a, b) => a.average - b.average);

console.log('Weakest Areas:', averages.slice(0, 3));
```

#### In Python

```python
import json
import statistics

# Load data
with open('scheme-export.json') as f:
    data = json.load(f)

# Overall statistics
scores = [s['percentage_score'] for s in data['submissions']]
print(f"Mean: {statistics.mean(scores):.2f}")
print(f"Median: {statistics.median(scores):.2f}")
print(f"Std Dev: {statistics.stdev(scores):.2f}")

# Per-criterion analysis
criteria = {}
for submission in data['submissions']:
    for evaluation in submission['evaluations']:
        criterion = evaluation['criterion_name']
        if criterion not in criteria:
            criteria[criterion] = []
        criteria[criterion].append(evaluation['percentage'])

# Identify areas for improvement
weak_areas = {
    criterion: statistics.mean(scores)
    for criterion, scores in criteria.items()
}
sorted_criteria = sorted(weak_areas.items(), key=lambda x: x[1])

print("\nWeakest Criteria:")
for criterion, avg in sorted_criteria[:3]:
    print(f"  {criterion}: {avg:.1f}%")
```

## Statistics View

### Accessing Statistics

1. Navigate to a grading scheme
2. Click **Statistics** button
3. View comprehensive usage data

### Available Statistics

#### Overview
- Total submissions graded
- Average overall score
- Score distribution
- Completion rate

#### Per-Question Stats
- Average score per question
- Achievement percentage (avg/max × 100)
- Score distribution
- Number of evaluations

#### Per-Criterion Stats
- Average score per criterion
- Achievement percentage
- Difficulty rating (inverse of achievement %)
- Common feedback themes (future)

### Example Statistics Page

```
Scheme: Essay Rubric Fall 2025

Overview
├── Total Submissions: 25
├── Average Score: 82.3 / 100 (82.3%)
├── Complete: 23 (92%)
└── Incomplete: 2 (8%)

Per-Question Statistics
├── Introduction (25 points)
│   ├── Average: 21.2 points (84.8%)
│   └── Evaluations: 25
├── Body Content (50 points)
│   ├── Average: 40.1 points (80.2%)
│   └── Evaluations: 25
└── Conclusion (25 points)
    ├── Average: 21.0 points (84.0%)
    └── Evaluations: 25

Per-Criterion Statistics (Top 3 Weakest)
├── Evidence Quality: 78.5% (needs attention)
├── Analysis Depth: 79.2%
└── Organization: 81.0%

Per-Criterion Statistics (Top 3 Strongest)
├── Grammar: 94.2%
├── Thesis Statement: 92.5%
└── Structure: 90.8%
```

## Analysis Techniques

### Identifying Trends

#### Grade Distribution
- What's the shape? (normal, bimodal, skewed)
- Are most students passing?
- Are there outliers?

#### Criterion Difficulty
- Which criteria have lowest averages?
- Are point allocations appropriate?
- Do students struggle with same areas?

#### Grading Consistency
- Similar submissions getting similar scores?
- Any grade inflation/deflation patterns?
- Feedback quality consistent?

### Actionable Insights

#### For Instructors

**Low Average Criterion** (< 70%):
- Review teaching materials for this topic
- Add more practice/examples
- Clarify rubric expectations
- Consider adjusting point allocation

**High Variance** (std dev > 20%):
- Review rubric clarity
- Provide exemplars
- Calibrate grading standards
- Check for bimodal distribution (two distinct groups)

**Low Completion Rate** (< 80%):
- Investigate submission issues
- Check deadline/workload
- Review assignment clarity

#### For Students

**Individual Performance**:
- Which criteria scored lowest?
- What patterns in feedback?
- How to improve for next assignment?

**Peer Comparison**:
- How does my score compare to class average?
- Which areas am I strong/weak relative to peers?

## Performance Considerations

### Large Dataset Handling

The system is optimized for large exports:
- **Tested**: 100 students × 50 criteria = 5,000 evaluations
- **CSV Export**: ~0.3 seconds
- **JSON Export**: ~0.2 seconds
- **Memory**: Efficient streaming for large datasets

### Best Practices

1. **Filter When Possible**: Use `include_incomplete=false` if you don't need drafts
2. **Schedule Exports**: For very large datasets, schedule during off-peak hours
3. **Incremental Analysis**: Analyze data in batches if needed
4. **Cache Results**: Save exported files for repeated analysis

## Troubleshooting

### Issue: Export file empty
**Causes**:
- No graded submissions for that scheme
- All submissions filtered out (e.g., incomplete excluded)

**Solution**: Verify submissions exist and are complete

### Issue: Export slow
**Causes**:
- Very large dataset (1000+ submissions)
- Server load

**Solution**:
- Export during off-peak hours
- Filter to reduce data size
- Contact administrator for database optimization

### Issue: CSV won't open in Excel
**Causes**:
- Character encoding issues
- Very large file

**Solution**:
- Try Google Sheets
- Open as UTF-8 in Excel
- Split into smaller exports

## Next Steps

- Review [Creating Schemes](01-creating-schemes.md) to improve rubric design
- See [Grading Submissions](02-grading-submissions.md) for grading tips
- Check [API Reference](04-api-reference.md) for programmatic access

## See Also

- [API Reference](04-api-reference.md) - Export API endpoints
- [Creating Schemes](01-creating-schemes.md) - Scheme design best practices
- [Grading Submissions](02-grading-submissions.md) - Grading workflow
