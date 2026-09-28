import os
import runpy

os.environ["RAG_PROVIDER"] = "gemini"
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "groq_app.py"))
