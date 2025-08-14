#!/usr/bin/env python3
"""
Simple launcher script for the Graph RAG Chatbot Streamlit app.
This makes it easier to run the Streamlit version directly.
"""

import subprocess
import sys
import os

def main():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the main chatbot script
    chatbot_path = os.path.join(script_dir, "src", "graph_rag_chatbot.py")
    
    if not os.path.exists(chatbot_path):
        print(f"Error: Could not find graph_rag_chatbot.py at {chatbot_path}")
        sys.exit(1)
    
    print("🚀 Launching Graph RAG Chatbot with Streamlit...")
    print("📱 The app will open in your default browser")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Try different ways to launch Streamlit
        streamlit_commands = [
            ["streamlit", "run", chatbot_path, "--server.headless", "false", "--server.port", "8501", "--theme.base", "light"],
            ["python3", "-m", "streamlit", "run", chatbot_path, "--server.headless", "false", "--server.port", "8501", "--theme.base", "light"],
            ["python3.11", "-m", "streamlit", "run", chatbot_path, "--server.headless", "false", "--server.port", "8501", "--theme.base", "light"],
            ["python", "-m", "streamlit", "run", chatbot_path, "--server.headless", "false", "--server.port", "8501", "--theme.base", "light"]
        ]
        
        streamlit_launched = False
        for cmd in streamlit_commands:
            try:
                subprocess.run(cmd, check=True)
                streamlit_launched = True
                break
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        
        if not streamlit_launched:
            print("❌ Error: Streamlit not found or failed to launch.")
            print("📦 Please install Streamlit:")
            print("   pip3 install streamlit")
            print("   # or")
            print("   python3 -m pip install streamlit")
            print("   # or")
            print("   python3.11 -m pip install streamlit")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n👋 Shutting down Streamlit server...")

if __name__ == "__main__":
    main()