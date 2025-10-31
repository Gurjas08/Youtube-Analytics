# src/etl_public_youtube.py
from __future__ import annotations
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
from googleapiclient.discovery import build
from utils import load_config

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "youtube.db"

def ensure_schema(conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS channels (
      channel_id TEXT PRIMARY KEY,
      title TEXT,
      description TEXT,
      country TEXT,
      subscriber_count INTEGER,
      view_count INTEGER,
      video_count INTEGER
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS videos (
      video_id TEXT PRIMARY KEY,
      channel_id TEXT,
      title TEXT,
      published_at TEXT,
      duration TEXT,
      category_id TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS video_stats_snapshots (
      snapshot_date TEXT,         -- YYYY-MM-DD
      video_id TEXT,
      view_count INTEGER,
      like_count INTEGER,
      comment_count INTEGER,
      PRIMARY KEY (snapshot_date, video_id)
    )""")
    conn.commit()

def upsert(conn: sqlite3.Connection, table: str, df: pd.DataFrame, key_cols: list[str]):
    if df.empty:
        return
    cur = conn.cursor()
    cols = list(df.columns)
    placeholders = ",".join(["?"] * len(cols))
    update_set = ",".join([f"{c}=excluded.{c}" for c in cols if c not in key_cols])
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders}) " \
          f"ON CONFLICT({','.join(key_cols)}) DO UPDATE SET {update_set}"
    cur.executemany(sql, df.values.tolist())
    conn.commit()

def fetch_channel_public(yt, channel_id: str) -> dict:
    r = yt.channels().list(part="snippet,statistics", id=channel_id).execute()
    if not r.get("items"):
        raise ValueError(f"No channel found for id={channel_id}")
    it = r["items"][0]
    sn, st = it["snippet"], it["statistics"]
    return {
        "channel_id": channel_id,
        "title": sn.get("title"),
        "description": sn.get("description"),
        "country": sn.get("country"),
        "subscriber_count": int(st.get("subscriberCount")) if "subscriberCount" in st else None,
        "view_count": int(st.get("viewCount", 0)),
        "video_count": int(st.get("videoCount", 0)),
    }

def list_recent_video_ids(yt, channel_id: str, days_back: int) -> list[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    ids: list[str] = []
    page = None
    while True:
        r = yt.search().list(
            part="id,snippet",
            channelId=channel_id,
            type="video",
            order="date",
            maxResults=50,
            pageToken=page
        ).execute()
        for it in r.get("items", []):
            vid = it["id"]["videoId"]
            published = it["snippet"]["publishedAt"]  # ISO8601
            published_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            if published_dt < cutoff:
                return ids
            ids.append(vid)
        page = r.get("nextPageToken")
        if not page:
            break
    return ids

def fetch_videos_and_stats(yt, video_ids: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not video_ids:
        return pd.DataFrame(), pd.DataFrame()
    r = yt.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids)
    ).execute()
    vids, stats = [], []
    for it in r.get("items", []):
        sn, st, cd = it["snippet"], it.get("statistics", {}), it.get("contentDetails", {})
        vids.append({
            "video_id": it["id"],
            "channel_id": sn.get("channelId"),
            "title": sn.get("title"),
            "published_at": sn.get("publishedAt"),
            "duration": cd.get("duration"),
            "category_id": sn.get("categoryId")
        })
        stats.append({
            "video_id": it["id"],
            "view_count": int(st.get("viewCount", 0)),
            "like_count": int(st.get("likeCount", 0)) if "likeCount" in st else None,
            "comment_count": int(st.get("commentCount", 0)) if "commentCount" in st else None,
        })
    return pd.DataFrame(vids), pd.DataFrame(stats)

def main():
    cfg = load_config()
    API_KEY = cfg["API_KEY"]
    CHANNEL_ID = cfg["CHANNEL_ID"]
    DAYS = int(cfg.get("DEFAULT_DAYS_BACK", 90))

    yt = build("youtube", "v3", developerKey=API_KEY)

    with sqlite3.connect(DB) as conn:
        ensure_schema(conn)

        # channel → upsert
        ch = fetch_channel_public(yt, CHANNEL_ID)
        upsert(conn, "channels", pd.DataFrame([ch]), ["channel_id"])

        # videos from recent DAYS → upsert
        ids = list_recent_video_ids(yt, CHANNEL_ID, DAYS)
        v_df, s_df = fetch_videos_and_stats(yt, ids)
        upsert(conn, "videos", v_df, ["video_id"])

        # snapshot stats (dated today) → upsert
        today = datetime.utcnow().date().isoformat()
        s_df = s_df.copy()
        s_df.insert(0, "snapshot_date", today)
        upsert(conn, "video_stats_snapshots", s_df, ["snapshot_date", "video_id"])

        print(f"Done. Channel: {ch['title']}, videos snapshot: {len(s_df)} on {today}")

if __name__ == "__main__":
    main()
