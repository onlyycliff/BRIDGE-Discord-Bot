# IMPORTANT: --workers MUST stay at 1. The Discord bot thread is started once
# at module import via _ensure_bot_started() in dashboard.py. Multiple workers
# would each spawn a bot process logging in with the same token — Discord will
# kick one, or both will process the same interactions causing double-votes.
web: gunicorn dashboard:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 --log-level info --access-logfile - --error-logfile -
