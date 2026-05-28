#!/usr/bin/env bash
exec setsid -f bash -c '
  DISPLAY=:0 exec /home/robin/Dokumente/Coding/ai-assistant/.venv/bin/python -m ai_assistant.main >> /tmp/ai-assistant.log 2>&1
'
