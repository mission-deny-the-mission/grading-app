#!/bin/bash
#
# Bundle Size Analysis Script
#
# Analyzes PyInstaller bundle size and identifies large dependencies
# Usage: bash desktop/installer/analyze-bundle.sh

set -e

DIST_DIR="dist/GradingApp"
TARGET_SIZE_MB=150

echo "=================================================="
echo "Grading App Bundle Size Analysis"
echo "=================================================="
echo ""

# Check if dist directory exists
if [ ! -d "$DIST_DIR" ]; then
    echo "Error: Distribution directory not found: $DIST_DIR"
    echo "Please run: pyinstaller grading-app.spec"
    exit 1
fi

# Calculate total size
if command -v du &> /dev/null; then
    TOTAL_SIZE=$(du -sm "$DIST_DIR" | cut -f1)
    echo "Total Bundle Size: ${TOTAL_SIZE}MB"
    echo "Target Size:       ${TARGET_SIZE_MB}MB"
    echo ""

    if [ $TOTAL_SIZE -gt $TARGET_SIZE_MB ]; then
        echo "WARNING: Bundle exceeds target size by $((TOTAL_SIZE - TARGET_SIZE_MB))MB"
    else
        echo "OK: Bundle is within target size"
    fi
    echo ""
else
    echo "Warning: 'du' command not available, skipping size check"
    echo ""
fi

# List largest files
echo "Largest Files (Top 20):"
echo "--------------------------------------"
if command -v find &> /dev/null; then
    find "$DIST_DIR" -type f -exec ls -lh {} \; | \
        awk '{print $5 "\t" $9}' | \
        sort -rh | \
        head -20
else
    echo "Warning: 'find' command not available"
fi
echo ""

# Analyze by file type
echo "Size by File Type:"
echo "--------------------------------------"

# Python libraries
PYLIB_SIZE=$(find "$DIST_DIR" -name "*.pyc" -o -name "*.so" -o -name "*.pyd" 2>/dev/null | xargs du -ch 2>/dev/null | tail -1 | cut -f1 || echo "N/A")
echo "Python libraries (.pyc, .so, .pyd): $PYLIB_SIZE"

# Data files
DATA_SIZE=$(find "$DIST_DIR" -name "*.html" -o -name "*.css" -o -name "*.js" -o -name "*.json" 2>/dev/null | xargs du -ch 2>/dev/null | tail -1 | cut -f1 || echo "N/A")
echo "Data files (templates, static):     $DATA_SIZE"

# Executables
EXE_SIZE=$(find "$DIST_DIR" -type f -executable 2>/dev/null | xargs du -ch 2>/dev/null | tail -1 | cut -f1 || echo "N/A")
echo "Executables:                        $EXE_SIZE"

echo ""

# Check for commonly excluded modules
echo "Optimization Opportunities:"
echo "--------------------------------------"

EXCLUDE_SUGGESTIONS=()

# Check for test modules
if find "$DIST_DIR" -path "*/test/*" -o -path "*/tests/*" -o -name "*_test.py" 2>/dev/null | grep -q .; then
    EXCLUDE_SUGGESTIONS+=("--exclude-module pytest")
    EXCLUDE_SUGGESTIONS+=("--exclude-module unittest")
    echo "- Found test modules (can exclude: pytest, unittest)"
fi

# Check for development tools
if find "$DIST_DIR" -name "*setuptools*" 2>/dev/null | grep -q .; then
    EXCLUDE_SUGGESTIONS+=("--exclude-module setuptools")
    echo "- Found setuptools (can exclude if not needed at runtime)"
fi

# Check for documentation
if find "$DIST_DIR" -name "*.md" -o -name "*.rst" -o -name "*.txt" 2>/dev/null | grep -q .; then
    echo "- Found documentation files (consider excluding)"
fi

# Check for large GUI libraries
if find "$DIST_DIR" -name "*matplotlib*" 2>/dev/null | grep -q .; then
    EXCLUDE_SUGGESTIONS+=("--exclude-module matplotlib")
    echo "- Found matplotlib (can exclude if not used)"
fi

if find "$DIST_DIR" -name "*numpy*" 2>/dev/null | grep -q .; then
    echo "- Found numpy (check if actually needed)"
fi

if [ ${#EXCLUDE_SUGGESTIONS[@]} -eq 0 ]; then
    echo "- No major optimization opportunities found"
else
    echo ""
    echo "Suggested exclusions for grading-app.spec:"
    printf '%s\n' "${EXCLUDE_SUGGESTIONS[@]}" | sed 's/^/  /'
fi

echo ""
echo "=================================================="
echo "Analysis Complete"
echo "=================================================="
