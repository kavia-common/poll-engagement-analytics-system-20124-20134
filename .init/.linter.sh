#!/bin/bash
cd /home/kavia/workspace/code-generation/poll-engagement-analytics-system-20124-20134/polls_analytics_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

