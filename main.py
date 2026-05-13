# pyrefly: ignore [missing-import]
import uvicorn
import os
import sys

# Ensure the current directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("Starting BioCredit Agent Prototype...")
    uvicorn.run("biocredit_agent.app:app", host="127.0.0.1", port=8000, reload=True)
