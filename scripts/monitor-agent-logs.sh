#!/bin/bash
# Monitor CloudWatch logs for Bedrock Agent and Lambda in real-time
# Solves: Checking logs too early, missing events due to lag

LAMBDA_NAME="$1"
DURATION="${2:-5}"  # Default 5 minutes

if [ -z "$LAMBDA_NAME" ]; then
    echo "Usage: ./monitor-agent-logs.sh <lambda-name> [duration-minutes]"
    exit 1
fi

LOG_GROUP="/aws/lambda/$LAMBDA_NAME"

echo "=========================================="
echo "MONITORING LOGS FOR: $LAMBDA_NAME"
echo "Duration: Last $DURATION minutes"
echo "=========================================="
echo ""

# Check if log group exists
if ! aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --query 'logGroups[0]' --output text &>/dev/null; then
    echo "❌ Log group not found: $LOG_GROUP"
    echo "   Lambda may not have been invoked yet"
    exit 1
fi

echo "📋 Recent Events (newest first):"
echo "------------------------------------------"

# Get logs from last N minutes
START_TIME=$(($(date +%s) - ($DURATION * 60)))000
END_TIME=$(date +%s)000

aws logs filter-log-events \
    --log-group-name "$LOG_GROUP" \
    --start-time "$START_TIME" \
    --end-time "$END_TIME" \
    --query 'events[*].[timestamp,message]' \
    --output text | \
while IFS=$'\t' read -r timestamp message; do
    # Convert timestamp to readable format
    readable_time=$(date -d "@$((timestamp / 1000))" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r "$((timestamp / 1000))" '+%Y-%m-%d %H:%M:%S')
    echo "[$readable_time] $message"
done

echo ""
echo "------------------------------------------"
echo "✅ Log monitoring complete"
echo ""
echo "💡 Tips:"
echo "   • If no logs appear, Lambda hasn't been invoked"
echo "   • Check for 'DependencyFailedException' in logs"
echo "   • Look for 'Task timed out' for timeout issues"
echo "   • Search for 'ERROR' or 'Exception' for errors"
echo ""
echo "To follow logs in real-time:"
echo "   aws logs tail $LOG_GROUP --follow"
