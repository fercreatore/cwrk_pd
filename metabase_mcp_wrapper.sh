#!/bin/bash
export METABASE_URL="http://192.168.2.106:3000"
export METABASE_API_KEY="mb_qkq1EvNki5YjpW3u7Lf4PMLkE7J4W/mCd2d+QhA4Ld0="
export LOG_LEVEL="silent"
export NO_COLOR="1"
exec /opt/homebrew/bin/node /opt/homebrew/lib/node_modules/metabase-ai-assistant/src/mcp/server.js 2>/dev/null
