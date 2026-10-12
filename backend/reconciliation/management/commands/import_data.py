import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from reconciliation.models import Location, SystemARecord, SystemBEntry


def normalize_reference(raw_ref: str) -> str:
    """
    Normalizes dirty record references:
    - Strips leading/trailing whitespace
    - Uppercases letters (rec1034 -> REC1034)
    - Removes whitespace around hyphens ('REC - 1070' -> 'REC-1070')
    - If purely digits (e.g. '1112'), prefixes with 'REC-' -> 'REC-1112'
    """
    if not raw_ref:
        return ""
    
    cleaned = raw_ref.strip().upper()
    
    # Remove spaces around hyphens: 'REC - 1070' -> 'REC-1070'
    cleaned = re.sub(r'\s*-\s*', '-', cleaned)
    
    # If case was 'REC1034' without hyphen, convert to 'REC-1034'
    if re.match(r'^REC\d+$', cleaned):
        cleaned = f"REC-{cleaned[3:]}"
    
    # If purely digits like '1112', prefix with 'REC-'
    elif cleaned.isdigit():
        cleaned = f"REC-{cleaned}"
        
    return cleaned


def parse_decimal(raw_val: str):
    """
    Safely parses decimal numbers:
    - Blank or None -> None (not 0.00!)
    - Removes commas (supports standard '125,400.00' and Indian '1,25,400.00')
    - Returns None if completely unparseable string
    """
    if raw_val is None:
        return None
    val_str = str(raw_val).strip()
    if not val_str:
        return None
    
    # Strip currency commas
    val_clean = val_str.replace(',', '')
    try:
        return Decimal(val_clean)
    except (InvalidOperation, ValueError):
        return None


def parse_date(raw_date: str):
    """
    Returns valid date string YYYY-MM-DD or None.
    """
    if not raw_date:
        return None
    d = raw_date.strip()
    return d if d else None


class Command(BaseCommand):
    help = "Safely imports locations.csv, system_a.csv, and system_b.csv without losing dirty data."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dir',
            type=str,
            default=None,
            help='Path to Datasets directory containing the CSV files'
        )

    def handle(self, *args, **options):
        # Locate Datasets folder (either from command arg, or parent of backend)
        if options['dir']:
            datasets_dir = Path(options['dir'])
        else:
            datasets_dir = settings.BASE_DIR.parent / 'Datasets'
            if not datasets_dir.exists():
                datasets_dir = settings.BASE_DIR / 'Datasets'

        self.stdout.write(self.style.NOTICE(f"Loading CSV files from: {datasets_dir.resolve()}"))

        # Clear existing data to ensure clean, repeatable imports
        Location.objects.all().delete()
        SystemARecord.objects.all().delete()
        SystemBEntry.objects.all().delete()

        # 1. Import locations.csv
        loc_path = datasets_dir / 'locations.csv'
        loc_count = 0
        with open(loc_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                loc_id = row['location_id'].strip()
                if loc_id:
                    Location.objects.create(
                        location_id=loc_id,
                        org_id=row['org_id'].strip(),
                        location_name=row['location_name'].strip()
                    )
                    loc_count += 1
        self.stdout.write(self.style.SUCCESS(f"Successfully imported {loc_count} locations."))

        # 2. Import system_a.csv
        a_path = datasets_dir / 'system_a.csv'
        a_count = 0
        with open(a_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rec_id = row['record_id'].strip()
                raw_base = row.get('base_value', '')
                raw_adj = row.get('adjustment', '')
                raw_total = row.get('total_value', '')
                raw_date = row.get('event_date', '')
                raw_actor = row.get('actor_id', '').strip()

                SystemARecord.objects.create(
                    record_id=rec_id,
                    location_id=row['location_id'].strip(),
                    event_date=parse_date(raw_date),
                    raw_event_date=raw_date,
                    category_code=row.get('category_code', '').strip(),
                    actor_id=raw_actor if raw_actor else None,
                    base_value=parse_decimal(raw_base),
                    raw_base_value=raw_base,
                    adjustment=parse_decimal(raw_adj),
                    raw_adjustment=raw_adj,
                    total_value=parse_decimal(raw_total),
                    raw_total_value=raw_total,
                    state=row.get('state', '').strip(),
                )
                a_count += 1
        self.stdout.write(self.style.SUCCESS(f"Successfully imported {a_count} System A records."))

        # 3. Import system_b.csv
        b_path = datasets_dir / 'system_b.csv'
        b_count = 0
        with open(b_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry_id = row['entry_id'].strip()
                raw_ref = row.get('record_ref', '')
                raw_val = row.get('value', '')
                raw_date = row.get('recorded_on', '')

                SystemBEntry.objects.create(
                    entry_id=entry_id,
                    record_ref_raw=raw_ref,
                    record_ref_normalized=normalize_reference(raw_ref),
                    location_id=row['location_id'].strip(),
                    recorded_on=parse_date(raw_date),
                    raw_recorded_on=raw_date,
                    value=parse_decimal(raw_val),
                    raw_value=raw_val,
                    label=row.get('label', '').strip(),
                )
                b_count += 1
        self.stdout.write(self.style.SUCCESS(f"Successfully imported {b_count} System B entries."))

        self.stdout.write(self.style.SUCCESS(
            f"Import complete! DB verification: Locations={loc_count}, System A={a_count}, System B={b_count}"
        ))
