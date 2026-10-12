from django.test import TestCase

# Create your tests here.

from decimal import Decimal
from django.test import TestCase
from reconciliation.models import Location, SystemARecord, SystemBEntry
from reconciliation.services import run_reconciliation


class ReconciliationEngineTests(TestCase):
    def setUp(self):
        """Create sample locations for testing tenant boundaries."""
        Location.objects.create(location_id="LOC-101", org_id="ORG-A", location_name="HQ 1")
        Location.objects.create(location_id="LOC-201", org_id="ORG-B", location_name="Branch 2")

    def test_clean_matching_record_not_flagged(self):
        """A clean record matching perfectly in both systems must NOT be flagged as a disagreement."""
        SystemARecord.objects.create(
            record_id="REC-2001",
            location_id="LOC-101",
            total_value=Decimal("5000.00"),
            raw_total_value="5000.00"
        )
        SystemBEntry.objects.create(
            entry_id="ENT-2001",
            record_ref_raw="REC-2001",
            record_ref_normalized="REC-2001",
            location_id="LOC-101",
            value=Decimal("5000.00"),
            raw_value="5000.00"
        )

        results = run_reconciliation()
        self.assertEqual(len(results), 0, "Clean matching records should produce 0 disagreements")

    def test_missing_system_b_entry(self):
        """System A record exists, but System B has zero matching entries."""
        SystemARecord.objects.create(
            record_id="REC-2002",
            location_id="LOC-101",
            total_value=Decimal("1200.00")
        )

        results = run_reconciliation()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["record_ref"], "REC-2002")
        self.assertIn("MISSING_SYSTEM_B_ENTRY", results[0]["issue_types"])

    def test_orphan_system_b_entry(self):
        """System B entry references a record that does not exist in System A."""
        SystemBEntry.objects.create(
            entry_id="ENT-2003",
            record_ref_raw="REC-9999",
            record_ref_normalized="REC-9999",
            location_id="LOC-101",
            value=Decimal("850.00")
        )

        results = run_reconciliation()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["record_ref"], "REC-9999")
        self.assertIn("ORPHAN_SYSTEM_B_ENTRY", results[0]["issue_types"])

    def test_duplicate_system_b_entry(self):
        """Multiple entries in System B reference the same System A record."""
        SystemARecord.objects.create(
            record_id="REC-2004",
            location_id="LOC-101",
            total_value=Decimal("1000.00")
        )
        # Entry 1
        SystemBEntry.objects.create(
            entry_id="ENT-2004A",
            record_ref_raw="REC-2004",
            record_ref_normalized="REC-2004",
            location_id="LOC-101",
            value=Decimal("1000.00")
        )
        # Entry 2 (duplicate)
        SystemBEntry.objects.create(
            entry_id="ENT-2004B",
            record_ref_raw="REC-2004",
            record_ref_normalized="REC-2004",
            location_id="LOC-101",
            value=Decimal("1000.00")
        )

        results = run_reconciliation()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["record_ref"], "REC-2004")
        self.assertIn("DUPLICATE_SYSTEM_B_ENTRY", results[0]["issue_types"])
        self.assertEqual(len(results[0]["system_b_entries"]), 2)

    def test_value_mismatch(self):
        """System A total_value does not equal System B value."""
        SystemARecord.objects.create(
            record_id="REC-2005",
            location_id="LOC-101",
            total_value=Decimal("1500.00")
        )
        SystemBEntry.objects.create(
            entry_id="ENT-2005",
            record_ref_raw="REC-2005",
            record_ref_normalized="REC-2005",
            location_id="LOC-101",
            value=Decimal("1400.00")
        )

        results = run_reconciliation()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["record_ref"], "REC-2005")
        self.assertIn("VALUE_MISMATCH", results[0]["issue_types"])

    def test_split_entries_sum_matches(self):
        """Two split entries in System B whose sum matches System A total (like REC-1055)."""
        SystemARecord.objects.create(
            record_id="REC-2006",
            location_id="LOC-101",
            total_value=Decimal("300.00")
        )
        SystemBEntry.objects.create(
            entry_id="ENT-2006A",
            record_ref_raw="REC-2006",
            record_ref_normalized="REC-2006",
            location_id="LOC-101",
            value=Decimal("100.00")
        )
        SystemBEntry.objects.create(
            entry_id="ENT-2006B",
            record_ref_raw="REC-2006",
            record_ref_normalized="REC-2006",
            location_id="LOC-101",
            value=Decimal("200.00")
        )

        results = run_reconciliation()
        self.assertEqual(len(results), 1)
        # It is flagged as duplicate/split entries, but NOT value mismatch because 100+200 == 300
        self.assertIn("DUPLICATE_SYSTEM_B_ENTRY", results[0]["issue_types"])
        self.assertNotIn("VALUE_MISMATCH", results[0]["issue_types"])

    def test_location_and_tenant_boundary_mismatch(self):
        """System A and System B show different locations across tenant boundaries."""
        SystemARecord.objects.create(
            record_id="REC-2007",
            location_id="LOC-101",  # Belongs to ORG-A
            total_value=Decimal("500.00")
        )
        SystemBEntry.objects.create(
            entry_id="ENT-2007",
            record_ref_raw="REC-2007",
            record_ref_normalized="REC-2007",
            location_id="LOC-201",  # Belongs to ORG-B
            value=Decimal("500.00")
        )

        results = run_reconciliation()
        self.assertEqual(len(results), 1)
        self.assertIn("LOCATION_MISMATCH", results[0]["issue_types"])
