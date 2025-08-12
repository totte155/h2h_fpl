# streamlit_app.py
import requests
import pandas as pd
import streamlit as st
from collections import defaultdict

# ──────────────────────────────────────────────────────────────────────────────
# Page / Layout
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FPL: Think Tank vs Youngsters",
    page_icon="⚽",
    layout="wide"
)
st.title("⚽ FPL: Think Tank vs Youngsters — Head‑to‑Head Live")
st.caption("App loaded — preparing data…")

# ──────────────────────────────────────────────────────────────────────────────
# Config: IDs, Names, Groups, Schedule
# ──────────────────────────────────────────────────────────────────────────────
THINK_TANK = [3544410, 5508333, 333333]   # Torsten, Max, Phil
YOUNGSTERS = [1584965, 2767628, 454394]   # Tommi, Pat, Frej

NAMES = {
    3544410: "Torsten",
    5508333: "Max",
    333333:  "Phil",
    1584965: "Tommi",
    2767628: "Pat",
    454394:  "Frej",
}
NAME_TO_ID = {v: k for k, v in NAMES.items()}
PLAYER_TO_TEAM = {**{pid: "Think Tank" for pid in THINK_TANK},
                  **{pid: "Youngsters" for pid in YOUNGSTERS}}
ALL_IDS = THINK_TANK + YOUNGSTERS

# Schedule (Youngster vs Think Tank by names)
FINAL_SCHEDULE_BY_NAME = {
    1:  [("Frej","Phil"), ("Tommi","Max"),   ("Pat","Torsten")],
    2:  [("Frej","Max"),  ("Tommi","Torsten"), ("Pat","Phil")],
    3:  [("Frej","Torsten"), ("Tommi","Phil"), ("Pat","Max")],
    4:  [("Frej","Phil"), ("Tommi","Max"),   ("Pat","Torsten")],
    5:  [("Frej","Max"),  ("Tommi","Torsten"), ("Pat","Phil")],
    6:  [("Frej","Torsten"), ("Tommi","Phil"), ("Pat","Max")],
    7:  [("Frej","Phil"), ("Tommi","Max"),   ("Pat","Torsten")],
    8:  [("Frej","Max"),  ("Tommi","Torsten"), ("Pat","Phil")],
    9:  [("Frej","Torsten"), ("Tommi","Phil"), ("Pat","Max")],
    10: [("Frej","Phil"), ("Tommi","Max"),   ("Pat","Torsten")],
    11: [("Frej","Max"),  ("Tommi","Torsten"), ("Pat","Phil")],
    12: [("Frej","Torsten"), ("Tommi","Phil"), ("Pat","Max")],
    13: [("Frej","Phil"), ("Tommi","Max"),   ("Pat","Torsten")],
    14: [("Frej","Max"),  ("Tommi","Torsten"), ("Pat","Phil")],
    15: [("Frej","Torsten"), ("Tommi","Phil"), ("Pat","Max")],
    16: [("Frej","Phil"), ("Tommi","Max"),   ("Pat","Torsten")],
    17: [("Frej","Max"),  ("Tommi","Torsten"), ("Pat","Phil")],
    18: [("Frej","Torsten"), ("Tommi","Phil"), ("Pat","Max")],
}
N_GWS = max(FINAL_SCHEDULE_BY_NAME.keys())

# Convert schedule to IDs: {gw: [(youngster_id, thinktank_id), ...]}
SCHEDULE = defaultdict(list)
for gw, pairs in FINAL_SCHEDULE_BY_NAME.items():
    for y_name, t_name in pairs:
        SCHEDULE[gw].append((NAME_TO_ID[y_name], NAME_TO_ID[t_name]))

# ──────────────────────────────────────────────────────────────────────────────
# Data fetching (cached)
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=15 * 60, show_spinner=False)
def fetch_player_points(player_id: int) -> dict:
    """Return {gw: points} or {} on failure."""
    url = f"https://fantasy.premierleague.com/api/entry/{player_id}/history/"
    try:
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        data = r.json().get("current", [])
        return {int(ev["event"]): int(ev["points"]) for ev in data}
    except Exception:
        return {}

