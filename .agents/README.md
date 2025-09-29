# AI Agent Support Directory

This directory contains resources and templates to help AI agents work effectively with the Grading App codebase.

## Purpose

The `.agents/` directory provides structured guidance for AI agents who need to understand, modify, or maintain the Grading App project. It includes:

- **Project Overview**: Comprehensive understanding of the application architecture and features
- **Development Guidelines**: Coding standards, patterns, and best practices
- **Task Templates**: Structured approaches for common development tasks
- **Quality Assurance**: Checklists and procedures for ensuring code quality

## Directory Structure

```
.agents/
├── README.md                    # This file
├── prompts/                     # Task-specific prompt templates
│   ├── feature-development.md   # Template for implementing new features
│   ├── bug-fixing.md           # Template for fixing bugs
│   ├── code-review.md          # Template for code reviews
│   └── deployment-ops.md       # Template for deployment operations
└── ../agents.md                # Main project guide for AI agents
```

## How to Use

### For AI Agents

1. **Start with `../agents.md`** - Read the main project overview first
2. **Select appropriate template** - Choose the template that matches your task
3. **Follow the checklists** - Use the structured approach to ensure completeness
4. **Maintain quality** - Follow the coding standards and testing guidelines

### For Human Developers

1. **Review templates** - Understand the structured approach expected from AI agents
2. **Customize as needed** - Adapt templates for your specific requirements
3. **Provide feedback** - Suggest improvements to templates based on experience

## Key Principles

- **Consistency**: All AI agents should follow the same patterns and standards
- **Completeness**: Templates ensure all aspects of a task are considered
- **Quality**: Built-in quality checks and best practices
- **Documentation**: Changes should be properly documented
- **Testing**: Comprehensive testing is required for all changes

## Template Usage Examples

### Feature Development
```bash
# When implementing a new feature
# Use .agents/prompts/feature-development.md as a guide
```

### Bug Fixing
```bash
# When fixing a reported bug
# Use .agents/prompts/bug-fixing.md for structured debugging
```

### Code Review
```bash
# When reviewing code changes
# Use .agents/prompts/code-review.md for comprehensive review
```

### Deployment
```bash
# When planning or executing deployments
# Use .agents/prompts/deployment-ops.md for operational guidance
```

## Contributing

To improve these templates:

1. **Add missing scenarios** - Create new templates for common tasks
2. **Enhance existing templates** - Add more detailed checklists or guidance
3. **Update guidelines** - Keep coding standards and best practices current
4. **Add examples** - Include real-world examples where helpful

## Contact

For questions about these templates or the AI agent workflow:

- Review the main project documentation in `docs/`
- Check the `README.md` in the project root
- Examine existing code patterns in the codebase

These templates are designed to evolve with the project and should be updated regularly to reflect current best practices and project requirements.