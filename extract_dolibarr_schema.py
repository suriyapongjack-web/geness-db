"""
extract_dolibarr_schema.py
──────────────────────────
Extract SCHEMA (CREATE TABLE) ของทุก table ใน addvaluesystem_upver.sql
ไม่เอา INSERT data → ไฟล์เล็ก < 500 KB → upload Claude ได้เลย

Usage:
    cd E:\GENESS\geness-db
    python extract_dolibarr_schema.py

Output:
    dolibarr_schema.sql   ← schema ทุก table (CREATE TABLE only)
    dolibarr_summary.txt  ← สรุป table list + column count
"""

import re
import os

INPUT_FILE   = "addvaluesystem_upver.sql"
OUTPUT_SQL   = "dolibarr_schema.sql"
OUTPUT_SUMMARY = "dolibarr_summary.txt"

def extract_schema(input_path, output_sql, output_summary):
    if not os.path.exists(input_path):
        print(f"❌ ไม่พบไฟล์: {input_path}")
        return

    size_mb = os.path.getsize(input_path) / 1024 / 1024
    print(f"Reading: {input_path}  ({size_mb:.1f} MB) ...")

    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Extract CREATE TABLE statements
    create_pattern = re.compile(
        r"(CREATE TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+`?(\w+)`?\s*\([\s\S]*?\)\s*"
        r"(?:ENGINE[^\n;]*(?:CHARSET[^\n;]*)?)?\s*;)",
        re.IGNORECASE
    )

    tables = {}
    for m in create_pattern.finditer(content):
        tbl_name = m.group(2)
        tables[tbl_name] = m.group(1)

    # Count INSERT rows per table
    insert_counts = {}
    for m in re.finditer(r"INSERT\s+INTO\s+`?(\w+)`?", content, re.IGNORECASE):
        tbl = m.group(1)
        insert_counts[tbl] = insert_counts.get(tbl, 0) + 1

    # Count columns per table
    def count_columns(create_sql):
        # นับบรรทัดที่เป็น column definition (ขึ้นต้นด้วย backtick)
        return len(re.findall(r"^\s+`\w+`", create_sql, re.MULTILINE))

    print(f"\nFound {len(tables)} tables\n")

    # Write SQL output
    with open(output_sql, "w", encoding="utf-8") as out:
        out.write("-- ═══════════════════════════════════════════════════════════\n")
        out.write("-- Dolibarr Full Schema Extract\n")
        out.write(f"-- Source:  {input_path}  ({size_mb:.1f} MB)\n")
        out.write(f"-- Tables:  {len(tables)}\n")
        out.write("-- Content: CREATE TABLE only (no INSERT data)\n")
        out.write("-- ═══════════════════════════════════════════════════════════\n\n")

        for tbl_name in sorted(tables.keys()):
            rows = insert_counts.get(tbl_name, 0)
            cols = count_columns(tables[tbl_name])
            out.write(f"-- [{tbl_name}]  columns:{cols}  rows:{rows}\n")
            out.write(tables[tbl_name])
            out.write("\n\n")

    # Write summary text
    with open(output_summary, "w", encoding="utf-8") as out:
        out.write(f"Dolibarr Schema Summary — addvaluesystem_upver\n")
        out.write(f"{'='*55}\n")
        out.write(f"Total tables: {len(tables)}\n\n")
        out.write(f"{'Table Name':<50} {'Cols':>5} {'Rows':>8}\n")
        out.write(f"{'-'*50} {'-'*5} {'-'*8}\n")

        total_rows = 0
        for tbl_name in sorted(tables.keys()):
            rows = insert_counts.get(tbl_name, 0)
            cols = count_columns(tables[tbl_name])
            total_rows += rows
            out.write(f"{tbl_name:<50} {cols:>5} {rows:>8}\n")
            print(f"  {tbl_name:<50} cols:{cols:>3}  rows:{rows:>6}")

        out.write(f"\n{'TOTAL':>55} {total_rows:>8}\n")

    sql_kb  = os.path.getsize(output_sql) / 1024
    sum_kb  = os.path.getsize(output_summary) / 1024
    print(f"\n{'═'*60}")
    print(f"✅ Output files:")
    print(f"   {output_sql:<35} {sql_kb:>7.0f} KB")
    print(f"   {output_summary:<35} {sum_kb:>7.0f} KB")
    print(f"\nTotal tables: {len(tables)}")
    print(f"Total rows:   {total_rows:,}")

    if sql_kb < 2000:
        print(f"\n✅ ไฟล์เล็กพอ — upload ใน Claude ได้เลย หรือ push ขึ้น GitHub")
    else:
        print(f"\n⚠️  ไฟล์ใหญ่กว่าที่คาด — ใช้ dolibarr_summary.txt แทน")


if __name__ == "__main__":
    extract_schema(INPUT_FILE, OUTPUT_SQL, OUTPUT_SUMMARY)
    print("\nDone.")
