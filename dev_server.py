#!/usr/bin/env python3
"""
🔥 Hot Reload Development Server for Inspection System
Monitors file changes and automatically restarts the inspection system
"""
import os
import sys
import time
import subprocess
import signal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class InspectionReloadHandler(FileSystemEventHandler):
    def __init__(self, main_script="main.py"):
        self.main_script = main_script
        self.process = None
        self.restart_delay = 1  # seconds
        self.last_restart = 0
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Only reload Python files
        if not event.src_path.endswith('.py'):
            return
            
        # Skip cache and test files
        if any(skip in event.src_path for skip in ['__pycache__', '.pyc', 'test_', 'conftest']):
            return
            
        current_time = time.time()
        if current_time - self.last_restart < self.restart_delay:
            return
            
        print(f"🔄 File changed: {event.src_path}")
        self.restart_server()
        self.last_restart = current_time
        
    def restart_server(self):
        """Restart the inspection system"""
        if self.process:
            print("🛑 Stopping previous instance...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        
        print(f"🚀 Starting {self.main_script}...")
        env = os.environ.copy()
        env.update({
            'INSPECTION_ENV': 'development',
            'INSPECTION_DEBUG': '1',
            'PYTHONPATH': os.getcwd()
        })
        
        self.process = subprocess.Popen([
            sys.executable, self.main_script, '--debug'
        ], env=env)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hot Reload Development Server")
    parser.add_argument('--script', default='main.py', help='Main script to run')
    parser.add_argument('--watch-dir', default='.', help='Directory to watch')
    args = parser.parse_args()
    
    event_handler = InspectionReloadHandler(args.script)
    observer = Observer()
    observer.schedule(event_handler, args.watch_dir, recursive=True)
    
    print(f"👀 Watching for changes in: {args.watch_dir}")
    print("🔄 Starting initial server...")
    
    # Start initial server
    event_handler.restart_server()
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
        print("\n👋 Development server stopped")
    
    observer.join()

if __name__ == "__main__":
    main()
