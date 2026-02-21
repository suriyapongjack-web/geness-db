"""
extract_dolibarr_for_cpoc.py
────────────────────────────
Extract เฉพาะ tables ที่จำเป็นจาก Dolibarr (addvaluesystem_upver.sql)
เพื่อ compare / link กับ B1701-7-GEN-TE-DB-0001 Rev A41

Output: dolibarr_extract.sql  (~ควรได้ < 5 MB)
"""

import re
import os

# ── Config ────────────────────────────────────────────────────────
INPUT_FILE  = "addvaluesystem_upver.sql"   # ← แก้ path ถ้าจำเป็น
OUTPUT_FILE = "dolibarr_extract.sql"

# Tables ที่ต้องการ — เลือกเฉพาะที่ match กับ Rev A41
TARGET_TABLES = [
    # Products & BOM  → Rev A41: product, product_alt, bom
    "llx_product",
    "llx_product_fournisseur_price",   # = supplier pricing per product → product_alt
    "llx_product_fournisseur_price_log",
    "llx_bom_bom",                     # = bom header
    "llx_bom_bomline",                 # = bom line items
    "llx_categorie_product",           # = product category mapping

    # Supplier  → Rev A41: supplier
    "llx_societe",                     # = supplier / company
    "llx_societe_contacts",
    "llx_socpeople",                   # = contact persons

    # Quotation  → Rev A41: quotation, quotation_item
    "llx_propal",                      # = quotation header
    "llx_propaldet",                   # = quotation line items
    "llx_supplier_proposal",           # = supplier quote
    "llx_supplier_proposaldet",        # = supplier quote line items

    # Project  → Rev A41: project, platform
    "llx_projet",                      # = project
    "llx_projet_task",                 # = tasks

    # Finance  → Rev A41: quotation_rev, incoterm_cost_model
    "llx_facture",                     # = invoice
    "llx_facturedet",                  # = invoice lines
    "llx_commande",                    # = purchase order
    "llx_commandedet",                 # = PO lines

    # Config / Categories
    "llx_categorie",
    "llx_c_country",
    "llx_c_units",
]

# ── Parser ────────────────────────────────────────────────────────
def extract_tables(input_path, output_path, target_tables):
    target_set = set(t.lower() for t in target_tables)

    print(f"Reading: {input_path}  ({os.path.getsize(input_path)/1024/1024:.1f} MB)")

    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    results = {}  # table_name → {"create": str, "inserts": [str]}

    # ── 1. Extract CREATE TABLE ───────────────────────────────────
    create_pattern = re.compile(
        r"(CREATE TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+`?(\w+)`?\s*\([\s\S]*?\)\s*"
        r"(?:ENGINE[^;]*)?;)",
        re.IGNORECASE
    )
    for m in create_pattern.finditer(content):
        tbl = m.group(2).lower()
        if tbl in target_set:
            if tbl not in results:
                results[tbl] = {"create": "", "inserts": []}
            results[tbl]["create"] = m.group(1)
            print(f"  ✓ CREATE TABLE {m.group(2)}")

    # ── 2. Extract INSERT INTO (line by line for memory efficiency) ──
    print("\nScanning INSERT statements...")
    lines = content.split("\n")
    current_insert = []
    current_tbl = None

    for line in lines:
        # Detect start of INSERT
        m = re.match(r"INSERT\s+INTO\s+`?(\w+)`?", line, re.IGNORECASE)
        if m:
            # Save previous if any
            if current_tbl and current_insert:
                stmt = "\n".join(current_insert)
                if not stmt.endswith(";"): stmt += ";"
                results.setdefault(current_tbl, {"create":"","inserts":[]})["inserts"].append(stmt)

            tbl = m.group(1).lower()
            if tbl in target_set:
                current_tbl = tbl
                current_insert = [line]
            else:
                current_tbl = None
                current_insert = []
        elif current_tbl:
            current_insert.append(line)
            if line.rstrip().endswith(";"):
                stmt = "\n".join(current_insert)
                results.setdefault(current_tbl, {"create":"","inserts":[]})["inserts"].append(stmt)
                current_tbl = None
                current_insert = []

    # ── 3. Write output ───────────────────────────────────────────
    with open(output_path, "w", encoding="utf-8") as out:
        out.write("-- ═══════════════════════════════════════════════════\n")
        out.write("-- Dolibarr Extract for CPOC Rev A41 Comparison\n")
        out.write(f"-- Source: {input_path}\n")
        out.write(f"-- Tables: {', '.join(sorted(results.keys()))}\n")
        out.write("-- ═══════════════════════════════════════════════════\n\n")

        total_rows = 0
        for tbl_name in target_tables:
            tbl = tbl_name.lower()
            if tbl not in results:
                print(f"  ⚠ {tbl_name} — not found in source")
                continue

            data = results[tbl]
            row_count = len(data["inserts"])
            total_rows += row_count

            out.write(f"\n-- ─────────────────────────────────────────\n")
            out.write(f"-- {tbl_name}  ({row_count} INSERT statements)\n")
            out.write(f"-- ─────────────────────────────────────────\n")

            if data["create"]:
                out.write(data["create"] + "\n\n")
            else:
                out.write(f"-- (CREATE TABLE not found for {tbl_name})\n\n")

            for ins in data["inserts"]:
                out.write(ins + "\n")

            print(f"  ✓ {tbl_name:<45} {row_count:>6} rows")

    size_kb = os.path.getsize(output_path) / 1024
    print(f"\n{'─'*55}")
    print(f"Output: {output_path}")
    print(f"Size:   {size_kb:.0f} KB  ({size_kb/1024:.2f} MB)")
    print(f"Total INSERT statements: {total_rows}")

    if size_kb < 5000:
        print("✅ ขนาดเหมาะสม — upload ใน Claude ได้เลย")
    elif size_kb < 10000:
        print("⚠️  ขนาดค่อนข้างใหญ่ — ลองรันอีกครั้งด้วย ROW_LIMIT")
    else:
        print("❌ ยังใหญ่เกิน — ใช้ ROW_LIMIT ด้านล่าง")

    return results


