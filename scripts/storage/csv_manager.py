"""
Unified CSV read/write operations.
"""
import csv
from pathlib import Path
from typing import List, Type, TypeVar, Dict, Any

T = TypeVar('T')


class CSVManager:
    """Manage CSV files with automatic serialization."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def read(self, filename: str, model_class: Type[T]) -> List[T]:
        """
        Read CSV file and return list of model instances.
        
        Args:
            filename: CSV filename (without path)
            model_class: Dataclass to instantiate for each row
            
        Returns:
            List of model instances
        """
        filepath = self.data_dir / filename
        if not filepath.exists():
            return []
        
        results = []
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert empty strings to None for optional fields
                cleaned = {k: v if v != '' else None for k, v in row.items()}
                # Filter to only fields in the dataclass
                valid_fields = {f.name for f in model_class.__dataclass_fields__.values()}
                filtered = {k: v for k, v in cleaned.items() if k in valid_fields}
                results.append(model_class(**filtered))
        
        return results
    
    def write(self, filename: str, data: List[T], fieldnames: List[str] = None):
        """
        Write list of model instances to CSV.
        
        Args:
            filename: CSV filename (without path)
            data: List of dataclass instances
            fieldnames: Optional explicit column order
        """
        if not data:
            return
        
        filepath = self.data_dir / filename
        
        # Infer fieldnames from first item if not provided
        if fieldnames is None:
            fieldnames = list(data[0].__dataclass_fields__.keys())
        
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in data:
                row = {
                    k: getattr(item, k, '') or ''
                    for k in fieldnames
                }
                writer.writerow(row)
    
    def read_dicts(self, filename: str) -> List[Dict[str, str]]:
        """Read CSV as list of dictionaries."""
        filepath = self.data_dir / filename
        if not filepath.exists():
            return []
        
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            return list(csv.DictReader(f))
    
    def write_dicts(self, filename: str, data: List[Dict[str, Any]], fieldnames: List[str]):
        """Write list of dictionaries to CSV."""
        if not data:
            return
        
        filepath = self.data_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
