# main.py

import logging
import sys
import uuid
import warnings
import time

# Suppress the SQLite date warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)

# Imports
try:
    from sns2f_framework.core.orchestrator import Orchestrator
    from sns2f_framework.core.trace_manager import trace_manager
except ImportError as e:
    print(f"\n[CRITICAL] Import Error: {e}")
    print("Are you running this from the D:\\Code\\Turiya directory?")
    sys.exit(1)

def print_banner():
    # Clear screen command (optional, makes it cleaner)
    # print("\033[H\033[J", end="") 
    print(r"""
   _____   _   __  _____   ___    _____ 
  / ___/  / | / / / ___/  |__ \  / ___/ 
  \__ \  /  |/ /  \__ \   __/ / / /_    
 ___/ / / /|  /  ___/ /  / __/ / __/    
/____/ /_/ |_/  /____/  /____/ /_/      
                                        
Self-Evolving Neuro-Symbolic Swarm Framework
v7.0 - "Conscious"
--------------------------------------------
Commands:
  /start   - Start autonomous learning
  /stop    - Stop learning
  /ask ... - Ask a question
  /trace   - Show the thought process
  /consolidate - Crystallize concepts
  /sleep   - Perform maintenance cycle
  /set mode [strict|safe|open] - Change crawler safety
  /flush   - Clear crawler queue
  /quit    - Exit
--------------------------------------------
    """, flush=True)

def handle_response(response_text: str):
    print(f"\n[🤖 AI]: {response_text}\n>> ", end="", flush=True)

def main():
    print("--- Initializing System ---")
    orc = Orchestrator()
    
    print("--- Starting Agents ---")
    orc.start()
    
    print("--- Waiting for Neural Engine (10s) ---")
    # Increased wait time to let the LLM load cleanly before we take over the screen
    time.sleep(10.0)
    
    print_banner()
    
    last_req_id = None

    try:
        while True:
            # Force flush to ensure the prompt is visible
            sys.stdout.flush()
            user_input = input(">> ").strip()
            
            if not user_input: continue
                
            if user_input.lower() == "/quit":
                print("Exiting...")
                break
                
            elif user_input.lower() == "/start":
                orc.start_learning()
                print("[System]: Swarm is now learning...")
                
            elif user_input.lower() == "/stop":
                orc.stop_learning()
                print("[System]: Learning paused.")

            elif user_input.lower() == "/consolidate":
                print("[System]: Mining concepts...")
                count = orc.consolidate_knowledge()
                print(f"[System]: Crystallized {count} concepts.")

            elif user_input.lower() == "/trace":
                if last_req_id:
                    print(trace_manager.get_trace(last_req_id))
                else:
                    print("[System]: No history available.")
            
            elif user_input.lower().startswith("/ask"):
                query = user_input[5:].strip()
                if query:
                    last_req_id = str(uuid.uuid4())
                    print(f"[System]: Thinking...")
                    orc.ask(query, handle_response, request_id=last_req_id)
                else:
                    print("[System]: Ask what?")

            elif user_input.lower() == "/flush":
                orc.flush_perception()
                print("[System]: Crawler queue cleared. Ready for new sources.")
            
            elif user_input.lower() == "/sleep":
                print("[System]: Initiating Sleep Cycle (Memory Pruning)...")
                stats = orc.sleep_cycle()
                
                print(f"[System]: Sleep Complete.")
                print(f"   - Noise Deleted:     {stats.get('deleted_noise', 0)}")
                print(f"   - Duplicates Merged: {stats.get('merged_duplicates', 0)}")
                print(f"   - Concepts Formed:   {stats.get('concepts_formed', 0)}")
                print(f"   - New Categories:    {stats.get('abstractions_formed', 0)}")
            
            elif user_input.lower().startswith("/set mode"):
                parts = user_input.split()
                if len(parts) == 3:
                    mode = parts[2].lower()
                    if mode in ["strict", "safe", "open"]:
                        orc.set_crawl_mode(mode)
                        print(f"[System]: Crawl mode set to {mode.upper()}.")
                    else:
                        print("[System]: Invalid mode. Use: strict, safe, open")
                else:
                    print("[System]: Usage: /set mode [strict|safe|open]")

            else:
                print("[System]: Unknown command.")

    except KeyboardInterrupt:
        print("\n[System]: Force quit.")
    except Exception as e:
        print(f"\n[CRITICAL ERROR]: {e}")
    finally:
        print("--- Stopping Orchestrator ---")
        orc.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()