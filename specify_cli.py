#!/usr/bin/env python3
"""
Simplified Specify CLI for Grading App Spec-Driven Development
Based on GitHub Spec Kit methodology

This is a lightweight implementation that provides the core functionality
needed for Spec-Driven Development in the grading app project.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python specify_cli.py <command>")
        print("Commands:")
        print("  init     - Initialize Spec-Driven Development")
        print("  check    - Check system requirements")
        print("  status   - Show current status")
        print("  help     - Show this help message")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        init_project()
    elif command == "check":
        check_requirements()
    elif command == "status":
        show_status()
    elif command == "help":
        show_help()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

def init_project():
    """Initialize Spec-Driven Development in current project"""

    # Check if already initialized
    specify_dir = Path('.specify')
    if specify_dir.exists() and '--force' not in sys.argv:
        print("✅ Spec-Driven Development already initialized in this project")
        return

    # Create directory structure
    print("🏗️  Creating Spec-Driven Development structure...")

    directories = [
        '.specify',
        '.specify/memory',
        '.specify/specs',
        '.specify/templates',
        '.specify/scripts',
        '.specify/templates/commands'
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"  📁 Created {directory}")

    # Check if templates exist
    template_files = [
        '.specify/templates/plan-template.md',
        '.specify/templates/spec-template.md',
        '.specify/templates/tasks-template.md',
        '.specify/memory/constitution.md'
    ]

    missing_templates = [f for f in template_files if not Path(f).exists()]
    if missing_templates:
        print(f"⚠️  Missing templates: {missing_templates}")
        print("    These will be created when you first use the slash commands.")

    print("✅ Initialized Spec-Driven Development")
    print("\n📋 Next steps:")
    print("1. Start your AI coding agent in this directory")
    print("2. Use the following slash commands:")
    print("   /constitution - View/modify project principles")
    print("   /specify - Define what you want to build")
    print("   /plan - Create technical implementation plans")
    print("   /tasks - Generate actionable task lists")
    print("   /implement - Execute implementation")

def check_requirements():
    """Check system requirements"""

    print("🔍 System Requirements Check:")

    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 11):
        print(f"  ✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        print(f"  ❌ Python {python_version.major}.{python_version.minor}.{python_version.micro} (need 3.11+)")

    # Check Click
    try:
        import click
        print("  ✅ Click package available")
    except ImportError:
        print("  ⚠️  Click package not installed (optional)")

    # Check Git
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✅ Git")
        else:
            print("  ❌ Git")
    except FileNotFoundError:
        print("  ❌ Git not found")

    # Check if .specify directory exists
    if Path('.specify').exists():
        print("  ✅ Spec-Driven Development initialized")
    else:
        print("  ❌ Spec-Driven Development not initialized")

    # Check if we're in a git repo
    if Path('.git').exists():
        print("  ✅ Git repository")
    else:
        print("  ⚠️  Not in a Git repository")

    # Check project files
    required_files = ['app.py', 'models.py', 'requirements.txt']
    for file in required_files:
        if Path(file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} missing")

def show_status():
    """Show current Spec-Driven Development status"""

    specify_dir = Path('.specify')
    if not specify_dir.exists():
        print("❌ Spec-Driven Development not initialized. Run 'python specify_cli.py init' first.")
        return

    print("📋 Spec-Driven Development Status:")
    print(f"📁 Project root: {Path.cwd()}")

    # Check constitution
    constitution_file = specify_dir / 'memory' / 'constitution.md'
    if constitution_file.exists():
        print("✅ Constitution established")
        # Read and show version
        try:
            with open(constitution_file, 'r') as f:
                content = f.read()
                for line in content.split('\n'):
                    if line.startswith('**Version**:'):
                        print(f"   📄 {line.strip()}")
                        break
        except:
            pass
    else:
        print("❌ No constitution - run /constitution first")

    # Check specs
    specs_dir = specify_dir / 'specs'
    if specs_dir.exists():
        spec_count = len([d for d in specs_dir.iterdir() if d.is_dir()])
        if spec_count > 0:
            print(f"✅ {spec_count} specification(s) created")
            # List specs
            for spec_dir in specs_dir.iterdir():
                if spec_dir.is_dir():
                    spec_file = spec_dir / 'spec.md'
                    if spec_file.exists():
                        print(f"   📝 {spec_dir.name}")
        else:
            print("❌ No specifications - run /specify first")

    # Check templates
    templates_dir = specify_dir / 'templates'
    template_files = ['plan-template.md', 'spec-template.md', 'tasks-template.md']
    for template in template_files:
        if (templates_dir / template).exists():
            print(f"✅ {template}")
        else:
            print(f"❌ {template} missing")

    # Check git status
    try:
        result = subprocess.run(['git', 'status', '--porcelain'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Git repository active")
        else:
            print("⚠️ Git status unknown")
    except:
        print("⚠️ Git status unknown")

def show_help():
    """Show help information"""

    print("Simplified Specify CLI for Grading App")
    print("=====================================")
    print("")
    print("This is a lightweight version of GitHub Spec Kit adapted for the grading app project.")
    print("It provides the core slash commands for structured development:")
    print("")
    print("Slash Commands (used with AI coding agent):")
    print("  /constitution - Establish project principles")
    print("  /specify      - Define requirements and user stories")
    print("  /clarify      - Resolve underspecified areas")
    print("  /plan         - Create technical implementation plans")
    print("  /tasks        - Generate actionable task lists")
    print("  /analyze      - Cross-artifact consistency analysis")
    print("  /implement    - Execute implementation tasks")
    print("")
    print("CLI Commands:")
    print("  python specify_cli.py init     - Initialize Spec-Driven Development")
    print("  python specify_cli.py check    - Check system requirements")
    print("  python specify_cli.py status   - Show current status")
    print("  python specify_cli.py help     - Show this help message")
    print("")
    print("Examples:")
    print("  python specify_cli.py init     # Initialize in current directory")
    print("  python specify_cli.py check    # Check requirements")
    print("  python specify_cli.py status   # Show project status")

if __name__ == '__main__':
    main()
