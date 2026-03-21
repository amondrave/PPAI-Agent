# Scoring algorithm constants — v1.0 (2026-03-18)
# Changing these values = new version, requires PR documentation.

# urgencyScore thresholds (hours)
URGENCY_THRESHOLD_24H = 24
URGENCY_THRESHOLD_72H = 72

# urgencyScore values (0–10)
URGENCY_SCORE_24H = 10   # deadline within next 24h
URGENCY_SCORE_72H = 7    # deadline within next 72h
URGENCY_SCORE_FAR = 4    # deadline beyond 72h
URGENCY_SCORE_NONE = 3   # no deadline

# ageScore cap (days)
AGE_SCORE_MAX_DAYS = 7   # 1 point per day, capped at 7

# snoozeScore formula: min(snooze_count * MULTIPLIER, MAX)
SNOOZE_SCORE_MULTIPLIER = 2
SNOOZE_SCORE_MAX = 10

# in-process Top 3 cache TTL (seconds)
TOP3_CACHE_TTL_SECONDS = 60
