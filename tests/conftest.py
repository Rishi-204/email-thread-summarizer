import os
import sys

# Offline tests: the client is created at import time but never called.
os.environ.setdefault("GEMINI_API_KEY", "dummy-key-for-offline-tests")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
