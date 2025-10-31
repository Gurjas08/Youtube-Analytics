# YouTube Channel Analytics — Step-by-Step (Public Data Only)

This guide reproduces exactly what I built: an end-to-end pipeline that pulls **public** YouTube stats (views/likes/comments) for any channel via **YouTube Data API v3**, stores them in **SQLite**, exports tidy **CSVs**, and visualizes everything in **Power BI**.

> ⚠️ Note: This uses **public data** only. Private analytics like **impressions, CTR, traffic sources, audience retention** require channel-owner OAuth and are **not** available for other people’s channels.

---

## 1) Create a Google Cloud API key (no OAuth needed)

1. Go to **Google Cloud Console** → create/select a project.  
2. **APIs & Services → Library** → enable **YouTube Data API v3**.  
3. **APIs & Services → Credentials → Create Credentials → API key**.  
4. (Recommended) **Restrict key** → *API restrictions* → restrict to **YouTube Data API v3**.

You now have an API key that looks like `AIza...`.

---

## 2) Prepare local config

Create `config.json` in the project root just like the `config.example.json`

---

## 3) Install Python packages

```bash
python -m pip install --upgrade pip
pip install --user google-api-python-client pandas
```
---

## 4) Run ETL (API -> SQLite)

This script(etl_public_youtube.py) pulls public channel info, recent videos, and per-video stats, then upserts into youtube.db

---

## 5) Export tidy csv's for PowerBI

Run the export_for_powerbi.py script and this will generate 5 csv files channels.csv(for now only has one row for the given channel id but can be expanded for multiple), videos.csv, video_stats_snapshots.csv, daily_totals.csv, video_latest.csv

---

## 6) Build the PowerBI report

**Import CSVs:**  
Open Power BI Desktop → **Get Data → Text/CSV** → load the five files from your `data/` folder.



### Set Data Types (using Column Tools)

### Create Measures  
In **Model View**, select the `video_latest` table → **New Measure** → add these DAX formulas:

```DAX
Views (Latest)    = SUM(video_latest[view_count])
Likes (Latest)    = SUM(video_latest[like_count])
Comments (Latest) = SUM(video_latest[comment_count])
Like Rate         = DIVIDE(SUM(video_latest[like_count]), SUM(video_latest[view_count]))
Comment Rate      = DIVIDE(SUM(video_latest[comment_count]), SUM(video_latest[view_count]))
```
Format the comment rate to 4 decimals and like rate to 2 decimals (both as percentages).

After creating this we can go ahead and build the visuals that we wish to (check the docs folder)

---

## 🏁 Conclusion & Next Steps

This project demonstrates a complete **data pipeline** - from API extraction and database storage to analytics and visualization - all using **Python, SQLite, and Power BI**.  
It showcases how public YouTube data can be transformed into actionable insights through clean ETL design and interactive reporting.

---

### 🌟 Key Takeaways
- Built an **automated data collection workflow** using the YouTube Data API v3.  
- Designed a **structured SQLite database** to store and track video performance over time.  
- Created **export scripts** that produce BI-ready CSVs with clean, analyzable fields.  
- Developed a **two-page Power BI dashboard** visualizing:
  - Overall channel KPIs and top-performing videos.
  - Per-video engagement patterns and correlations between duration, likes, and views.

---

### 🚀 Future Improvements
If you want to extend this project, here are some ideas:
1. **Add time-series tracking** - run the ETL daily to monitor view growth and cumulative metrics.  
2. **Include more channels** - compare performance across multiple creators using joins on `channel_id`.  
3. **Deploy to Power BI Service** - schedule automatic refreshes and share live dashboards online.  
4. **Enhance analytics** - add regression or correlation scripts in Python to analyze content-type impact on engagement.  
5. **Integrate Power BI parameters** - let users dynamically filter channels or time periods from the report UI.

---
