from pathlib import Path
import pandas as pd
import sys

# test_app.py
# Reads "Halsa Baby v1 FAQ.xlsx" and exports every sheet whose name ends with "Final" to a CSV.
# Requires: pandas (and an Excel engine like openpyxl)


def export_final_sheets(excel_file: Path):
    excel_file = Path(excel_file)
    if not excel_file.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_file}")

    xl = pd.ExcelFile(excel_file)
    finals = [s for s in xl.sheet_names if s.strip().lower().endswith("final")]
    if not finals:
        print("No sheets ending with 'Final' found.")
        return

    out_dir = excel_file.parent
    base_stem = excel_file.stem
    for sheet in finals:
        # read sheet
        df = xl.parse(sheet_name=sheet)
        # sanitize sheet name for filename
        safe_sheet = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in sheet).strip().replace(" ", "_")
        out_path = out_dir / f"{base_stem}_{safe_sheet}.csv"
        df.to_csv(out_path, index=False)
        print(f"Saved: {out_path}")

if __name__ == "__main__":
    # default filename (same directory as this script)
    default = Path.cwd() / "Halsa Baby v1 FAQs.xlsx"
    excel_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    export_final_sheets(excel_path)