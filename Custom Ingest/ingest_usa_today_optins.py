"""
Ingest USA TODAY opt-in Excel files from an S3-backed Snowflake external stage
into PGAT.CUSTOM_IDENTITY tables.

Why this approach
------------------
The source workbooks have Excel "Protect Workbook / Protect Sheet" structure
protection turned on. That protection is an XML-level flag inside the .xlsx
package -- it stops someone editing the sheet *in Excel*, but it does NOT
encrypt the file and does NOT stop a library like openpyxl/pandas from
reading it. That's why this can be done in Python without ever asking the
file owners to change anything: we just read the cell data directly and
ignore the protection flag.

(If a *future* file ever comes in actually password-encrypted -- i.e. Excel
asks for a password before it will even open the file -- this script will
fail with a clear "file is encrypted" error at the openpyxl step. See the
NOTE in `read_excel_to_df()` for the one extra step that would be needed in
that case: decrypt in-memory with `msoffcrypto-tool` before handing the
bytes to pandas. Not needed today.)

What this script does
----------------------
1. Connects to Snowflake with Snowpark.
2. Downloads each .xlsx from the external (S3) stage to a local temp dir
   using GET.
3. Reads each workbook with pandas/openpyxl, cleans/renames columns, and
   parses the "Data Added" timestamp.
4. Writes each cleaned DataFrame into its target table via
   Session.write_pandas(..., auto_create_table=True), so the tables are
   created fresh with correct types on first run and fully replaced on any
   re-run (idempotent).

Requirements
------------
    pip install snowflake-snowpark-python pandas openpyxl

Authentication
---------------
Two modes, controlled by SNOWFLAKE_AUTHENTICATOR:

1. Service account (default) -- password or key-pair auth, no browser,
   works unattended (cron, a scheduled Task, CI/CD):

    export SNOWFLAKE_ACCOUNT=your_account_locator
    export SNOWFLAKE_USER=your_service_user
    export SNOWFLAKE_PASSWORD=your_password        # or SNOWFLAKE_PRIVATE_KEY_PATH
    export SNOWFLAKE_ROLE=ACCOUNTADMIN
    export SNOWFLAKE_WAREHOUSE=your_warehouse

2. SSO via OneLogin (or any SAML2.0 IdP your account federates with) --
   opens a browser for you to log in through OneLogin; requires a human
   at a browser, so it only works for interactive/manual runs, not
   scheduled ones:

    export SNOWFLAKE_ACCOUNT=your_account_locator
    export SNOWFLAKE_USER=your_sso_username
    export SNOWFLAKE_AUTHENTICATOR=externalbrowser
    export SNOWFLAKE_ROLE=ACCOUNTADMIN
    export SNOWFLAKE_WAREHOUSE=your_warehouse
    # no SNOWFLAKE_PASSWORD needed in this mode

Then run:

    python ingest_usa_today_optins.py
"""

import io
import os
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

import pandas as pd
from snowflake.snowpark import Session

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------

DATABASE = "PGAT"
SCHEMA = "CUSTOM_IDENTITY"
STAGE_NAME = "DATA_INGEST"  # @PGAT.CUSTOM_IDENTITY.DATA_INGEST, per the stage screenshot
STAGE_PREFIX = "partners-offers-newsletter"  # sub-folder inside the stage/bucket

# One entry per source file -> target table.
FILES_TO_LOAD = [
    {
        "filename": "USATODAY_OptinMembers[49].xlsx",
        "table": "USA_TODAY_OPTINS_US_AUG_2026",
    },
    {
        "filename": "USATODAY_OptinMembersCalifornia[39].xlsx",
        "table": "USA_TODAY_OPTINS_CALIFORNIA_AUG_2026",
    },
]

# Source column name -> target Snowflake column name.
# Both files share this schema per the sample provided.
COLUMN_MAP = {
    "Email Address": "EMAIL_ADDRESS",
    "Data Added": "DATE_ADDED",
    "First Name": "FIRST_NAME",
    "Last Name": "LAST_NAME",
    "State": "STATE",
    "Postal Code": "POSTAL_CODE",
    "Phone": "PHONE",
    "How Many Tournaments Do You Attend Per Year": "TOURNAMENTS_PER_YEAR",
    "What's the Last Tournament You Attended and When": "LAST_TOURNAMENT_ATTENDED",
    "What's Your Bucket List Tournament to Attend": "BUCKET_LIST_TOURNAMENT",
}

# Columns that must stay text (never numeric) so leading zeros / formatting survive.
STRING_COLUMNS = {"POSTAL_CODE", "PHONE"}

