
import threading
import time
from loguru import logger
import sys
from pathlib import Path

# Ensure 'main' can be imported if it's in parent dir
# Actually integrated_inspector is in utils/, main.py is in parent.
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Swap Order: Import main FIRST to ensure models is loaded in sys.modules
from main import DiagnosisSystem
from models import InspectionData, DiagnosisState, InspectionResult, InspectionPoint

class IntegratedInspector:
    """
    Wrapper class to run DiagnosisSystem from web server.
    """
    def __init__(self):
        logger.info("🚀 [IntegratedInspector] Initializing DiagnosisSystem...")
        self.system = DiagnosisSystem()

    def run_loop(self):
        """
        Background loop to process tasks.
        Aliases to DiagnosisSystem.run() but we might want to capture it to prevent exit.
        """
        logger.info("🚀 [IntegratedInspector] Background Loop Started")
        try:
            self.system.run()
        except Exception as e:
            logger.error(f"❌ IntegratedInspector Loop Crashed: {e}")
