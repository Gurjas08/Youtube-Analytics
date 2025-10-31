from pathlib import Path
import sqlite3
import pandas as pd
import re
from typing import Optional

# ---------- Paths ----------
ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "youtube.db"
OUT = ROOT / "data"
OUT.mkdir(parents=True, exist_ok=True)

# ---------- Helpers ----------
_dur_re = re.compile(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")

def iso8601_to_seconds(s: Optional[str]) -> Optional[int]:
    """Convert ISO 8601 duration like 'PT12M45S' or 'PT1H2M3S' to total seconds."""
    if not isinstance(s, str):
        return None
    m = _dur_re.match(s)
    if not m:
        return None
    h = int(m.group(1) or 0)
    m_ = int(m.group(2) or 0)
    s_ = int(m.group(3) or 0)
    return h * 3600 + m_ * 60 + s_


# ---------- Export Script ----------
def main():
    with sqlite3.connect(DB) as conn:
        # 1) Base tables
        channels = pd.read_sql("SELECT * FROM channels", conn)
        videos = pd.read_sql("SELECT * FROM videos", conn)
        snaps = pd.read_sql("SELECT * FROM video_stats_snapshots", conn)

        # Add numeric duration
        if not videos.empty:
            videos["duration_seconds"] = videos["duration"].apply(iso8601_to_seconds)

        # --- Save base tables ---
        channels.to_csv(OUT / "channels.csv", index=False)
        videos.to_csv(OUT / "videos.csv", index=False)
        snaps.to_csv(OUT / "video_stats_snapshots.csv", index=False)

        # 2) Daily totals (views, likes, comments summed across videos)
        if not snaps.empty:
            daily_totals = (
                snaps.groupby("snapshot_date", as_index=False)
                     .agg(views=("view_count","sum"),
                          likes=("like_count","sum"),
                          comments=("comment_count","sum"))
                     .sort_values("snapshot_date")
            )
            daily_totals.to_csv(OUT / "daily_totals.csv", index=False)

        # 3) Latest snapshot per video (now with duration_seconds)
        if not snaps.empty:
            snaps["snapshot_date"] = pd.to_datetime(snaps["snapshot_date"])
            latest = (
                snaps.sort_values(["video_id","snapshot_date"])
                     .groupby("video_id").tail(1)
            )

            video_latest = (
                latest.merge(videos, on="video_id", how="left")
                      .loc[:, ["video_id","title","published_at","duration","duration_seconds",
                               "snapshot_date","view_count","like_count","comment_count"]]
                      .sort_values("view_count", ascending=False)
            )
            video_latest.to_csv(OUT / "video_latest.csv", index=False)

    print(f"✅ Exported CSVs to {OUT} (with duration_seconds)")

if __name__ == "__main__":
    main()