# Excel's "Data Added" values look like '8/14/2026 10:42:00 PM'.
DATE_ADDED_FORMAT = "%m/%d/%Y %I:%M:%S %p"

# Set to False if you want to append instead of fully replacing the table on each run.
OVERWRITE_TABLE = True


# --------------------------------------------------------------------------
# SNOWFLAKE SESSION
# --------------------------------------------------------------------------

def get_session() -> Session:
    """
    Build a Snowpark session from environment variables.

    SNOWFLAKE_AUTHENTICATOR selects the auth mode:
      - unset / "snowflake" (default): password or key-pair auth (service account).
      - "externalbrowser": SSO via your account's federated IdP (e.g. OneLogin).
        Opens a browser for interactive login. Not usable for unattended runs.
    """
    connection_params = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "role": os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
        "database": DATABASE,
        "schema": SCHEMA,
    }

    authenticator = os.environ.get("SNOWFLAKE_AUTHENTICATOR", "snowflake").lower()

    if authenticator == "externalbrowser":
        # SSO / OneLogin (or any SAML2.0 IdP federated with this account).
        # No password or key needed -- a browser window opens for login.
        connection_params["authenticator"] = "externalbrowser"

        # Optional: cache the resulting session token locally so re-runs on
        # this machine within the token's validity window skip the browser
        # prompt. Requires the connector's secure local storage to be set up
        # (keyring on most platforms).
        if os.environ.get("SNOWFLAKE_CACHE_SSO_TOKEN", "false").lower() == "true":
            connection_params["client_store_temporary_credential"] = True
    else:
        private_key_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")
        if private_key_path:
            connection_params["private_key_file"] = private_key_path
            if os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"):
                connection_params["private_key_file_pwd"] = os.environ[
                    "SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"
                ]
        else:
            connection_params["password"] = os.environ["SNOWFLAKE_PASSWORD"]

    return Session.builder.configs(connection_params).create()


# --------------------------------------------------------------------------
# STAGE -> LOCAL DOWNLOAD
# --------------------------------------------------------------------------

def download_from_stage(session: Session, filename: str, local_dir: Path) -> Path:
    """
    Download a single file from the external stage down to local_dir.

    Since GET/PUT SQL commands are not supported on external stages in Snowflake,
    we generate a presigned URL using Snowflake's GET_PRESIGNED_URL function
    and download the file directly via HTTPS.
    """
    stage_ref = f"@{DATABASE}.{SCHEMA}.{STAGE_NAME}"

    # 1. List stage files to discover the exact relative path
    list_sql = f"LIST {stage_ref}"
    listed_files = []
    try:
        listed_files = session.sql(list_sql).collect()
    except Exception as e:
        print(f"  [warning] Could not list stage {stage_ref}: {e}")

    relative_path = None
    if listed_files:
        for row in listed_files:
            stage_file_name = row["name"]
            if stage_file_name.lower().endswith(filename.lower()):
                # Extract relative path after S3 bucket name
                # e.g. "s3://pgatour-datalake-.../partners-offers-newsletter/USATODAY_OptinMembers[49].xlsx"
                #   -> "partners-offers-newsletter/USATODAY_OptinMembers[49].xlsx"
                if "://" in stage_file_name:
                    proto_and_rest = stage_file_name.split("://", 1)[1]
                    relative_path = proto_and_rest.split("/", 1)[1] if "/" in proto_and_rest else proto_and_rest
                else:
                    parts = stage_file_name.split("/", 1)
                    relative_path = parts[1] if len(parts) > 1 else stage_file_name
                break

    if not relative_path:
        relative_path = f"{STAGE_PREFIX}/{filename}" if STAGE_PREFIX else filename

    # 2. Get presigned URL for the relative path
    clean_rel_path = relative_path.replace("'", "''")
    get_url_sql = f"SELECT GET_PRESIGNED_URL('{stage_ref}', '{clean_rel_path}') AS URL"
    res = session.sql(get_url_sql).collect()

    if not res or not res[0]["URL"]:
        available = [r["name"] for r in listed_files] if listed_files else "None"
        raise RuntimeError(
            f"Could not generate presigned URL for '{relative_path}' on stage {stage_ref}.\n"
            f"Files visible on stage: {available}"
        )

    presigned_url = res[0]["URL"]
    local_path = local_dir / filename

    # 3. Download file via presigned URL
    try:
        urllib.request.urlretrieve(presigned_url, local_path)
    except urllib.error.HTTPError as err:
        available = [r["name"] for r in listed_files] if listed_files else "None"
        raise RuntimeError(
            f"HTTP {err.code} ({err.reason}) downloading '{filename}' using presigned path '{relative_path}'.\n"
            f"Files visible on stage: {available}"
        ) from err

    if not local_path.exists() or local_path.stat().st_size == 0:
        raise RuntimeError(f"Failed to download file or empty file received: {local_path}")

    return local_path


