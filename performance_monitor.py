#!/usr/bin/env python3
"""
📊 Real-time Performance Monitor for Inspection System
Monitors CPU, memory, and model performance during development
"""
import psutil
import time
import threading
from dataclasses import dataclass
from typing import List, Dict
import json
from pathlib import Path

@dataclass
class PerformanceMetrics:
    timestamp: float
    cpu_percent: float
    memory_mb: float
    gpu_memory_mb: float = 0
    models_loaded: int = 0
    images_processed: int = 0
    avg_processing_time: float = 0

class PerformanceMonitor:
    def __init__(self, log_file="performance_log.json"):
        self.log_file = Path(log_file)
        self.metrics: List[PerformanceMetrics] = []
        self.process = psutil.Process()
        self.monitoring = False
        self.models_loaded = 0
        self.images_processed = 0
        self.processing_times: List[float] = []
        
    def start_monitoring(self, interval=1.0):
        """Start performance monitoring"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        print("📊 Performance monitoring started")
        
    def stop_monitoring(self):
        """Stop monitoring and save results"""
        self.monitoring = False
        self._save_metrics()
        print(f"📊 Performance metrics saved to {self.log_file}")
        
    def _monitor_loop(self, interval):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                cpu_percent = self.process.cpu_percent()
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                metrics = PerformanceMetrics(
                    timestamp=time.time(),
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    models_loaded=self.models_loaded,
                    images_processed=self.images_processed,
                    avg_processing_time=sum(self.processing_times[-10:]) / len(self.processing_times) if self.processing_times else 0
                )
                
                self.metrics.append(metrics)
                
                # Real-time console output
                print(f"📊 CPU: {cpu_percent:5.1f}% | Memory: {memory_mb:6.1f}MB | Models: {self.models_loaded} | Images: {self.images_processed}")
                
                time.sleep(interval)
            except Exception as e:
                print(f"⚠️ Monitoring error: {e}")
                
    def log_model_load(self, model_name: str):
        """Log when a model is loaded"""
        self.models_loaded += 1
        print(f"🤖 Model loaded: {model_name} (Total: {self.models_loaded})")
        
    def log_image_processing(self, processing_time: float):
        """Log image processing time"""
        self.images_processed += 1
        self.processing_times.append(processing_time)
        print(f"🖼️ Image processed in {processing_time:.3f}s (Total: {self.images_processed})")
        
    def _save_metrics(self):
        """Save metrics to file"""
        data = []
        for m in self.metrics:
            data.append({
                'timestamp': m.timestamp,
                'cpu_percent': m.cpu_percent,
                'memory_mb': m.memory_mb,
                'models_loaded': m.models_loaded,
                'images_processed': m.images_processed,
                'avg_processing_time': m.avg_processing_time
            })
        
        with open(self.log_file, 'w') as f:
            json.dump(data, f, indent=2)
            
    def get_summary(self) -> Dict:
        """Get performance summary"""
        if not self.metrics:
            return {}
            
        cpu_values = [m.cpu_percent for m in self.metrics]
        memory_values = [m.memory_mb for m in self.metrics]
        
        return {
            'avg_cpu': sum(cpu_values) / len(cpu_values),
            'max_cpu': max(cpu_values),
            'avg_memory': sum(memory_values) / len(memory_values),
            'max_memory': max(memory_values),
            'total_models': self.models_loaded,
            'total_images': self.images_processed,
            'avg_processing_time': sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        }

# Global instance for easy access
monitor = PerformanceMonitor()

def get_monitor():
    return monitor
