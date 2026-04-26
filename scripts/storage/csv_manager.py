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
                filtered = {}
                for k, v in cleaned.items():
                    if k in valid_fields:
                        # Handle None values for numeric fields
                        field_info = model_class.__dataclass_fields__.get(k)
                        if field_info and 'Optional[float]' in str(field_info.type):
                            try:
                                filtered[k] = float(v) if v is not None else None
                            except (ValueError, TypeError):
                                filtered[k] = None
                        else:
                            filtered[k] = v
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

    def merge_by_place_id(
        self,
        filename: str,
        new_restaurants: List[Any],
        model_class: Type[T],
    ) -> List[T]:
        """
        Merge new restaurants into existing CSV by place_id.
        Existing entries with matching place_id are updated (all fields overwritten
        except AI-extracted fields like happy_hour_times, menu_summary if new data is empty).
        New entries are appended. Untouched entries keep their old freshness_date.

        Fallback: entries without place_id are matched by restaurant_name to prevent
        data loss during migration from old schema (no place_id) to new schema.

        Returns the merged list.
        """
        existing = self.read(filename, model_class)
        existing_by_id: Dict[str, Any] = {}
        legacy_by_name: Dict[str, Any] = {}  # For entries without place_id
        for r in existing:
            pid = getattr(r, 'place_id', '') or ''
            if pid:
                existing_by_id[pid] = r
            else:
                name = getattr(r, 'restaurant_name', '') or ''
                if name:
                    legacy_by_name[name] = r

        merged_by_id: Dict[str, Any] = dict(existing_by_id)
        merged_legacy: Dict[str, Any] = dict(legacy_by_name)
        updated_count = 0
        added_count = 0
        preserved_legacy_count = len(legacy_by_name)

        AI_FIELDS = ('happy_hour_times', 'menu_summary', 'cheapest_drink',
                     'cheapest_drink_price', 'cheapest_food', 'cheapest_food_price')

        for new_r in new_restaurants:
            pid = getattr(new_r, 'place_id', '') or ''
            name = getattr(new_r, 'restaurant_name', '') or ''
            matched = False

            # Try match by place_id first
            if pid and pid in merged_by_id:
                old_r = merged_by_id[pid]
                for field in model_class.__dataclass_fields__:
                    if field == 'place_id':
                        continue
                    new_val = getattr(new_r, field, None)
                    if field in AI_FIELDS and not new_val:
                        continue
                    if new_val is not None:
                        setattr(old_r, field, new_val)
                old_r.freshness_date = new_r.freshness_date
                updated_count += 1
                matched = True
            # Fallback: match legacy entries by name
            elif name and name in merged_legacy:
                old_r = merged_legacy[name]
                for field in model_class.__dataclass_fields__:
                    if field == 'place_id':
                        continue
                    new_val = getattr(new_r, field, None)
                    if field in AI_FIELDS and not new_val:
                        continue
                    if new_val is not None:
                        setattr(old_r, field, new_val)
                # Upgrade legacy entry with place_id
                old_r.place_id = pid
                old_r.freshness_date = new_r.freshness_date
                updated_count += 1
                matched = True

            if not matched:
                if pid:
                    merged_by_id[pid] = new_r
                else:
                    merged_by_id[id(new_r)] = new_r
                added_count += 1

        merged = list(merged_by_id.values()) + list(merged_legacy.values())
        self.write(filename, merged)
        print(f"  CSV merge: {updated_count} updated, {added_count} added, "
              f"{preserved_legacy_count - len(merged_legacy)} legacy upgraded, "
              f"{len(merged)} total")
        return merged
