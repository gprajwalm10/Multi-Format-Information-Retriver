import os
import runpy
import sys

script_directory = os.path.dirname(os.path.abspath(__file__))
os.environ["RAG_PROVIDER"] = "anthropic"
sys.path[:] = [
	entry for entry in sys.path
	if os.path.abspath(entry or os.curdir) != script_directory
]
try:
	runpy.run_path(os.path.join(script_directory, "groq_app.py"))
finally:
	sys.path.insert(0, script_directory)