# ── Optional: จำกัด rows ต่อ table (ถ้า output ยังใหญ่เกิน) ────────
ROW_LIMIT = None  # ตั้งเป็น เช่น 500 ถ้า output > 5MB

def extract_tables_limited(input_path, output_path, target_tables, row_limit=None):
    """Version ที่ limit rows per table"""
    target_set = set(t.lower() for t in target_tables)

    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    results = {}

    create_pattern = re.compile(
        r"(CREATE TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+`?(\w+)`?\s*\([\s\S]*?\)\s*(?:ENGINE[^;]*)?;)",
        re.IGNORECASE
    )
    for m in create_pattern.finditer(content):
        tbl = m.group(2).lower()
        if tbl in target_set:
            results.setdefault(tbl, {"create":"","inserts":[]})["create"] = m.group(1)

    insert_pattern = re.compile(
        r"(INSERT\s+INTO\s+`?(\w+)`?\s*[\s\S]*?;)",
        re.IGNORECASE
    )
    counts = {}
    for m in insert_pattern.finditer(content):
        tbl = m.group(2).lower()
        if tbl not in target_set: continue
        counts[tbl] = counts.get(tbl, 0) + 1
        if row_limit and counts[tbl] > row_limit: continue
        results.setdefault(tbl, {"create":"","inserts":[]})["inserts"].append(m.group(1))

    with open(output_path, "w", encoding="utf-8") as out:
        out.write(f"-- Dolibarr Extract (limit={row_limit} rows/table)\n\n")
        for tbl_name in target_tables:
            tbl = tbl_name.lower()
            if tbl not in results: continue
            data = results[tbl]
            out.write(f"-- {tbl_name} ({len(data['inserts'])} rows)\n")
            if data["create"]: out.write(data["create"] + "\n\n")
            for ins in data["inserts"]: out.write(ins + "\n")

    print(f"Output: {output_path}  ({os.path.getsize(output_path)/1024:.0f} KB)")


# ── Run ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"❌ ไม่พบไฟล์: {INPUT_FILE}")
        print("   แก้ INPUT_FILE ให้ตรงกับ path จริง")
        exit(1)

    if ROW_LIMIT:
        print(f"Running with ROW_LIMIT = {ROW_LIMIT}")
        extract_tables_limited(INPUT_FILE, OUTPUT_FILE, TARGET_TABLES, ROW_LIMIT)
    else:
        extract_tables(INPUT_FILE, OUTPUT_FILE, TARGET_TABLES)
