from datetime import datetime
from pathlib import Path
import os
import sqlite3
from sqlite3 import Cursor
from typing import List, Tuple

from aw_client import ActivityWatchClient
from aw_core import Event
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Constants
DEFAULT_SERVER_ADDRESS = "http://localhost:5600"
CLIENT_NAME = "aw-import-screentime"
BUCKET_TYPE = "currentwindow"
DB_TEST_PATH = "~/tmp/sync-with-vm-host/Knowledge/knowledgeC.db"
DB_PROD_PATH = "~/Library/Application Support/Knowledge/knowledgeC.db"


def main() -> None:
    dbfile = _get_db_path()
    print(f"Reading from database file at {dbfile}")

    with sqlite3.connect(dbfile) as conn:
        conn.execute("pragma journal_mode=wal;")
        cur = conn.cursor()
        devices = get_devices(cur)

        for index, device in enumerate(devices):
            events = get_events_for_device(device[0], cur)
            print(
                f"{index + 1} / {len(devices)} Sending {len(events)} events to ActivityWatch for device {device[0]} - {device[1]}"
            )
            if len(events) > 0:
                send_to_activitywatch(events, device)


def get_devices(database_connection: Cursor) -> List[Tuple[str, str]]:
    query = """
    SELECT
      DISTINCT(ZSOURCE.ZDEVICEID) as deviceId,
	  ZSYNCPEER.ZMODEL as deviceModel
    FROM
      ZSOURCE
	  LEFT JOIN
		ZSYNCPEER
		ON ZSYNCPEER.ZDEVICEID = ZSOURCE.ZDEVICEID
    """
    return list(database_connection.execute(query))


def get_events_for_device(device: str, database_connection: Cursor) -> List[Event]:
    query = """
  SELECT
    ZOBJECT.ZVALUESTRING AS "app",
      (ZOBJECT.ZENDDATE - ZOBJECT.ZSTARTDATE) AS "usage",
      CASE ZOBJECT.ZSTARTDAYOFWEEK
        WHEN "1" THEN "Sunday"
        WHEN "2" THEN "Monday"
        WHEN "3" THEN "Tuesday"
        WHEN "4" THEN "Wednesday"
        WHEN "5" THEN "Thursday"
        WHEN "6" THEN "Friday"
        WHEN "7" THEN "Saturday"
      END "dow",
      ZOBJECT.ZSECONDSFROMGMT/3600 AS "tz",
      DATETIME(ZOBJECT.ZSTARTDATE + 978307200, \'UNIXEPOCH\') as "start_time",
      DATETIME(ZOBJECT.ZENDDATE + 978307200, \'UNIXEPOCH\') as "end_time",
      DATETIME(ZOBJECT.ZCREATIONDATE + 978307200, \'UNIXEPOCH\') as "created_at",
      CASE ZMODEL
        WHEN ZMODEL THEN ZMODEL
        ELSE "Other"
      END "source",
      ZSOURCE.ZDEVICEID AS "device"
    FROM
      ZOBJECT
      LEFT JOIN
        ZSTRUCTUREDMETADATA
      ON ZOBJECT.ZSTRUCTUREDMETADATA = ZSTRUCTUREDMETADATA.Z_PK
      LEFT JOIN
        ZSOURCE
      ON ZOBJECT.ZSOURCE = ZSOURCE.Z_PK
      LEFT JOIN
        ZSYNCPEER
      ON ZSOURCE.ZDEVICEID = ZSYNCPEER.ZDEVICEID
    WHERE
      ZSTREAMNAME = "/app/usage"
      AND 
      device = ?
  """
    rows = list(database_connection.execute(query, (device,)))
    # TODO: Handle timezone. Maybe not needed if everything is in UTC anyway?
    return [
        Event(
            timestamp=row[4],
            duration=datetime.fromisoformat(row[5]) - datetime.fromisoformat(row[4]),
            data={"app": row[0], "category": row[-1]},
        )
        for row in rows
    ]


def send_to_activitywatch(events: List[Event], device: Tuple[str, str]) -> None:
    hostname = f"ios-{device[0]}-{device[1]}"
    bucket = f"aw-watcher-android_aw-import-screentime_{hostname}"

    server_address = os.getenv("AW_SERVER_ADDRESS", DEFAULT_SERVER_ADDRESS)
    aw = ActivityWatchClient(
        client_name=CLIENT_NAME, testing=False, host=server_address
    )
    aw.client_hostname = hostname
    aw.create_bucket(bucket, BUCKET_TYPE)
    aw.insert_events(bucket, events)


def _get_db_path() -> Path:
    path_test = Path(DB_TEST_PATH).expanduser()
    path_prod = Path(DB_PROD_PATH).expanduser()

    path = path_test if path_test.exists() else path_prod
    assert path.exists(), "couldn't find database file"
    return path


if __name__ == "__main__":
    main()
