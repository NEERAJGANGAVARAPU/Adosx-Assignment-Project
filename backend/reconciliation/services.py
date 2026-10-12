from decimal import Decimal
from typing import List, Dict, Any
from reconciliation.models import Location, SystemARecord, SystemBEntry


def run_reconciliation() -> List[Dict[str, Any]]:
    """
    Core reconciliation engine.
    Compares System A records against System B entries and detects all disagreements.
    Returns a list of structured issue dictionaries.
    """
    # 1. Build Location -> Org lookup
    locations_map = {loc.location_id: loc.org_id for loc in Location.objects.all()}

    # 2. Fetch all System A records
    system_a_records = list(SystemARecord.objects.all())
    system_a_by_id = {rec.record_id: rec for rec in system_a_records}

    # 3. Group System B entries by their normalized reference
    system_b_entries = list(SystemBEntry.objects.all())
    system_b_by_ref: Dict[str, List[SystemBEntry]] = {}
    for entry in system_b_entries:
        ref = entry.record_ref_normalized
        system_b_by_ref.setdefault(ref, []).append(entry)

    disagreements = []

    # -------------------------------------------------------------
    # Check System A records against System B
    # -------------------------------------------------------------
    for a_rec in system_a_records:
        rec_id = a_rec.record_id
        b_list = system_b_by_ref.get(rec_id, [])
        issues = []

        # Issue 1: MISSING_SYSTEM_B_ENTRY
        if len(b_list) == 0:
            issues.append("MISSING_SYSTEM_B_ENTRY")
        
        # Issue 2: DUPLICATE_SYSTEM_B_ENTRY
        elif len(b_list) > 1:
            issues.append("DUPLICATE_SYSTEM_B_ENTRY")

        # Issue 3: VALUE_MISMATCH
        if len(b_list) == 1:
            b_entry = b_list[0]
            # Blank/missing value in B or unequal decimal values
            if b_entry.value is None or a_rec.total_value != b_entry.value:
                issues.append("VALUE_MISMATCH")
        elif len(b_list) > 1:
            # Check both cases:
            # 1. Are they duplicate entries with the same value as System A?
            # 2. Or is it a split entry whose sum equals System A (like REC-1055)?
            b_total = sum((b.value for b in b_list if b.value is not None), Decimal('0'))
            has_matching_copy = any(b.value == a_rec.total_value for b in b_list)
            
            # Only flag VALUE_MISMATCH if neither the sum nor an individual duplicate matches A
            if a_rec.total_value != b_total and not has_matching_copy:
                issues.append("VALUE_MISMATCH")

        # Issue 4: LOCATION_MISMATCH (Tenant boundary check)
        for b_entry in b_list:
            if a_rec.location_id != b_entry.location_id:
                if "LOCATION_MISMATCH" not in issues:
                    issues.append("LOCATION_MISMATCH")
                break

        # If any issues were flagged, add to disagreements report
        if issues:
            org_id = locations_map.get(a_rec.location_id, "UNKNOWN_ORG")
            disagreements.append({
                "record_ref": rec_id,
                "issue_types": issues,
                "system_a": {
                    "record_id": a_rec.record_id,
                    "total_value": str(a_rec.total_value) if a_rec.total_value is not None else None,
                    "raw_total_value": a_rec.raw_total_value,
                    "location_id": a_rec.location_id,
                    "org_id": org_id,
                    "state": a_rec.state,
                },
                "system_b_entries": [
                    {
                        "entry_id": b.entry_id,
                        "record_ref_raw": b.record_ref_raw,
                        "value": str(b.value) if b.value is not None else None,
                        "raw_value": b.raw_value,
                        "location_id": b.location_id,
                        "org_id": locations_map.get(b.location_id, "UNKNOWN_ORG"),
                        "label": b.label,
                    }
                    for b in b_list
                ],
            })

    # -------------------------------------------------------------
    # Check for ORPHAN_SYSTEM_B_ENTRY (B entries that point to non-existent A records)
    # -------------------------------------------------------------
    for ref, b_list in system_b_by_ref.items():
        if ref not in system_a_by_id:
            for b in b_list:
                disagreements.append({
                    "record_ref": b.record_ref_normalized or b.record_ref_raw,
                    "issue_types": ["ORPHAN_SYSTEM_B_ENTRY"],
                    "system_a": None,
                    "system_b_entries": [
                        {
                            "entry_id": b.entry_id,
                            "record_ref_raw": b.record_ref_raw,
                            "value": str(b.value) if b.value is not None else None,
                            "raw_value": b.raw_value,
                            "location_id": b.location_id,
                            "org_id": locations_map.get(b.location_id, "UNKNOWN_ORG"),
                            "label": b.label,
                        }
                    ],
                })

    return disagreements
