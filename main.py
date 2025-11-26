# main.py

import logging
import sys
import time
import threading

# Configure Logging (Clean output for the CLI)
# We set the level to INFO to suppress the noisy DEBUG logs during normal use.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)

# Import the Orchestrator
from sns2f_framework.core.orchestrator import Orchestrator

def print_banner():
    print(r"""
   _____   _   __  _____   ___    _____ 
  / ___/  / | / / / ___/  |__ \  / ___/ 
  \__ \  /  |/ /  \__ \   __/ / / /_    
 ___/ / / /|  /  ___/ /  / __/ / __/    
/____/ /_/ |_/  /____/  /____/ /_/      
                                        
Self-Evolving Neuro-Symbolic Swarm Framework
v0.1 - "Genesis"
--------------------------------------------
Commands:
  /start   - Start autonomous learning (read from sources)
  /stop    - Stop learning (consolidate only)
  /ask ... - Ask a question (e.g., /ask What is sparse activation?)
  /quit    - Shutdown and exit
--------------------------------------------
    """)

def handle_response(response_text: str):
    """Callback to print the AI's answer."""
    print(f"\n[🤖 AI]: {response_text}\n>> ", end="", flush=True)

def main():
    orc = Orchestrator()
    orc.start()
    
    print_banner()
    
    try:
        while True:
            # We use a simple input loop
            user_input = input(">> ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() == "/quit":
                print("Exiting...")
                break
                
            elif user_input.lower() == "/start":
                orc.start_learning()
                print("[System]: Swarm is now learning from sources...")
                
            elif user_input.lower() == "/stop":
                orc.stop_learning()
                print("[System]: Learning paused. Consolidating memories...")
                
            elif user_input.lower().startswith("/ask"):
                query = user_input[5:].strip()
                if query:
                    print(f"[System]: Thinking...")
                    orc.ask(query, handle_response)
                else:
                    print("[System]: Please provide a question.")
            
            else:
                print("[System]: Unknown command. Use /start, /stop, /ask, or /quit.")

    except KeyboardInterrupt:
        print("\n[System]: Force quit detected.")
    finally:
        orc.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()