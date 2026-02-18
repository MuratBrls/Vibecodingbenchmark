import os
import psutil
import logging
from dataclasses import dataclass, asdict
from typing import List, Optional

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """Data class to hold system resource usage."""
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float

@dataclass
class FileMetadata:
    """Data class to hold file information."""
    path: str
    size_mb: float
    error: Optional[str] = None

class LocalOptimizer:
    """
    Analyzes the local file system for large files and monitors system resources.
    """

    def __init__(self, target_directory: str, size_threshold_mb: float = 100.0):
        """
        Initialize the LocalOptimizer.

        Args:
            target_directory (str): The directory to scan.
            size_threshold_mb (float): Threshold in MB to consider a file 'large'.
        """
        self.target_directory = target_directory
        self.size_threshold_mb = size_threshold_mb
        self._validate_directory()

    def _validate_directory(self):
        """Validates if the target directory exists."""
        if not os.path.exists(self.target_directory):
            raise FileNotFoundError(f"Directory not found: {self.target_directory}")

    def get_system_load(self) -> SystemMetrics:
        """
        Captures current system CPU and RAM usage using psutil.
        
        Returns:
            SystemMetrics: An object containing CPU and RAM statistics.
        """
        try:
            # CPU usage
            cpu = psutil.cpu_percent(interval=None)
            
            # RAM usage
            mem = psutil.virtual_memory()
            ram_percent = mem.percent
            ram_used_gb = round(mem.used / (1024 ** 3), 2)
            ram_total_gb = round(mem.total / (1024 ** 3), 2)

            metrics = SystemMetrics(
                cpu_percent=cpu,
                ram_percent=ram_percent,
                ram_used_gb=ram_used_gb,
                ram_total_gb=ram_total_gb
            )
            logger.info(f"System Load: CPU={cpu}%, RAM={ram_percent}% ({ram_used_gb}/{ram_total_gb} GB)")
            return metrics
        except Exception as e:
            logger.error(f"Failed to retrieve system metrics: {e}")
            raise

    def find_large_files(self) -> List[FileMetadata]:
        """
        Scans the target directory for files larger than the threshold.

        Returns:
            List[FileMetadata]: A list of detected large files or files with access errors.
        """
        large_files = []
        logger.info(f"Scanning '{self.target_directory}' for files larger than {self.size_threshold_mb} MB...")

        files_processed = 0
        errors_encountered = 0

        for root, _, files in os.walk(self.target_directory):
            for filename in files:
                file_path = os.path.join(root, filename)
                files_processed += 1
                
                try:
                    # Get file stats
                    file_stat = os.stat(file_path)
                    size_mb = file_stat.st_size / (1024 * 1024)

                    if size_mb >= self.size_threshold_mb:
                        logger.info(f"Large file found: {filename} ({size_mb:.2f} MB)")
                        large_files.append(FileMetadata(
                            path=file_path,
                            size_mb=round(size_mb, 2)
                        ))

                except PermissionError:
                    logger.warning(f"Permission denied: {file_path}")
                    errors_encountered += 1
                    large_files.append(FileMetadata(path=file_path, size_mb=0, error="PermissionDenied"))
                except OSError as e:
                    logger.error(f"OS Error accessing {file_path}: {e}")
                    errors_encountered += 1
                    large_files.append(FileMetadata(path=file_path, size_mb=0, error=str(e)))
                except Exception as e:
                    logger.error(f"Unexpected error on {file_path}: {e}")
                    errors_encountered += 1

        logger.info(f"Scan complete. Processed {files_processed} files. Found {len([f for f in large_files if not f.error])} large files. Errors: {errors_encountered}")
        return large_files

if __name__ == "__main__":
    # Example usage
    target_dir = os.getcwd()
    optimizer = LocalOptimizer(target_dir)
    
    # 1. Check System Load
    optimizer.get_system_load()
    
    # 2. Find Large Files (Scanning current directory for demo functionality)
    optimizer.find_large_files()
