import os
import sys

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def get_login_rate_limit() -> str:
	# Avoid flaky test failures due to shared test client IP throttling.
	is_testing = os.getenv("TESTING", "false").lower() == "true" or "pytest" in sys.modules
	if is_testing:
		return "100000/minute"
	return os.getenv("RATE_LIMIT_LOGIN", "5/minute")