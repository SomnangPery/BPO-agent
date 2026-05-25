import logging
import os
from ic_agent.config import KNOWLEDGE_DIR
from ic_agent.rag_pipeline import build_index

logging.basicConfig(level=logging.INFO)

def main():
    print("Building Project-Only IC Agent Knowledge Index...")
    if not os.path.exists(KNOWLEDGE_DIR):
        print(f"Knowledge directory not found: {KNOWLEDGE_DIR}")
        return
        
    build_index(KNOWLEDGE_DIR)
    print("Index built successfully.")

if __name__ == "__main__":
    main()
