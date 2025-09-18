import sqlite3
import pandas as pd
import os

DB_NAME = "codes.db"
EXCEL_FOLDER = "excel_files"  # put your 5 Excel files inside this folder

def create_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            used INTEGER DEFAULT 0,
            used_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def import_excel_files():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for file in os.listdir(EXCEL_FOLDER):
        if file.endswith(".xlsx"):
            file_path = os.path.join(EXCEL_FOLDER, file)
            print(f"📂 Importing {file_path} ...")

            df = pd.read_excel(file_path)

            # Try to find column with "code"
            if "code" in df.columns:
                codes = df["code"].dropna().unique()
            else:
                # if codes are in first column
                codes = df.iloc[:, 0].dropna().unique()

            for c in codes:
                try:
                    cursor.execute("INSERT OR IGNORE INTO codes (code) VALUES (?)", (c.strip(),))
                except Exception as e:
                    print(f"⚠️ Skipping {c}: {e}")

    conn.commit()
    conn.close()
    print("✅ Import finished!")


if __name__ == "__main__":
    create_table()
    import_excel_files()
    print("All done!")