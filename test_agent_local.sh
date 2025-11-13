#!/bin/bash
# Script to test the CV Matcher Agent locally before running in GitHub Actions

set -e

echo "🧪 Testing CV Matcher Agent Locally"
echo "===================================="
echo ""

# Check if GEMINI_API_KEY is set
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ Error: GEMINI_API_KEY environment variable is not set"
    echo "Please set it with: export GEMINI_API_KEY='your-api-key'"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed"
    exit 1
fi

# Install dependencies if needed
echo "📦 Installing dependencies..."
pip install -q -r agent/requirements.txt

# Use the example job description
JOB_DESC_FILE="examples/job_description_sre.txt"

if [ ! -f "$JOB_DESC_FILE" ]; then
    echo "❌ Error: Job description file not found: $JOB_DESC_FILE"
    exit 1
fi

echo "📋 Using job description from: $JOB_DESC_FILE"
echo ""

# Run the agent
echo "🤖 Running CV Matcher Agent..."
python3 agent/cv_matcher_agent.py \
    --cv ./LaTeX/resume.tex \
    --job-description "$JOB_DESC_FILE" \
    --output ./LaTeX/resume_adapted.tex

echo ""
echo "✅ Agent execution complete!"
echo ""
echo "📊 Results:"
echo "  - Original CV: ./LaTeX/resume.tex"
echo "  - Adapted CV: ./LaTeX/resume_adapted.tex"
echo ""
echo "To compile the adapted CV to PDF, you can use:"
echo "  - Run the LaTeX workflow in GitHub Actions"
echo "  - Or compile locally if you have LaTeX installed"
echo ""
echo "💡 Tip: You can review the changes with:"
echo "  diff ./LaTeX/resume.tex ./LaTeX/resume_adapted.tex"
