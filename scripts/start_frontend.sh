#!/usr/bin/env bash
# Start the React dashboard on http://localhost:3000
set -e
cd "$(dirname "$0")/../frontend"
exec npm run dev