# [model_manager.py] - Optimized Model Loading and Memory Management
import os
import gc
import pickle
import hashlib
from pathlib import Path
from typing import Dict, Optional, Any, Union
from functools import lru_cache
import psutil
import cv2
import numpy as np
from loguru import logger
from ultralytics import YOLO

from config_optimized import config

class ModelManager:
    """Optimized model manager with lazy loading, caching, and memory monitoring"""
    
    def __init__(self):
        self._models: Dict[str, Any] = {}
        self._model_configs: Dict[str, Any] = {}
        self._usage_count: Dict[str, int] = {}
        self._memory_usage: Dict[str, float] = {}
        self.process = psutil.Process()
        self._setup_optimizations()
    
    def _setup_optimizations(self):
        """Apply CPU and memory optimizations"""
        # Set OpenCV thread count
        cv2.setNumThreads(config.CPU_OPT["opencv_threads"])
        
        # Set numpy threads
        os.environ["OMP_NUM_THREADS"] = str(config.CPU_OPT["numpy_threads"])
        os.environ["MKL_NUM_THREADS"] = str(config.CPU_OPT["numpy_threads"])
        
        # Enable memory monitoring
        if config.MONITORING.get("log_memory_usage", True):
            logger.info("🔍 Memory monitoring enabled")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def _check_memory_limit(self) -> bool:
        """Check if memory usage exceeds limit"""
        current_memory = self._get_memory_usage()
        max_memory = config.PERFORMANCE["max_memory_mb"]
        
        if current_memory > max_memory * config.MEMORY_OPT["memory_warning_threshold"]:
            logger.warning(f"⚠️ High memory usage: {current_memory:.1f}MB / {max_memory}MB")
            return False
        
        return True
    
    def _cleanup_memory(self):
        """Force garbage collection and memory cleanup"""
        gc.collect()
        
        # Unload least recently used models if memory is high
        if not self._check_memory_limit():
            self._unload_least_used_models()
        
        logger.debug(f"🧹 Memory cleanup. Current: {self._get_memory_usage():.1f}MB")
    
    def _unload_least_used_models(self):
        """Unload models with lowest usage count to free memory"""
        if not self._models:
            return
        
        # Sort models by usage count
        sorted_models = sorted(self._usage_count.items(), key=lambda x: x[1])
        
        # Unload least used models until memory is acceptable
        for model_name, usage in sorted_models:
            if model_name in self._models:
                logger.info(f"🗑️ Unloading model {model_name} (usage: {usage})")
                del self._models[model_name]
                self._usage_count.pop(model_name, None)
                self._memory_usage.pop(model_name, None)
                
                if self._check_memory_limit():
                    break
        
        self._cleanup_memory()
    
    def _get_model_cache_key(self, model_path: Union[str, Path]) -> str:
        """Generate cache key for model"""
        model_str = str(model_path)
        # Include file modification time for cache invalidation
        if os.path.exists(model_str):
            mtime = os.path.getmtime(model_str)
            model_str += f"_{mtime}"
        
        return hashlib.md5(model_str.encode()).hexdigest()
    
    def _load_model_optimized(self, model_name: str) -> YOLO:
        """Load YOLO model with optimizations"""
        model_config = config.get_model_config(model_name)
        model_path = model_config["path"]
        
        logger.info(f"📦 Loading model {model_name} from {model_path}")
        
        # Load model with optimizations
        model = YOLO(str(model_path))
        
        # Apply model optimizations
        if model_config.get("half_precision", True):
            # Use FP16 if available to reduce memory
            try:
                if hasattr(model, 'model') and hasattr(model.model, 'half'):
                    model.model.half()
                    logger.debug(f"🔧 Applied half precision to {model_name}")
            except Exception as e:
                logger.warning(f"⚠️ Could not apply half precision: {e}")
        
        # Store model config for later use
        self._model_configs[model_name] = model_config
        
        # Estimate memory usage
        initial_memory = self._get_memory_usage()
        self._models[model_name] = model
        self._usage_count[model_name] = 1
        self._memory_usage[model_name] = self._get_memory_usage() - initial_memory
        
        logger.info(f"✅ Model {model_name} loaded successfully "
                   f"(~{self._memory_usage[model_name]:.1f}MB)")
        
        return model
    
    def get_model(self, model_name: str) -> YOLO:
        """Get model with lazy loading and caching"""
        # Check if model is already loaded
        if model_name in self._models:
            self._usage_count[model_name] += 1
            return self._models[model_name]
        
        # Check memory before loading
        if not self._check_memory_limit():
            self._cleanup_memory()
        
        # Load new model
        model = self._load_model_optimized(model_name)
        
        # Enforce concurrent model limit
        max_models = config.PERFORMANCE["max_concurrent_models"]
        if len(self._models) > max_models:
            self._unload_least_used_models()
        
        return model
    
    def predict_optimized(self, model_name: str, image: np.ndarray, 
                         **kwargs) -> list:
        """Optimized prediction with memory management"""
        model = self.get_model(model_name)
        model_config = self._model_configs.get(model_name, {})
        
        # Prepare image - resize if too large
        max_size = config.MEMORY_OPT["max_image_size"]
        h, w = image.shape[:2]
        if h > max_size[1] or w > max_size[0]:
            # Calculate scaling factor
            scale = min(max_size[0] / w, max_size[1] / h)
            new_w, new_h = int(w * scale), int(h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            logger.debug(f"🖼️ Resized image from {(w,h)} to {(new_w,new_h)}")
        
        # Set default parameters
        conf = kwargs.get("conf", model_config.get("conf_threshold", 0.25))
        max_det = kwargs.get("max_det", model_config.get("max_det", 50))
        device = kwargs.get("device", model_config.get("device", "cpu"))
        verbose = kwargs.get("verbose", False)
        
        try:
            # Perform prediction
            results = model.predict(
                image,
                conf=conf,
                max_det=max_det,
                device=device,
                verbose=verbose,
                **{k: v for k, v in kwargs.items() if k not in ["conf", "max_det", "device", "verbose"]}
            )
            
            # Log performance metrics
            if config.MONITORING.get("enable_profiling", False):
                logger.debug(f"🔍 {model_name} prediction completed in {len(results)} results")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Prediction failed for {model_name}: {e}")
            raise
    
    def preload_models(self, model_names: list = None):
        """Preload commonly used models"""
        if model_names is None:
            model_names = ["classifier", "ag_pose"]
        
        logger.info(f"🚀 Preloading models: {model_names}")
        
        for model_name in model_names:
            try:
                self.get_model(model_name)
            except Exception as e:
                logger.error(f"❌ Failed to preload {model_name}: {e}")
    
    def unload_model(self, model_name: str):
        """Unload specific model to free memory"""
        if model_name in self._models:
            logger.info(f"🗑️ Unloading model {model_name}")
            del self._models[model_name]
            self._usage_count.pop(model_name, None)
            self._memory_usage.pop(model_name, None)
            self._cleanup_memory()
    
    def unload_all_models(self):
        """Unload all models to free maximum memory"""
        logger.info("🗑️ Unloading all models")
        self._models.clear()
        self._usage_count.clear()
        self._memory_usage.clear()
        self._cleanup_memory()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory statistics"""
        total_memory = self._get_memory_usage()
        model_memory = sum(self._memory_usage.values())
        
        return {
            "total_memory_mb": total_memory,
            "model_memory_mb": model_memory,
            "other_memory_mb": total_memory - model_memory,
            "loaded_models": list(self._models.keys()),
            "model_usage": self._usage_count.copy(),
            "process_memory_percent": self.process.memory_percent()
        }
    
    def optimize_memory_for_next_task(self):
        """Optimize memory before processing next task"""
        if config.PERFORMANCE.get("garbage_collection_interval", 10) > 0:
            self._cleanup_memory()
    
    @lru_cache(maxsize=128)
    def get_optimized_image(self, image_path: str) -> np.ndarray:
        """Load and optimize image with caching"""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")
        
        # Apply memory optimizations
        max_size = config.MEMORY_OPT["max_image_size"]
        h, w = img.shape[:2]
        
        if h > max_size[1] or w > max_size[0]:
            scale = min(max_size[0] / w, max_size[1] / h)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        return img

# Global model manager instance
model_manager = ModelManager()

# Convenience functions for backward compatibility
def get_classifier():
    """Get classifier model"""
    return model_manager.get_model("classifier")

def get_ag_inspector():
    """Get AG inspector model"""
    return model_manager.get_model("ag_pose")

def predict_with_classifier(image, **kwargs):
    """Predict using classifier with optimizations"""
    return model_manager.predict_optimized("classifier", image, **kwargs)

def predict_with_ag_inspector(image, **kwargs):
    """Predict using AG inspector with optimizations"""
    return model_manager.predict_optimized("ag_pose", image, **kwargs)