# ──────────────────────────────────────────────────────────────────────────────
# Fetch with progress, then build tables (pure)
# ──────────────────────────────────────────────────────────────────────────────
points = {}
with st.status("Fetching FPL points…", expanded=False) as status:
    for pid in ALL_IDS:
        points[pid] = fetch_player_points(pid)
    status.update(label="Fetch complete", state="complete")

def build_tables(points_dict: dict):
    # Player weekly
    rows_weeks = []
    for gw in range(1, N_GWS + 1):
        for pid in ALL_IDS:
            rows_weeks.append({
                "gameweek": gw,
                "player_id": pid,
                "player_name": NAMES[pid],
                "team": PLAYER_TO_TEAM[pid],
                "fpl_points": points_dict.get(pid, {}).get(gw, 0),
            })
    df_player_weekly = pd.DataFrame(rows_weeks)

    # Fixtures/results (Youngster is 'home', Think Tank is 'away' by design)
    match_rows = []
    for gw, pairs in SCHEDULE.items():
        for y_id, t_id in pairs:
            y_pts = points_dict.get(y_id, {}).get(gw, 0)
            t_pts = points_dict.get(t_id, {}).get(gw, 0)
            if y_pts > t_pts:
                y_mp, t_mp, winner = 1, 0, NAMES[y_id]
            elif t_pts > y_pts:
                y_mp, t_mp, winner = 0, 1, NAMES[t_id]
            else:
                y_mp, t_mp, winner = 0, 0, "Draw"
            match_rows.append({
                "gameweek": gw,
                "young_id": y_id, "young_name": NAMES[y_id], "young_team": "Youngsters",
                "young_score": y_pts, "young_match_point": y_mp,
                "think_id": t_id, "think_name": NAMES[t_id], "think_team": "Think Tank",
                "think_score": t_pts, "think_match_point": t_mp,
                "winner": winner,
            })
    df_fixtures = pd.DataFrame(match_rows).sort_values(["gameweek", "young_name"])

    # Player summary
    player_rows = []
    for pid in ALL_IDS:
        wins = int(
            df_fixtures.loc[df_fixtures.young_id == pid, "young_match_point"].sum() +
            df_fixtures.loc[df_fixtures.think_id == pid, "think_match_point"].sum()
        )
        player_rows.append({
            "player_id": pid,
            "player_name": NAMES[pid],
            "team": PLAYER_TO_TEAM[pid],
            "wins": wins,
            "total_fpl_points": int(df_player_weekly.loc[df_player_weekly.player_id == pid, "fpl_points"].sum())
        })
    df_player_summary = pd.DataFrame(player_rows).sort_values(["wins", "total_fpl_points"], ascending=[False, False])

    # Team weekly (FPL + match points)
    team_rows = []
    for gw in range(1, N_GWS + 1):
        tt_fpl = int(df_player_weekly.query("gameweek==@gw and team=='Think Tank'")["fpl_points"].sum())
        yo_fpl = int(df_player_weekly.query("gameweek==@gw and team=='Youngsters'")["fpl_points"].sum())
        tt_mp = int(df_fixtures.loc[df_fixtures.gameweek == gw, "think_match_point"].sum())
        yo_mp = int(df_fixtures.loc[df_fixtures.gameweek == gw, "young_match_point"].sum())
        team_rows += [
            {"gameweek": gw, "team": "Think Tank", "team_fpl_points": tt_fpl, "team_match_points": tt_mp},
            {"gameweek": gw, "team": "Youngsters", "team_fpl_points": yo_fpl, "team_match_points": yo_mp},
        ]
    df_team_weekly = pd.DataFrame(team_rows)

    # Overall scoreboard
    df_team_scoreboard = (
        df_team_weekly.groupby("team", as_index=False)["team_match_points"]
        .sum().rename(columns={"team_match_points":"Points"})
        .sort_values("Points", ascending=False)
    )

    return df_player_weekly, df_fixtures, df_player_summary, df_team_weekly, df_team_scoreboard

