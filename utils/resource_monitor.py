import psutil
import os
import threading
import time
import gc
from utils.logging_utils import Logging

logger = Logging()

class ResourceMonitor:
    def __init__(self, memory_threshold=80, cpu_threshold=90, check_interval=60):
        """
        Monitor system resources and clean up when needed
        
        Args:
            memory_threshold: Memory usage percentage threshold (default: 80%)
            cpu_threshold: CPU usage percentage threshold (default: 90%)
            check_interval: Check interval in seconds (default: 60)
        """
        self.memory_threshold = memory_threshold
        self.cpu_threshold = cpu_threshold
        self.check_interval = check_interval
        self.monitoring = False
        self._monitor_thread = None
        
    def start_monitoring(self):
        """Start resource monitoring in background thread"""
        if self.monitoring:
            logger.warning("Resource monitor already running")
            return
            
        self.monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Resource monitor started")
        
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Resource monitor stopped")
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Check memory usage
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > self.memory_threshold:
                    logger.warning(f"High memory usage detected: {memory_percent:.1f}%")
                    self._cleanup_resources()
                    
                # Check CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent > self.cpu_threshold:
                    logger.warning(f"High CPU usage detected: {cpu_percent:.1f}%")
                    
                # Check disk usage
                disk_percent = psutil.disk_usage('/').percent
                if disk_percent > 90:
                    logger.warning(f"High disk usage detected: {disk_percent:.1f}%")
                    self._cleanup_temp_files()
                    
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in resource monitor: {e}")
                time.sleep(self.check_interval)
                
    def _cleanup_resources(self):
        """Cleanup resources to free memory"""
        try:
            logger.info("Starting resource cleanup...")
            
            # Force garbage collection
            collected = gc.collect()
            logger.info(f"Garbage collected {collected} objects")
            
            # Get memory info after cleanup
            memory_percent = psutil.virtual_memory().percent
            logger.info(f"Memory usage after cleanup: {memory_percent:.1f}%")
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")
            
    def _cleanup_temp_files(self):
        """Cleanup temporary files"""
        try:
            temp_files = [
                "temp_avatar.png",
                "notification_canvas.png",
                "temp.mp4"
            ]
            
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        logger.info(f"Removed temp file: {temp_file}")
                    except Exception as e:
                        logger.error(f"Failed to remove {temp_file}: {e}")
                        
            # Cleanup old cache files in modules/cache
            cache_dir = "modules/cache"
            if os.path.exists(cache_dir):
                for root, dirs, files in os.walk(cache_dir):
                    for file in files:
                        if file.startswith("temp_") or file.startswith("cache_"):
                            file_path = os.path.join(root, file)
                            try:
                                # Remove files older than 1 hour
                                if time.time() - os.path.getmtime(file_path) > 3600:
                                    os.remove(file_path)
                                    logger.info(f"Removed old cache file: {file_path}")
                            except Exception as e:
                                logger.error(f"Failed to remove {file_path}: {e}")
                                
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")
            
    def get_resource_stats(self):
        """Get current resource statistics"""
        try:
            stats = {
                'memory_percent': psutil.virtual_memory().percent,
                'cpu_percent': psutil.cpu_percent(interval=1),
                'disk_percent': psutil.disk_usage('/').percent,
                'process_memory_mb': psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            }
            return stats
        except Exception as e:
            logger.error(f"Error getting resource stats: {e}")
            return None

# Global instance
resource_monitor = ResourceMonitor(memory_threshold=80, cpu_threshold=90, check_interval=60)
