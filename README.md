aw-import-screentime
====================

**NOTE:** This is a work in progress.

Import data from Apple's Screen Time to ActivityWatch. This could potentially be used to retrieve the Screen Time data of both macOS and iOS devices.

Based on analysis of the `Knowledge.db` file done here: https://www.r-bloggers.com/2019/10/spelunking-macos-screentime-app-usage-with-r/


## Usage

Requirements:

 - Python 3.12+
 - uv (install with `curl -LsSf https://astral.sh/uv/install.sh | sh`)

Install dependencies with: `uv pip install .`

Run script with: `python3 main.py`


## Limitations of Knowledge.db

 - macOS doesn't keep track of which apps are active and which are inactive (only that they run, or at least have an open window?)
   - It almost seems like sometimes it does and sometimes it doesn't, weird.
   - Is it different for iOS? (It seems to work for iOS, but leaving this just inc case)
 - How far back does the history go?
 - How often does the db file update? (based on icloud, a couple of hours?)
   - I can't seem to retrieve the latest entries, maybe they are stuck in WAL?