df_player_weekly, df_fixtures, df_player_summary, df_team_weekly, df_team_scoreboard = build_tables(points)

# Detect pre‑season
pre_season = (df_player_weekly["fpl_points"].sum() == 0)
if pre_season:
    st.info("Season hasn’t started yet — showing schedule and a 0–0 scoreboard.")

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar Navigation
# ──────────────────────────────────────────────────────────────────────────────
page = st.sidebar.radio("Navigate", ["Dashboard", "All Games"])
st.sidebar.caption("Data cached for 15 minutes.")

# ──────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────
if page == "Dashboard":
    # Overall team scoreboard
    st.subheader("Overall Scoreboard (Match Points)")
    st.dataframe(df_team_scoreboard.reset_index(drop=True), use_container_width=True)

    # Per‑GW Match Center (moved just below the scoreboard)
    st.divider()
    st.subheader("Per‑GW Match Center")
    sel_gw = st.slider("Gameweek", min_value=1, max_value=N_GWS, value=1, step=1)
    gw_df = df_fixtures[df_fixtures.gameweek == sel_gw].copy()
    if pre_season:
        # show dashes instead of zeros
        for c in ["young_score","think_score","young_match_point","think_match_point","winner"]:
            if c in gw_df.columns:
                gw_df[c] = gw_df[c].apply(lambda v: "—" if isinstance(v, int) and v == 0 else v)
    match_center = gw_df[[
        "young_name","young_score","think_name","think_score","winner"
    ]].rename(columns={
        "young_name":"Youngsters player",
        "young_score":"Youngsters score",
        "think_name":"Think Tank player",
        "think_score":"Think Tank score",
        "winner":"Winner"
    })
    st.dataframe(match_center, use_container_width=True)

    # Team points over time (line graph) — hide GWs with no points yet
    st.divider()
    st.subheader("Team Points by Gameweek")
    metric = st.radio("Metric", ["Match Points (0–3 per GW)", "FPL Points (sum of 3 players)"], horizontal=True)

    # Determine which GWs have any points recorded
    gw_has_points = (
        df_player_weekly.groupby("gameweek")["fpl_points"].sum() > 0
    )
    valid_gws = gw_has_points[gw_has_points].index.tolist()

    if len(valid_gws) == 0:
        st.info("No completed gameweeks yet — chart will appear once GW scores exist.")
    else:
        filtered = df_team_weekly[df_team_weekly.gameweek.isin(valid_gws)]
        if metric.startswith("Match"):
            plot_df = filtered.pivot(index="gameweek", columns="team", values="team_match_points").fillna(0)
        else:
            plot_df = filtered.pivot(index="gameweek", columns="team", values="team_fpl_points").fillna(0)
        st.line_chart(plot_df, height=320)

    # Best & worst players
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Best Player (Most Wins)")
        st.dataframe(df_player_summary.head(1)[["player_name","team","wins","total_fpl_points"]],
                     use_container_width=True)
    with col2:
        st.subheader("Worst Player (Least Wins)")
        worst = df_player_summary.sort_values(["wins","total_fpl_points"], ascending=[True, True]).head(1)
        st.dataframe(worst[["player_name","team","wins","total_fpl_points"]],
                     use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# ALL GAMES (simplified columns)
# ──────────────────────────────────────────────────────────────────────────────
else:
    st.subheader("All Games — Full Schedule & Results")
    tidy = df_fixtures[[
        "gameweek",
        "young_name","young_score",
        "think_name","think_score",
        "winner",
    ]].rename(columns={
        "gameweek":"GW",
        "young_name":"Youngsters player",
        "young_score":"Youngsters score",
        "think_name":"Think Tank player",
        "think_score":"Think Tank score",
        "winner":"Winner",
    }).sort_values(["GW","Youngsters player"])

    if pre_season:
        for c in ["Youngsters score","Think Tank score"]:
            tidy[c] = tidy[c].apply(lambda v: "—" if isinstance(v, int) and v == 0 else v)
        tidy["Winner"] = "—"

    st.dataframe(tidy, use_container_width=True)
