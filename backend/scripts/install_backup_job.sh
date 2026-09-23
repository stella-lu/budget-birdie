#!/bin/bash
# Installs a launchd agent that runs run_backup.sh nightly at 23:30.
# Safe to re-run (unloads any existing job with the same label first).
#
# Prerequisites (do these first):
#   1. rclone config    # set up a remote named "gdrive" pointing at Google Drive
#   2. Test it once by hand: ./scripts/run_backup.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.budgetbirdie.backup"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
RCLONE_DIR="$(dirname "$(command -v rclone || echo "$HOME/bin/rclone")")"

mkdir -p "$PROJECT_ROOT/backups"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$PROJECT_ROOT/scripts/run_backup.sh</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$RCLONE_DIR:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>23</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$PROJECT_ROOT/backups/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_ROOT/backups/launchd.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"
echo "Installed and loaded $LABEL — runs nightly at 23:30."
echo "Logs: $PROJECT_ROOT/backups/launchd.log"
echo "To remove: launchctl unload $PLIST && rm $PLIST"
