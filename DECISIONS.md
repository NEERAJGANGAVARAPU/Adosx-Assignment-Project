# Architectural Decisions

This file explains the main decisions I made while building the ADOSX Data Reconciliation Reviewer and why I chose these approaches over other options.

## 1. Keeping the Original Data

**Decision:** I decided to store the original values from the CSV files along with the cleaned numbers and dates in the database.

**Alternative rejected:** Storing only the cleaned values and removing the original data.

**Reason:** Some values in the CSV files may be formatted differently or contain invalid data. For example, a number such as `1,25,400.00` needs to be parsed before it can be used in calculations. Keeping the original value makes it easier to check what was actually present in the file if something goes wrong during parsing.

## 2. Allowing Multiple System B Entries

**Decision:** I allowed multiple System B entries to refer to the same System A record.

**Alternative rejected:** Making the record reference unique so that only one System B entry could refer to a System A record.

**Reason:** The supplied data contains records with multiple entries. Some may be duplicate submissions, while others may represent split transactions. I need to keep all these entries so the application can identify and display them for review instead of rejecting or losing them during import.

## 3. Handling Blank Values

**Decision:** I kept blank numerical values as `NULL` in the database instead of replacing them with zero.

**Alternative rejected:** Converting every blank value to `0.00`.

**Reason:** A missing value and a value of zero have different meanings. If a System B entry has no recorded amount, replacing it with zero could lead to a misleading comparison. Keeping it as `NULL` allows the application to distinguish missing information from a valid zero value.

## 4. Keeping the Comparison Logic Separate

**Decision:** I kept the reconciliation logic in a separate file called `services.py`.

**Alternative rejected:** Writing all the comparison logic directly inside Django views or React components.

**Reason:** The comparison rules are easier to understand and test when they are separate from the API and frontend code. I can create sample records, run the reconciliation function, and check the results without needing to open the frontend or start a browser.

## 5. Using the Location Mapping for Organizations

**Decision:** I used `locations.csv` to determine which organization each location belongs to.

**Alternative rejected:** Guessing the organization from the location ID or its number.

**Reason:** The assignment specifies that `locations.csv` is the source for mapping locations to organizations. Using this mapping avoids making assumptions about ownership and helps identify cases where System A and System B associate a record with locations belonging to different organizations.

## 6. Handling Multiple Entries Carefully

**Decision:** I made the comparison logic check multiple System B entries carefully before reporting a value mismatch.

**Alternative rejected:** Always adding all System B values together whenever multiple entries refer to the same record.

**Reason:** During reconciliation, multiple entries can represent different situations. For example, `REC-1042` has two System B entries with the same value, while `REC-1055` has two entries whose values add up to the System A total. Blindly summing every entry could incorrectly flag an identical duplicate as a value mismatch. I therefore need to distinguish these cases while still reporting the multiple-entry issue for review.

