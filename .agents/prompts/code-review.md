# Code Review Template

## Review Overview
- **File/PR**: [File name or PR number]
- **Author**: [Author name]
- **Reviewer**: [Your name]
- **Review Date**: [Current date]

## Summary
[Brief summary of what the code does and the purpose of the changes]

## Code Quality Assessment

### ✅ Strengths
- [ ] Well-structured and readable code
- [ ] Follows project coding standards
- [ ] Good use of existing patterns and conventions
- [ ] Comprehensive error handling
- [ ] Appropriate documentation and comments
- [ ] Efficient algorithms and data structures
- [ ] Good separation of concerns
- [ ] Proper input validation
- [ ] Security best practices followed

### ⚠️ Areas for Improvement
- [ ] Code complexity could be reduced
- [ ] Missing or unclear documentation
- [ ] Inconsistent naming conventions
- [ ] Potential performance issues
- [ ] Error handling could be improved
- [ ] Code duplication opportunities
- [ ] Better separation of concerns needed
- [ ] Missing input validation
- [ ] Security concerns identified

## Detailed Review

### Functionality
- [ ] Code implements the intended functionality correctly
- [ ] Edge cases are handled appropriately
- [ ] Business logic is sound
- [ ] Integration with existing code works as expected

### Code Structure and Design
- [ ] Functions/classes are well-organized
- [ ] Single responsibility principle followed
- [ ] Code is modular and reusable
- [ ] Dependencies are appropriate and minimal
- [ ] Design patterns used correctly (if applicable)

### Error Handling and Robustness
- [ ] Proper exception handling
- [ ] Meaningful error messages
- [ ] Graceful degradation on failure
- [ ] Resource cleanup is handled
- [ ] Logging is appropriate

### Performance Considerations
- [ ] Database queries are optimized
- [ ] Memory usage is efficient
- [ ] Algorithm complexity is appropriate
- [ ] Caching is used where beneficial
- [ ] No unnecessary computations

### Security Assessment
- [ ] Input validation is comprehensive
- [ ] SQL injection protection in place
- [ ] XSS prevention implemented
- [ ] Authentication/authorization handled
- [ ] Sensitive data is properly protected
- [ ] API keys/secrets not exposed

### Testing Coverage
- [ ] Unit tests are included and comprehensive
- [ ] Integration tests cover key scenarios
- [ ] Edge cases are tested
- [ ] Mocks are used appropriately
- [ ] Test coverage is maintained or improved

## Specific Issues and Recommendations

### Critical Issues (Must Fix)
1. **[Issue Title]**
   - **Location**: [File:Line numbers]
   - **Description**: [Detailed description of the issue]
   - **Risk**: [Security, functionality, performance, etc.]
   - **Recommendation**: [Specific fix recommendation]

### Major Issues (Should Fix)
1. **[Issue Title]**
   - **Location**: [File:Line numbers]
   - **Description**: [Detailed description of the issue]
   - **Risk**: [Maintainability, performance, etc.]
   - **Recommendation**: [Specific fix recommendation]

### Minor Issues (Nice to Have)
1. **[Issue Title]**
   - **Location**: [File:Line numbers]
   - **Description**: [Detailed description of the issue]
   - **Risk**: [Code quality, readability, etc.]
   - **Recommendation**: [Specific fix recommendation]

## Style and Formatting
- [ ] Code follows Black formatting standards
- [ ] Import statements are organized correctly
- [ ] Variable naming is consistent and descriptive
- [ ] Function and class names follow conventions
- [ ] Line length is within limits
- [ ] Whitespace and indentation are consistent

## Documentation
- [ ] Function/class docstrings are present and useful
- [ ] Complex logic is explained with comments
- [ ] README or other documentation is updated if needed
- [ ] API documentation is accurate if applicable

## Integration and Compatibility
- [ ] Changes don't break existing functionality
- [ ] Backward compatibility is maintained
- [ ] Database schema changes are handled properly
- [ ] API changes are versioned or documented
- [ ] Dependencies are compatible with project

## Deployment and Operations
- [ ] No changes that affect deployment process
- [ ] Configuration changes are documented
- [ ] Database migrations are included if needed
- [ ] New dependencies are clearly identified

## Test Results
- [ ] All tests pass locally
- [ ] CI/CD pipeline results are successful
- [ ] Performance tests meet expectations
- [ ] Security scans are clean

## Final Recommendation

### Approval Status
- [ ] **Approved** - Code is ready to merge
- [ ] **Approved with Comments** - Code can merge after minor changes
- [ ] **Changes Required** - Code needs revisions before approval
- [ ] **Rejected** - Code requires significant changes

### Merge Readiness
- [ ] Ready for merge
- [ ] Ready after minor fixes
- [ ] Requires more work

### Additional Comments
[Any additional context, praise, or specific guidance for the author]

## Follow-up Actions
- [ ] [ ] Author will address critical issues
- [ ] [ ] Author will address major issues
- [ ] [ ] Reviewer will re-review after changes
- [ ] [ ] Documentation updates needed
- [ ] [ ] Additional testing required

---
**Reviewer Signature**: [Your name/AI agent]
**Review Completed**: [Timestamp]