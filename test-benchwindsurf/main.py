#!/usr/bin/env python3
"""
Self-Organizing Media Library System
Advanced OOP-based intelligent media management
"""

import os
import json
import sqlite3
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import mimetypes
import re
from collections import defaultdict


class AutoCategory(Enum):
    """Automatic categorization types"""
    MUSIC = "music"
    MOVIES = "movies"
    TV_SHOWS = "tv_shows"
    PODCASTS = "podcasts"
    PHOTOS = "photos"
    DOCUMENTS = "documents"
    GAMES = "games"
    SOFTWARE = "software"
    ARCHIVES = "archives"
    OTHER = "other"


class ProcessingStatus(Enum):
    """File processing status"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    CATEGORIZING = "categorizing"
    ORGANIZING = "organizing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SmartMetadata:
    """Intelligent metadata extraction"""
    title: str
    detected_category: AutoCategory
    confidence_score: float
    extracted_tags: List[str]
    file_signature: str
    content_analysis: Dict[str, Any]
    auto_generated_name: Optional[str] = None
    
    def __post_init__(self):
        if not self.extracted_tags:
            self.extracted_tags = []


@dataclass
class MediaFile:
    """Enhanced media file representation"""
    id: Optional[int]
    original_path: str
    organized_path: Optional[str]
    file_name: str
    file_size: int
    file_hash: str
    mime_type: str
    category: AutoCategory
    metadata: SmartMetadata
    status: ProcessingStatus
    created_at: datetime
    processed_at: Optional[datetime]
    priority: int = 0
    
    def __post_init__(self):
        if self.processed_at is None:
            self.processed_at = datetime.now()


class IntelligentAnalyzer:
    """AI-powered content analyzer"""
    
    def __init__(self):
        self.patterns = {
            AutoCategory.MUSIC: [
                r'.*\.(mp3|flac|wav|aac|ogg|wma|m4a)$',
                r'.*(music|song|track|album|artist).*',
                r'.*\d{4}.*',  # Year patterns
            ],
            AutoCategory.MOVIES: [
                r'.*\.(mp4|avi|mkv|mov|wmv|flv|webm|m4v)$',
                r'.*(movie|film|cinema).*',
                r'.*\d{4}.*',  # Year patterns
                r'.*(1080p|720p|4K|HD|BluRay).*',
            ],
            AutoCategory.TV_SHOWS: [
                r'.*(S\d{2}E\d{2}|season.*episode).*',
                r'.*(tv|show|series|episode).*',
                r'.*\d{1,2}x\d{2}.*',
            ],
            AutoCategory.PODCASTS: [
                r'.*(podcast|episode|ep).*\.(mp3|wav|m4a)$',
                r'.*(talk|radio|interview).*',
            ],
            AutoCategory.PHOTOS: [
                r'.*\.(jpg|jpeg|png|gif|bmp|tiff|webp|raw)$',
                r'.*(photo|image|pic|picture|selfie).*',
            ],
            AutoCategory.DOCUMENTS: [
                r'.*\.(pdf|doc|docx|txt|rtf|odt|epub|mobi)$',
                r'.*(document|book|manual|guide).*',
            ],
            AutoCategory.GAMES: [
                r'.*\.(iso|exe|zip|rar|7z).*game.*',
                r'.*(game|gaming|play).*',
            ],
            AutoCategory.SOFTWARE: [
                r'.*\.(exe|msi|dmg|pkg|deb|rpm)$',
                r'.*(software|app|application|program).*',
            ],
            AutoCategory.ARCHIVES: [
                r'.*\.(zip|rar|7z|tar|gz|bz2|xz)$',
            ]
        }
        
        self.content_keywords = {
            AutoCategory.MUSIC: ['audio', 'sound', 'music', 'song', 'track', 'album'],
            AutoCategory.MOVIES: ['movie', 'film', 'cinema', 'theater', 'dvd', 'blu'],
            AutoCategory.TV_SHOWS: ['season', 'episode', 'series', 'tv', 'show'],
            AutoCategory.PODCASTS: ['podcast', 'talk', 'radio', 'interview', 'discussion'],
            AutoCategory.PHOTOS: ['photo', 'image', 'picture', 'camera', 'shot'],
            AutoCategory.DOCUMENTS: ['document', 'text', 'book', 'manual', 'guide'],
            AutoCategory.GAMES: ['game', 'play', 'gaming', 'steam', 'epic'],
            AutoCategory.SOFTWARE: ['software', 'app', 'application', 'program', 'tool'],
            AutoCategory.ARCHIVES: ['archive', 'compressed', 'backup', 'collection']
        }
    
    def analyze_file(self, file_path: Path) -> SmartMetadata:
        """Analyze file and extract intelligent metadata"""
        file_name = file_path.name.lower()
        file_ext = file_path.suffix.lower()
        
        # Pattern matching
        category_scores = defaultdict(float)
        
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, file_name, re.IGNORECASE):
                    category_scores[category] += 1.0
        
        # Content keyword matching
        for category, keywords in self.content_keywords.items():
            for keyword in keywords:
                if keyword in file_name:
                    category_scores[category] += 0.5
        
        # File extension influence
        ext_mapping = {
            '.mp3': AutoCategory.MUSIC, '.flac': AutoCategory.MUSIC, '.wav': AutoCategory.MUSIC,
            '.mp4': AutoCategory.MOVIES, '.avi': AutoCategory.MOVIES, '.mkv': AutoCategory.MOVIES,
            '.jpg': AutoCategory.PHOTOS, '.png': AutoCategory.PHOTOS, '.gif': AutoCategory.PHOTOS,
            '.pdf': AutoCategory.DOCUMENTS, '.doc': AutoCategory.DOCUMENTS,
            '.zip': AutoCategory.ARCHIVES, '.rar': AutoCategory.ARCHIVES, '.7z': AutoCategory.ARCHIVES,
        }
        
        if file_ext in ext_mapping:
            category_scores[ext_mapping[file_ext]] += 2.0
        
        # Determine best category
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            detected_category = best_category[0]
            confidence = min(best_category[1] / 3.0, 1.0)  # Normalize to 0-1
        else:
            detected_category = AutoCategory.OTHER
            confidence = 0.0
        
        # Extract tags
        tags = self._extract_tags(file_name)
        
        # Generate smart filename
        smart_name = self._generate_smart_name(file_path, detected_category)
        
        # Content analysis
        content_analysis = {
            "file_size_tier": self._get_size_tier(file_path.stat().st_size),
            "date_patterns": self._extract_date_patterns(file_name),
            "quality_indicators": self._extract_quality_indicators(file_name),
            "language_hints": self._detect_language(file_name)
        }
        
        return SmartMetadata(
            title=file_path.stem,
            detected_category=detected_category,
            confidence_score=confidence,
            extracted_tags=tags,
            file_signature=self._generate_file_signature(file_path),
            content_analysis=content_analysis,
            auto_generated_name=smart_name
        )
    
    def _extract_tags(self, filename: str) -> List[str]:
        """Extract meaningful tags from filename"""
        # Common patterns
        tags = []
        
        # Year extraction
        year_match = re.search(r'\b(19|20)\d{2}\b', filename)
        if year_match:
            tags.append(f"year_{year_match.group()}")
        
        # Quality indicators
        quality_patterns = {
            '4K': r'\b4k|2160p\b',
            'HD': r'\b720p|hd\b',
            'Full_HD': r'\b1080p|fullhd\b',
            'BluRay': r'\bbluray|bdrip\b',
            'DVD': r'\bdvd|dvdrip\b'
        }
        
        for quality, pattern in quality_patterns.items():
            if re.search(pattern, filename, re.IGNORECASE):
                tags.append(quality)
        
        return tags
    
    def _generate_smart_name(self, file_path: Path, category: AutoCategory) -> str:
        """Generate intelligent filename"""
        original_name = file_path.stem
        
        # Clean up common patterns
        clean_name = re.sub(r'[._-]+', ' ', original_name)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
        
        # Remove common junk
        junk_patterns = [
            r'\b(www\.)?[\w-]+\.(com|net|org|tv)\b',
            r'\b\d{3,4}p\b',
            r'\b(xvid|x264|h264|h265)\b',
            r'\b(ac3|dts|aac)\b'
        ]
        
        for pattern in junk_patterns:
            clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE)
        
        return clean_name.strip()
    
    def _generate_file_signature(self, file_path: Path) -> str:
        """Generate unique file signature"""
        stat = file_path.stat()
        return f"{file_path.suffix}_{stat.st_size}_{int(stat.st_mtime)}"
    
    def _get_size_tier(self, size: int) -> str:
        """Categorize file size"""
        mb = size / (1024 * 1024)
        if mb < 10:
            return "small"
        elif mb < 100:
            return "medium"
        elif mb < 1000:
            return "large"
        else:
            return "huge"
    
    def _extract_date_patterns(self, filename: str) -> List[str]:
        """Extract date patterns from filename"""
        patterns = []
        
        # YYYY-MM-DD
        date_match = re.search(r'\b(\d{4})[-/]?(\d{2})[-/]?(\d{2})\b', filename)
        if date_match:
            patterns.append(f"date_{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}")
        
        return patterns
    
    def _extract_quality_indicators(self, filename: str) -> List[str]:
        """Extract quality indicators"""
        indicators = []
        
        if re.search(r'\b(4k|uhd|2160p)\b', filename, re.IGNORECASE):
            indicators.append("4K")
        if re.search(r'\b(1080p|fullhd|fhd)\b', filename, re.IGNORECASE):
            indicators.append("Full_HD")
        if re.search(r'\b(720p|hd)\b', filename, re.IGNORECASE):
            indicators.append("HD")
        
        return indicators
    
    def _detect_language(self, filename: str) -> List[str]:
        """Detect language hints from filename"""
        languages = []
        
        lang_patterns = {
            'english': r'\b(eng|english)\b',
            'turkish': r'\b(turk|tr|turkish)\b',
            'french': r'\b(fr|french)\b',
            'german': r'\b(de|german)\b',
            'spanish': r'\b(es|spanish)\b'
        }
        
        for lang, pattern in lang_patterns.items():
            if re.search(pattern, filename, re.IGNORECASE):
                languages.append(lang)
        
        return languages


class SelfOrganizingLibrary:
    """Main self-organizing media library system"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.analyzer = IntelligentAnalyzer()
        self.processed_files: List[MediaFile] = []
        self.category_structure = {
            AutoCategory.MUSIC: "Music/{artist}/{album}",
            AutoCategory.MOVIES: "Movies/{year}/{quality}",
            AutoCategory.TV_SHOWS: "TV Shows/{series}/Season {season}",
            AutoCategory.PODCASTS: "Podcasts/{show}",
            AutoCategory.PHOTOS: "Photos/{year_month}",
            AutoCategory.DOCUMENTS: "Documents/{type}",
            AutoCategory.GAMES: "Games/{platform}",
            AutoCategory.SOFTWARE: "Software/{category}",
            AutoCategory.ARCHIVES: "Archives/{type}",
            AutoCategory.OTHER: "Other"
        }
    
    def scan_and_organize(self, source_directory: str = None) -> Dict[str, Any]:
        """Main organization process"""
        source = source_directory or str(self.base_path)
        print(f"🚀 Starting self-organization of: {source}")
        
        # Scan for files
        all_files = self._scan_files(source)
        print(f"📁 Found {len(all_files)} files to process")
        
        # Process each file
        processed_count = 0
        for file_path in all_files:
            try:
                media_file = self._process_file(file_path)
                if media_file:
                    self.processed_files.append(media_file)
                    processed_count += 1
                    print(f"✅ Processed: {file_path.name} → {media_file.category.value}")
            except Exception as e:
                print(f"❌ Error processing {file_path.name}: {e}")
        
        # Create directory structure
        self._create_directory_structure()
        
        # Organize files
        organized_count = self._organize_files()
        
        # Generate report
        report = self._generate_report()
        
        print(f"🎉 Organization complete!")
        print(f"📊 Processed: {processed_count}, Organized: {organized_count}")
        
        return report
    
    def _scan_files(self, directory: str) -> List[Path]:
        """Scan directory for media files"""
        path = Path(directory)
        files = []
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                # Skip system files and directories
                if file_path.suffix.lower() in ['.py', '.db', '.json', '.txt', '.md']:
                    continue
                files.append(file_path)
        
        return files
    
    def _process_file(self, file_path: Path) -> Optional[MediaFile]:
        """Process individual file"""
        # Analyze file
        metadata = self.analyzer.analyze_file(file_path)
        
        # Calculate file hash
        file_hash = self._calculate_hash(file_path)
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"
        
        # Create media file object
        media_file = MediaFile(
            id=None,
            original_path=str(file_path),
            organized_path=None,
            file_name=file_path.name,
            file_size=file_path.stat().st_size,
            file_hash=file_hash,
            mime_type=mime_type,
            category=metadata.detected_category,
            metadata=metadata,
            status=ProcessingStatus.COMPLETED,
            created_at=datetime.fromtimestamp(file_path.stat().st_ctime),
            priority=self._calculate_priority(metadata)
        )
        
        return media_file
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate file hash"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def _calculate_priority(self, metadata: SmartMetadata) -> int:
        """Calculate processing priority"""
        priority = 0
        
        # High confidence gets higher priority
        priority += int(metadata.confidence_score * 10)
        
        # Certain categories get priority
        if metadata.detected_category in [AutoCategory.MOVIES, AutoCategory.TV_SHOWS]:
            priority += 5
        
        return priority
    
    def _create_directory_structure(self):
        """Create organized directory structure"""
        for category in AutoCategory:
            category_path = self.base_path / category.value
            category_path.mkdir(exist_ok=True)
        
        print("📁 Directory structure created")
    
    def _organize_files(self) -> int:
        """Organize files into appropriate directories"""
        organized_count = 0
        
        for media_file in sorted(self.processed_files, key=lambda x: -x.priority):
            try:
                target_path = self._get_target_path(media_file)
                
                if target_path and target_path != media_file.original_path:
                    # Create target directory if needed
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Handle name conflicts
                    final_path = self._handle_name_conflicts(target_path)
                    
                    # Move file
                    shutil.move(media_file.original_path, str(final_path))
                    
                    # Update media file
                    media_file.organized_path = str(final_path)
                    organized_count += 1
                    
                    print(f"📦 Organized: {media_file.file_name} → {final_path.relative_to(self.base_path)}")
            
            except Exception as e:
                print(f"❌ Error organizing {media_file.file_name}: {e}")
        
        return organized_count
    
    def _get_target_path(self, media_file: MediaFile) -> Optional[Path]:
        """Get target path for media file"""
        category = media_file.category
        base_dir = self.base_path / category.value
        
        # Generate smart path based on category and metadata
        if category == AutoCategory.MUSIC:
            artist = "Unknown Artist"
            album = "Unknown Album"
            
            # Try to extract artist/album from metadata
            if media_file.metadata.extracted_tags:
                for tag in media_file.metadata.extracted_tags:
                    if tag.startswith("year_"):
                        year = tag.replace("year_", "")
                        base_dir = base_dir / year
            
            return base_dir / artist / album / media_file.file_name
        
        elif category == AutoCategory.MOVIES:
            year = "Unknown Year"
            quality = "Unknown Quality"
            
            for tag in media_file.metadata.extracted_tags:
                if tag.startswith("year_"):
                    year = tag.replace("year_", "")
                elif tag in ["4K", "Full_HD", "HD"]:
                    quality = tag
            
            return base_dir / year / quality / media_file.file_name
        
        elif category == AutoCategory.PHOTOS:
            # Organize by date
            date_str = datetime.now().strftime("%Y-%m")
            return base_dir / date_str / media_file.file_name
        
        else:
            # Default organization
            return base_dir / media_file.file_name
    
    def _handle_name_conflicts(self, target_path: Path) -> Path:
        """Handle file name conflicts"""
        if not target_path.exists():
            return target_path
        
        counter = 1
        stem = target_path.stem
        suffix = target_path.suffix
        
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = target_path.parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate organization report"""
        category_stats = defaultdict(int)
        total_size = 0
        
        for media_file in self.processed_files:
            category_stats[media_file.category.value] += 1
            total_size += media_file.file_size
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(self.processed_files),
            "total_size": total_size,
            "categories": dict(category_stats),
            "organization_rate": len([f for f in self.processed_files if f.organized_path]) / len(self.processed_files) * 100 if self.processed_files else 0,
            "average_confidence": sum(f.metadata.confidence_score for f in self.processed_files) / len(self.processed_files) if self.processed_files else 0
        }
        
        # Save report
        report_path = self.base_path / "organization_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📄 Report saved to: {report_path}")
        return report


def main():
    """Main execution function"""
    if len(os.sys.argv) < 2:
        print("Usage: python main.py run <description>")
        return
    
    description = " ".join(os.sys.argv[2:])
    print(f"🎯 Task: {description}")
    print("=" * 60)
    
    # Initialize self-organizing library
    base_path = r"C:\Users\egule\Documents\github\Vibecodingbenchmark\test-benchwindsurf"
    library = SelfOrganizingLibrary(base_path)
    
    try:
        # Run organization
        report = library.scan_and_organize()
        
        # Display results
        print(f"\n📊 ORGANIZATION RESULTS:")
        print(f"Total Files Processed: {report['total_files']}")
        print(f"Total Size: {report['total_size'] / (1024**3):.2f} GB")
        print(f"Organization Rate: {report['organization_rate']:.1f}%")
        print(f"Average Confidence: {report['average_confidence']:.2f}")
        
        print(f"\n📁 Categories:")
        for category, count in report['categories'].items():
            print(f"  {category}: {count} files")
        
        print(f"\n🎉 Self-organizing media library completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during organization: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
