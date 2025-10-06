#!/usr/bin/env python3
"""
Simplified Specify CLI for Grading App Spec-Driven Development
Based on GitHub Spec Kit methodology
"""

import os
import sys
import click
from pathlib import Path

@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    Simplified Specify CLI for Grading App Spec-Driven Development

    This is a lightweight version of GitHub Spec Kit adapted for the grading app project.
    It provides the core slash commands for structured development:

    /constitution - Establish project principles
    /specify - Define requirements and user stories
    /clarify - Resolve underspecified areas
    /plan - Create technical implementation plans
    /tasks - Generate actionable task lists
    /analyze - Cross-artifact consistency analysis
    /implement - Execute implementation tasks
    """
    pass

@cli.command()
@click.argument('project_name', default='grading-app')
@click.option('--here', is_flag=True, help='Initialize in current directory')
@click.option('--force', is_flag=True, help='Force overwrite existing files')
def init(project_name, here, force):
    """Initialize Spec-Driven Development in current project"""

    if here or project_name == 'grading-app':
        target_dir = Path('.')
    else:
        target_dir = Path(project_name)
        target_dir.mkdir(exist_ok=True)

    specify_dir = target_dir / '.specify'

    # Check if already initialized
    if specify_dir.exists() and not force:
        click.echo("✅ Spec-Driven Development already initialized in this project")
        return

    # Create directory structure
    (specify_dir / 'memory').mkdir(parents=True, exist_ok=True)
    (specify_dir / 'specs').mkdir(parents=True, exist_ok=True)
    (specify_dir / 'templates').mkdir(parents=True, exist_ok=True)
    (specify_dir / 'scripts').mkdir(parents=True, exist_ok=True)

    click.echo(f"✅ Initialized Spec-Driven Development in {target_dir}")
    click.echo("\nNext steps:")
    click.echo("1. Run your AI coding agent in this directory")
    click.echo("2. Use /constitution to establish project principles")
    click.echo("3. Use /specify to define what you want to build")
    click.echo("4. Use /plan to create technical implementation plans")
    click.echo("5. Use /tasks to break down into actionable tasks")
    click.echo("6. Use /implement to execute the implementation")

@cli.command()
def check():
    """Check system requirements"""

    checks = []

    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 11):
        checks.append(("✅", f"Python {python_version.major}.{python_version.minor}.{python_version.micro}"))
    else:
        checks.append(("❌", f"Python {python_version.major}.{python_version.minor}.{python_version.micro} (need 3.11+)"))

    # Check Git
    try:
        result = os.system("git --version > /dev/null 2>&1")
        if result == 0:
            checks.append(("✅", "Git"))
        else:
            checks.append(("❌", "Git"))
    except:
        checks.append(("❌", "Git"))

    # Check if .specify directory exists
    if Path('.specify').exists():
        checks.append(("✅", "Spec-Driven Development initialized"))
    else:
        checks.append(("❌", "Spec-Driven Development not initialized"))

    # Check if we're in a git repo
    if Path('.git').exists():
        checks.append(("✅", "Git repository"))
    else:
        checks.append(("⚠️", "Not in a Git repository"))

    click.echo("System Requirements Check:")
    for status, item in checks:
        click.echo(f"  {status} {item}")

@cli.command()
def status():
    """Show current Spec-Driven Development status"""

    specify_dir = Path('.specify')
    if not specify_dir.exists():
        click.echo("❌ Spec-Driven Development not initialized. Run 'specify init' first.")
        return

    click.echo("📋 Spec-Driven Development Status:")
    click.echo(f"📁 Project root: {Path.cwd()}")

    # Check constitution
    constitution_file = specify_dir / 'memory' / 'constitution.md'
    if constitution_file.exists():
        click.echo("✅ Constitution established")
    else:
        click.echo("❌ No constitution - run /constitution first")

    # Check specs
    specs_dir = specify_dir / 'specs'
    if specs_dir.exists():
        spec_count = len([d for d in specs_dir.iterdir() if d.is_dir()])
        if spec_count > 0:
            click.echo(f"✅ {spec_count} specification(s) created")
        else:
            click.echo("❌ No specifications - run /specify first")

    # Check git status
    try:
        os.system("git status --porcelain > /dev/null 2>&1")
        click.echo("✅ Git repository active")
    except:
        click.echo("⚠️ Git status unknown")

if __name__ == '__main__':
    cli()
