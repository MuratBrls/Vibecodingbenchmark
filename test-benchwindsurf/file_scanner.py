#!/usr/bin/env python3
"""
OOP-based Advanced File Scanner
Professional file system analysis and management tool
"""

import os
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Iterator
from dataclasses import dataclass, asdict
from enum import Enum
import mimetypes
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class FileType(Enum):
    """File type classifications"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    DOCUMENT = "document"
    CODE = "code"
    EXECUTABLE = "executable"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ScanMode(Enum):
    """Scanning modes"""
    QUICK = "quick"
    DEEP = "deep"
    CUSTOM = "custom"


@dataclass
class FileInfo:
    """Comprehensive file information"""
    path: str
    name: str
    size: int
    extension: str
    file_type: FileType
    mime_type: str
    created_time: datetime
    modified_time: datetime
    accessed_time: datetime
    hash_md5: Optional[str] = None
    hash_sha256: Optional[str] = None
    is_hidden: bool = False
    is_readonly: bool = False
    permissions: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['created_time'] = self.created_time.isoformat()
        data['modified_time'] = self.modified_time.isoformat()
        data['accessed_time'] = self.accessed_time.isoformat()
        return data


@dataclass
class ScanResult:
    """Scan result container"""
    total_files: int
    total_directories: int
    total_size: int
    file_types: Dict[str, int]
    largest_files: List[FileInfo]
    scan_duration: float
    errors: List[str]


class FileAnalyzer:
    """File analysis engine"""
    
    def __init__(self):
        self.type_mappings = {
            FileType.TEXT: ['.txt', '.md', '.log', '.csv', '.json', '.xml', '.yaml', '.yml'],
            FileType.IMAGE: ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.ico'],
            FileType.VIDEO: ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
            FileType.AUDIO: ['.mp3', '.flac', '.wav', '.aac', '.ogg', '.wma', '.m4a'],
            FileType.ARCHIVE: ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
            FileType.DOCUMENT: ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt'],
            FileType.CODE: ['.py', '.js', '.html', '.css', '.cpp', '.c', '.java', '.php', '.rb', '.go'],
            FileType.EXECUTABLE: ['.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm', '.app'],
            FileType.SYSTEM: ['.sys', '.dll', '.so', '.dylib', '.ini', '.cfg', '.conf']
        }
    
    def analyze_file(self, file_path: Path, calculate_hash: bool = False) -> FileInfo:
        """Analyze single file"""
        try:
            stat = file_path.stat()
            
            # Determine file type
            file_type = self._determine_file_type(file_path)
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            mime_type = mime_type or "application/octet-stream"
            
            # Calculate hashes if requested
            hash_md5 = None
            hash_sha256 = None
            if calculate_hash:
                hash_md5, hash_sha256 = self._calculate_hashes(file_path)
            
            # Check file attributes
            is_hidden = file_path.name.startswith('.')
            is_readonly = not os.access(file_path, os.W_OK)
            
            # Get permissions (Unix-style)
            permissions = oct(stat.st_mode)[-3:] if hasattr(stat, 'st_mode') else ""
            
            return FileInfo(
                path=str(file_path),
                name=file_path.name,
                size=stat.st_size,
                extension=file_path.suffix.lower(),
                file_type=file_type,
                mime_type=mime_type,
                created_time=datetime.fromtimestamp(stat.st_ctime),
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                accessed_time=datetime.fromtimestamp(stat.st_atime),
                hash_md5=hash_md5,
                hash_sha256=hash_sha256,
                is_hidden=is_hidden,
                is_readonly=is_readonly,
                permissions=permissions
            )
            
        except Exception as e:
            raise Exception(f"Error analyzing {file_path}: {e}")
    
    def _determine_file_type(self, file_path: Path) -> FileType:
        """Determine file type based on extension"""
        ext = file_path.suffix.lower()
        
        for file_type, extensions in self.type_mappings.items():
            if ext in extensions:
                return file_type
        
        return FileType.UNKNOWN
    
    def _calculate_hashes(self, file_path: Path) -> Tuple[str, str]:
        """Calculate MD5 and SHA256 hashes"""
        hash_md5 = hashlib.md5()
        hash_sha256 = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
                    hash_sha256.update(chunk)
            
            return hash_md5.hexdigest(), hash_sha256.hexdigest()
        except Exception:
            return "", ""


class FileScanner:
    """Main file scanner class"""
    
    def __init__(self, max_workers: int = 4):
        self.analyzer = FileAnalyzer()
        self.max_workers = max_workers
        self.scan_results: List[FileInfo] = []
        self.errors: List[str] = []
    
    def scan_directory(self, 
                      directory: str, 
                      mode: ScanMode = ScanMode.QUICK,
                      recursive: bool = True,
                      include_hidden: bool = False,
                      calculate_hashes: bool = False,
                      file_filter: Optional[str] = None) -> ScanResult:
        """Scan directory and return results"""
        start_time = time.time()
        path = Path(directory)
        
        if not path.exists():
            raise Exception(f"Directory does not exist: {directory}")
        
        print(f"🔍 Scanning: {directory}")
        print(f"📊 Mode: {mode.value}, Recursive: {recursive}")
        
        # Collect files to scan
        files_to_scan = self._collect_files(path, recursive, include_hidden, file_filter)
        
        # Scan files
        self.scan_results = []
        self.errors = []
        
        if mode == ScanMode.QUICK:
            self._scan_quick(files_to_scan, calculate_hashes)
        elif mode == ScanMode.DEEP:
            self._scan_deep(files_to_scan, calculate_hashes)
        else:
            self._scan_custom(files_to_scan, calculate_hashes)
        
        # Calculate statistics
        scan_duration = time.time() - start_time
        result = self._generate_statistics(scan_duration)
        
        print(f"✅ Scan completed in {scan_duration:.2f}s")
        print(f"📁 Files: {result.total_files}, Directories: {result.total_directories}")
        print(f"💾 Total size: {self._format_size(result.total_size)}")
        
        return result
    
    def _collect_files(self, 
                      path: Path, 
                      recursive: bool, 
                      include_hidden: bool,
                      file_filter: Optional[str]) -> List[Path]:
        """Collect files to scan"""
        files = []
        directories = 0
        
        try:
            if recursive:
                for item in path.rglob("*"):
                    if item.is_file():
                        if not include_hidden and item.name.startswith('.'):
                            continue
                        if file_filter and file_filter not in item.name:
                            continue
                        files.append(item)
                    elif item.is_dir():
                        directories += 1
            else:
                for item in path.iterdir():
                    if item.is_file():
                        if not include_hidden and item.name.startswith('.'):
                            continue
                        if file_filter and file_filter not in item.name:
                            continue
                        files.append(item)
                    elif item.is_dir():
                        directories += 1
                        
        except Exception as e:
            self.errors.append(f"Error collecting files: {e}")
        
        self.total_directories = directories
        return files
    
    def _scan_quick(self, files: List[Path], calculate_hashes: bool):
        """Quick scan - single threaded"""
        for file_path in files:
            try:
                file_info = self.analyzer.analyze_file(file_path, calculate_hashes=False)
                self.scan_results.append(file_info)
            except Exception as e:
                self.errors.append(f"Error scanning {file_path.name}: {e}")
    
    def _scan_deep(self, files: List[Path], calculate_hashes: bool):
        """Deep scan - multi threaded with hashes"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.analyzer.analyze_file, file_path, calculate_hashes): file_path 
                for file_path in files
            }
            
            for future in as_completed(futures):
                file_path = futures[future]
                try:
                    file_info = future.result()
                    self.scan_results.append(file_info)
                except Exception as e:
                    self.errors.append(f"Error scanning {file_path.name}: {e}")
    
    def _scan_custom(self, files: List[Path], calculate_hashes: bool):
        """Custom scan - balanced approach"""
        # Process in batches
        batch_size = 100
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            self._scan_deep(batch, calculate_hashes)
    
    def _generate_statistics(self, scan_duration: float) -> ScanResult:
        """Generate scan statistics"""
        total_files = len(self.scan_results)
        total_size = sum(f.size for f in self.scan_results)
        
        # File type statistics
        file_types = {}
        for file_info in self.scan_results:
            file_type = file_info.file_type.value
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        # Largest files
        largest_files = sorted(self.scan_results, key=lambda x: x.size, reverse=True)[:10]
        
        return ScanResult(
            total_files=total_files,
            total_directories=getattr(self, 'total_directories', 0),
            total_size=total_size,
            file_types=file_types,
            largest_files=largest_files,
            scan_duration=scan_duration,
            errors=self.errors
        )
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def export_results(self, filename: str = "scan_results.json") -> bool:
        """Export scan results to JSON"""
        try:
            export_data = {
                "scan_date": datetime.now().isoformat(),
                "total_files": len(self.scan_results),
                "files": [file_info.to_dict() for file_info in self.scan_results],
                "errors": self.errors
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"📄 Results exported to: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return False
    
    def find_duplicates(self) -> Dict[str, List[FileInfo]]:
        """Find duplicate files based on hash"""
        hash_groups = {}
        
        for file_info in self.scan_results:
            if file_info.hash_md5:
                hash_groups.setdefault(file_info.hash_md5, []).append(file_info)
        
        # Filter to only duplicates
        duplicates = {h: files for h, files in hash_groups.items() if len(files) > 1}
        
        print(f"🔍 Found {len(duplicates)} duplicate groups")
        return duplicates
    
    def get_file_statistics(self) -> Dict[str, any]:
        """Get detailed file statistics"""
        if not self.scan_results:
            return {}
        
        sizes = [f.size for f in self.scan_results]
        
        return {
            "total_files": len(self.scan_results),
            "total_size": sum(sizes),
            "average_size": sum(sizes) / len(sizes),
            "largest_file": max(sizes),
            "smallest_file": min(sizes),
            "file_types": dict(Counter(f.file_type.value for f in self.scan_results)),
            "hidden_files": sum(1 for f in self.scan_results if f.is_hidden),
            "readonly_files": sum(1 for f in self.scan_results if f.is_readonly)
        }


def main():
    """Main execution function"""
    import argparse
    from collections import Counter
    
    parser = argparse.ArgumentParser(description="Advanced File Scanner")
    parser.add_argument("directory", help="Directory to scan")
    parser.add_argument("--mode", choices=["quick", "deep", "custom"], default="quick", help="Scan mode")
    parser.add_argument("--no-recursive", action="store_true", help="Don't scan recursively")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden files")
    parser.add_argument("--calculate-hashes", action="store_true", help="Calculate file hashes")
    parser.add_argument("--filter", help="Filter files by name")
    parser.add_argument("--export", help="Export results to file")
    parser.add_argument("--find-duplicates", action="store_true", help="Find duplicate files")
    
    args = parser.parse_args()
    
    try:
        # Initialize scanner
        scanner = FileScanner()
        
        # Perform scan
        result = scanner.scan_directory(
            directory=args.directory,
            mode=ScanMode(args.mode),
            recursive=not args.no_recursive,
            include_hidden=args.include_hidden,
            calculate_hashes=args.calculate_hashes,
            file_filter=args.filter
        )
        
        # Display results
        print(f"\n📊 SCAN RESULTS:")
        print(f"Files: {result.total_files}")
        print(f"Directories: {result.total_directories}")
        print(f"Total Size: {scanner._format_size(result.total_size)}")
        print(f"Scan Duration: {result.scan_duration:.2f}s")
        
        print(f"\n📁 File Types:")
        for file_type, count in sorted(result.file_types.items()):
            print(f"  {file_type}: {count}")
        
        if result.largest_files:
            print(f"\n📈 Largest Files:")
            for i, file_info in enumerate(result.largest_files[:5], 1):
                print(f"  {i}. {file_info.name} ({scanner._format_size(file_info.size)})")
        
        if result.errors:
            print(f"\n⚠️  Errors ({len(result.errors)}):")
            for error in result.errors[:5]:
                print(f"  {error}")
        
        # Find duplicates if requested
        if args.find_duplicates:
            duplicates = scanner.find_duplicates()
            if duplicates:
                print(f"\n🔄 Duplicate Files:")
                for hash_val, files in list(duplicates.items())[:5]:
                    print(f"  Hash: {hash_val[:8]}...")
                    for file_info in files:
                        print(f"    {file_info.path}")
        
        # Export results if requested
        if args.export:
            scanner.export_results(args.export)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
        # Force write attempt
        try:
            with open("scanner_error.log", "w") as f:
                f.write(f"Scanner error: {e}\n")
                f.write(f"Time: {datetime.now()}\n")
            print("🔧 Error logged to scanner_error.log")
        except:
            print("🔧 Could not write error log")


if __name__ == "__main__":
    main()
