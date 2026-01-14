#!/usr/bin/env python3
"""
⚡ Development-Optimized Configuration for Industrial Inspection System
Focus on rapid iteration, hot reload, and minimal resource usage
"""
import os
from pathlib import Path
from typing import Dict, Any

class DevelopmentConfig:
    """Development-optimized configuration"""
    
    # 🚀 Performance Settings for Development
    PERFORMANCE = {
        "enable_model_caching": False,  # Disable for hot reload
        "lazy_loading": True,          # Load models on demand
        "max_concurrent_models": 1,    # Limit memory usage
        "image_batch_size": 1,         # Process one at a time
        "garbage_collection_interval": 5,  # More frequent GC
        "max_memory_mb": 300,          # Reasonable dev limit
        "enable_profiling": True,      # Development profiling
    }
    
    # 📁 Development Paths
    BASE_DIR = Path(__file__).parent
    PATHS = {
        "base_dir": "/home/kiie/synology/Projects/R25IA04/Inspection_and_Diagnosis/Inspection_Raw_DATA_Dockerd/robot-control-system_inspection_data(docker X)",
        "excel_file": "/home/kiie/synology/Projects/R25IA04/Inspection_point_Labeling.xlsx",
        "models_dir": BASE_DIR / "models",
        "cache_dir": BASE_DIR / "cache",
        "temp_dir": "/tmp/inspection_cache",
        "dev_data_dir": BASE_DIR / "examples" / "test_data",  # Small test dataset
    }
    
    # 🤖 Model Configuration - Development Optimized
    MODEL_CONFIG = {
        "classifier": str(BASE_DIR / "models" / "classifier" / "weights" / "best.pt"),
        "ag_pose": str(BASE_DIR / "models" / "ag_inspector" / "weights" / "best.pt"),
        "confidence_threshold": 0.5,  # Higher for faster processing
        "iou_threshold": 0.45,
        "image_size": 640,  # Smaller for faster processing
        "device": "cpu",  # CPU for development (change to 'cuda' for GPU)
    }
    
    # 🔍 Debug Settings
    DEBUG = {
        "enable_detailed_logging": True,
        "save_intermediate_results": True,
        "show_detection_boxes": True,
        "enable_step_by_step": True,
        "log_confidence_scores": True,
        "visualize_matching_process": True,
    }
    
    # 🧪 Testing Configuration
    TESTING = {
        "use_mock_models": os.getenv("USE_MOCK_MODELS", "false").lower() == "true",
        "small_test_dataset": True,
        "enable_parallel_testing": False,  # Sequential for easier debugging
        "timeout_per_test": 30,  # seconds
    }
    
    # 🔄 Hot Reload Configuration
    HOT_RELOAD = {
        "enabled": True,
        "watch_patterns": ["*.py", "*.yaml", "*.yml"],
        "ignore_patterns": ["__pycache__", "*.pyc", ".git", "test_results"],
        "restart_delay": 1.0,  # seconds
    }
    
    # 📊 Monitoring Configuration
    MONITORING = {
        "enable_performance_monitor": True,
        "log_interval": 1.0,  # seconds
        "save_metrics": True,
        "metrics_file": "dev_performance.json",
    }
    
    # 🌐 Development Server
    DEV_SERVER = {
        "host": "localhost",
        "port": 8080,
        "auto_reload": True,
        "debug_mode": True,
    }
    
    @classmethod
    def setup_environment(cls):
        """Setup development environment"""
        # Create necessary directories
        for path in cls.PATHS.values():
            if isinstance(path, Path):
                path.mkdir(parents=True, exist_ok=True)
        
        # Set environment variables
        os.environ["INSPECTION_ENV"] = "development"
        os.environ["INSPECTION_DEBUG"] = "1"
        os.environ["PYTHONPATH"] = str(cls.BASE_DIR)
        
        # Optimize Python for development
        os.environ["PYTHONOPTIMIZE"] = "0"  # No optimization for debugging
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"  # No .pyc files
        
        print("✅ Development environment configured")
    
    @classmethod
    def get_model_config(cls, model_type: str) -> Dict[str, Any]:
        """Get model-specific configuration"""
        base_config = cls.MODEL_CONFIG.copy()
        
        if model_type == "development":
            base_config.update({
                "confidence_threshold": 0.3,  # Lower for more detections during dev
                "image_size": 512,  # Smaller for faster processing
                "max_det": 100,  # Limit detections
            })
        elif model_type == "testing":
            base_config.update({
                "confidence_threshold": 0.1,  # Very low for comprehensive testing
                "device": "cpu",
            })
        
        return base_config

# Auto-setup when imported
DevelopmentConfig.setup_environment()

# Export configuration
config = DevelopmentConfig()