# --------------------------------------------------------------------------
# EXCEL -> DATAFRAME
# --------------------------------------------------------------------------

def read_excel_to_df(local_path: Path) -> pd.DataFrame:
    """
    Read Excel workbook (.xlsx or .xls, encrypted or unencrypted).
    """
    with open(local_path, "rb") as f:
        header = f.read(8)

    # Standard XLSX zip archive (starts with PK\x03\x04)
    if header.startswith(b"PK"):
        return pd.read_excel(local_path, sheet_name=0, engine="openpyxl", dtype=str)

    # Compound Binary File / OLE2 container (starts with \xd0\xcf\x11\xe0)
    if header.startswith(b"\xd0\xcf\x11\xe0"):
        # 1. Try msoffcrypto for encrypted Excel workbook
        try:
            import msoffcrypto
            with open(local_path, "rb") as f:
                office_file = msoffcrypto.OfficeFile(f)
                if office_file.is_encrypted():
                    password = os.environ.get("XLSX_PASSWORD", "")
                    office_file.load_key(password=password)
                    decrypted = io.BytesIO()
                    office_file.decrypt(decrypted)
                    return pd.read_excel(decrypted, sheet_name=0, engine="openpyxl", dtype=str)
        except ImportError:
            pass
        except Exception as e:
            raise RuntimeError(
                f"File '{local_path.name}' is an encrypted Excel workbook.\n"
                "To decrypt it, install `msoffcrypto-tool` (`pip install msoffcrypto-tool`) "
                "and set `$env:XLSX_PASSWORD='your_password'` if password-protected."
            ) from e

        # 2. Try legacy Excel .xls format
        try:
            return pd.read_excel(local_path, sheet_name=0, engine="xlrd", dtype=str)
        except Exception:
            pass

        # 3. Fallback default pd.read_excel
        try:
            return pd.read_excel(local_path, sheet_name=0, dtype=str)
        except Exception as e:
            raise RuntimeError(
                f"File '{local_path.name}' is an encrypted Excel workbook or OLE file. "
                "If it requires a password, install `msoffcrypto-tool` (`pip install msoffcrypto-tool`) "
                "and set `$env:XLSX_PASSWORD='password'`."
            ) from e

    # General fallback
    return pd.read_excel(local_path, sheet_name=0, dtype=str)


def clean_dataframe(df: pd.DataFrame, source_filename: str) -> pd.DataFrame:
    # Trim accidental whitespace in header names, then map to target names.
    df = df.rename(columns=lambda c: c.strip())

    missing = set(COLUMN_MAP) - set(df.columns)
    if missing:
        raise ValueError(
            f"{source_filename}: expected columns not found in sheet: {sorted(missing)}. "
            f"Actual columns: {list(df.columns)}"
        )

    df = df[list(COLUMN_MAP.keys())].rename(columns=COLUMN_MAP)

    # Parse the timestamp; keep any unparseable values as NaT rather than failing the load.
    df["DATE_ADDED"] = pd.to_datetime(
        df["DATE_ADDED"], format=DATE_ADDED_FORMAT, errors="coerce"
    )

    for col in STRING_COLUMNS:
        df[col] = df[col].astype("string").str.strip()

    text_cols = [c for c in df.columns if c not in ("DATE_ADDED",)]
    for col in text_cols:
        df[col] = df[col].astype("string").str.strip()

    df["SOURCE_FILE"] = source_filename
    df["LOADED_AT"] = pd.Timestamp.utcnow()

    return df


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------

def main() -> None:
    session = get_session()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)

            for item in FILES_TO_LOAD:
                filename = item["filename"]
                table_name = item["table"]

                print(f"--- {filename} -> {DATABASE}.{SCHEMA}.{table_name} ---")

                local_path = download_from_stage(session, filename, tmp_dir)
                print(f"  downloaded to {local_path}")

                df = read_excel_to_df(local_path)
                print(f"  read {len(df)} rows")

                df = clean_dataframe(df, filename)

                success, num_chunks, num_rows, _ = session.write_pandas(
                    df,
                    table_name=table_name,
                    database=DATABASE,
                    schema=SCHEMA,
                    auto_create_table=True,
                    overwrite=OVERWRITE_TABLE,
                    quote_identifiers=False,
                )
                print(f"  wrote {num_rows} rows to {DATABASE}.{SCHEMA}.{table_name} "
                      f"(success={success})")
    finally:
        session.close()


if __name__ == "__main__":
    main()
