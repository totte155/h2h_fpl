# streamlit_app.py
import requests
import pandas as pd
import streamlit as st
from collections import defaultdict

# ──────────────────────────────────────────────────────────────────────────────
# Page / Layout
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FPL: FPL Geese vs Big Ben Brexit Sauce Appreciation Society",
    page_icon="⚽",
    layout="wide"
)
st.title("⚽ FPL: FPL Geese vs Big Ben Brexit Sauce Appreciation Society — Head-to-Head Live")
st.caption("App loaded — preparing data…")

# Helper: center-align any dataframe in Streamlit
def center_df(df: pd.DataFrame):
    return (
        df.style
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
    )

# ──────────────────────────────────────────────────────────────────────────────
# Config: IDs, Names, Groups, Schedule
# ──────────────────────────────────────────────────────────────────────────────
# Team name constants (single source of truth)
TEAM_GEESE = "FPL Geese"
TEAM_BBBSAS = "Big Ben Brexit Sauce Appreciation Society"

# Team colors for UI accents
TEAM_COLORS = {
    TEAM_GEESE:  "#1f8ef1",  # blue
    TEAM_BBBSAS: "#8b5cf6",  # purple
}
NEUTRAL_GREY = "#6b7280"

# Players by FPL Entry IDs
THINK_TANK = [3544410, 5508333, 727945]   # Torsten, Max, Phil (Phil id updated)
YOUNGSTERS = [1584965, 2767628, 454394]   # Tommi, Pat, Frej

NAMES = {
    3544410: "Torsten",
    5508333: "Max",
    727945:  "Phil",
    1584965: "Tommi",
    2767628: "Pat",
    454394:  "Frej",
}
NAME_TO_ID = {v: k for k, v in NAMES.items()}
PLAYER_TO_TEAM = {**{pid: TEAM_GEESE for pid in THINK_TANK},
                  **{pid: TEAM_BBBSAS for pid in YOUNGSTERS}}
ALL_IDS = THINK_TANK + YOUNGSTERS

# Schedule (BBBSAS home vs Geese away) by names
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

# Convert schedule to IDs: {gw: [(bbb_id, geese_id), ...]}
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
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=5 * 60, show_spinner=False)
def detect_current_gw(df_player_weekly, n_gws: int) -> int:
    """
    Prefer FPL's bootstrap-static 'is_current'. If unavailable, fall back to the
    last GW with any points; else 1.
    """
    try:
        r = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=6)
        r.raise_for_status()
        events = r.json().get("events", [])
        cur = [e["id"] for e in events if e.get("is_current")]
        if cur:
            return int(min(max(cur[0], 1), n_gws))
        prev = [e["id"] for e in events if e.get("is_previous")]
        if prev:
            return int(min(max(max(prev), 1), n_gws))
    except Exception:
        pass

    # Fallback: last GW with any points in your data
    gw_has_points = (df_player_weekly.groupby("gameweek")["fpl_points"].sum() > 0)
    valid_gws = gw_has_points[gw_has_points].index.tolist()
    return int(min(max((max(valid_gws) if valid_gws else 1), 1), n_gws))

# Winner color resolver
def winner_team_and_color(winner: str):
    """Return (team_name, hex_color) for the winner; neutral grey on draw/unknown."""
    if not isinstance(winner, str) or winner in ("Draw", "—"):
        return None, NEUTRAL_GREY
    pid = NAME_TO_ID.get(winner)
    if not pid:
        return None, NEUTRAL_GREY
    team = PLAYER_TO_TEAM.get(pid)
    return team, TEAM_COLORS.get(team, NEUTRAL_GREY)

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

    # Fixtures/results
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
                "young_id": y_id, "young_name": NAMES[y_id], "young_team": TEAM_BBBSAS,
                "young_score": y_pts, "young_match_point": y_mp,
                "think_id": t_id, "think_name": NAMES[t_id], "think_team": TEAM_GEESE,
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
        geese_fpl = int(df_player_weekly.query("gameweek==@gw and team==@TEAM_GEESE")["fpl_points"].sum())
        bbb_fpl  = int(df_player_weekly.query("gameweek==@gw and team==@TEAM_BBBSAS")["fpl_points"].sum())
        geese_mp = int(df_fixtures.loc[df_fixtures.gameweek == gw, "think_match_point"].sum())
        bbb_mp   = int(df_fixtures.loc[df_fixtures.gameweek == gw, "young_match_point"].sum())
        team_rows += [
            {"gameweek": gw, "team": TEAM_GEESE,  "team_fpl_points": geese_fpl, "team_match_points": geese_mp},
            {"gameweek": gw, "team": TEAM_BBBSAS, "team_fpl_points": bbb_fpl,   "team_match_points": bbb_mp},
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

# Detect pre-season
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
    # ── Overall team scoreboard — BIG cards
    st.subheader("Overall Scoreboard (Match Points)")

    # Build values
    score_map = {row["team"]: int(row["Points"]) for _, row in df_team_scoreboard.iterrows()}
    geese_pts = score_map.get(TEAM_GEESE, 0)
    bbb_pts   = score_map.get(TEAM_BBBSAS, 0)
    leader = TEAM_GEESE if geese_pts >= bbb_pts else TEAM_BBBSAS
    diff = abs(geese_pts - bbb_pts)

    # Cards
    colA, colB = st.columns(2)

    def main_score_card(team, pts, highlight=False):
        grad = "linear-gradient(135deg, #1f8ef1 0%, #5ac8fa 100%)" if team == TEAM_GEESE else \
               "linear-gradient(135deg, #8b5cf6 0%, #c084fc 100%)"
        ring = "0 0 0 3px rgba(255,255,255,0.6)" if highlight else "0 0 0 0 rgba(0,0,0,0)"
        return f"""
        <div style="
            background: {grad};
            border-radius: 18px;
            padding: 22px 24px;
            color: white;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15), {ring};
        ">
            <div style="font-size: 16px; font-weight: 600; letter-spacing: .2px; opacity:.95; word-break: break-word;">{team}</div>
            <div style="font-size: 56px; font-weight: 800; line-height: 1; margin-top: 6px">{pts}</div>
            <div style="font-size: 14px; margin-top: 6px; opacity:.9">Match points</div>
        </div>
        """

    with colA:
        st.markdown(main_score_card(TEAM_GEESE, geese_pts, highlight=(leader==TEAM_GEESE)), unsafe_allow_html=True)
    with colB:
        st.markdown(main_score_card(TEAM_BBBSAS, bbb_pts, highlight=(leader==TEAM_BBBSAS)), unsafe_allow_html=True)

    st.caption(f"Current leader: **{leader}**" + ("" if diff == 0 else f" by **{diff}**"))

    # ── Gameweek Matches — compact cards with per-player links for selected GW
    st.divider()
    st.subheader("Gameweek Matches")
    default_gw = detect_current_gw(df_player_weekly, N_GWS)
    sel_gw = st.slider("Gameweek", min_value=1, max_value=N_GWS, value=default_gw, step=1)
    gw_df = df_fixtures[df_fixtures.gameweek == sel_gw].copy()

    if pre_season:
        # Replace scores & winner with dashes for display only
        gw_df["young_score"] = "—"
        gw_df["think_score"] = "—"
        gw_df["winner"] = "—"

    cols = st.columns(3)

    def mini_match_card(young_name, young_id, y_score, think_name, think_id, t_score, winner, gw_num):
        team, color = winner_team_and_color(winner)
        # Dynamic per-player GW links
        y_url = f"https://fantasy.premierleague.com/entry/{young_id}/event/{gw_num}"
        t_url = f"https://fantasy.premierleague.com/entry/{think_id}/event/{gw_num}"

        badge = ""
        if isinstance(winner, str) and winner not in ("Draw", "—"):
            badge = f"""<div style="
                display:inline-block;
                font-size:12px; font-weight:700;
                padding:2px 8px; border-radius:999px;
                background:{color}; color:white; margin-left:8px;
            ">WIN</div>"""

        return f"""
        <div style="
            background: #f7f7fb;
            border: 1px solid #e9e9f1;
            border-radius: 14px;
            padding: 14px 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            height: 100%;
        ">
            <div style="font-size: 13px; font-weight: 600; color:#6b7280; margin-bottom: 8px;">Match</div>
            <div style="display:flex; align-items:center; justify-content:space-between; gap:10px;">
                <div style="flex:1;">
                    <div style="font-size:13px; font-weight:600; color:#111827">
                        <a href="{y_url}" target="_blank" style="color:inherit; text-decoration:none;">
                            {young_name} <span style="font-size:11px; font-weight:700; opacity:.7;">↗</span>
                        </a>
                    </div>
                    <div style="font-size:28px; font-weight:800; margin-top:4px; color:#111827; text-align:left;">{y_score}</div>
                </div>
                <div style="width:34px; text-align:center; font-weight:700; color:#6b7280">vs</div>
                <div style="flex:1; text-align:right;">
                    <div style="font-size:13px; font-weight:600; color:#111827">
                        <a href="{t_url}" target="_blank" style="color:inherit; text-decoration:none;">
                            {think_name} <span style="font-size:11px; font-weight:700; opacity:.7;">↗</span>
                        </a>
                    </div>
                    <div style="font-size:28px; font-weight:800; margin-top:4px; color:#111827; text-align:right;">{t_score}</div>
                </div>
            </div>
            <div style="margin-top:10px; font-size:12px; color:#6b7280;">
                Winner: <span style="font-weight:700; color:{color}">{winner}</span>{badge}
            </div>
        </div>
        """

    for i, (_, row) in enumerate(gw_df.iterrows()):
        cols[i % 3].markdown(
            mini_match_card(
                row["young_name"], row["young_id"], row["young_score"],
                row["think_name"], row["think_id"], row["think_score"],
                row["winner"], sel_gw
            ),
            unsafe_allow_html=True
        )

    # NOTE: The "Team Points by Gameweek" section was removed per request.

    # ── Combined player rankings (Best → Worst)
    st.divider()
    st.subheader("Player Rankings (Wins, then Total FPL Points)")
    df_ranked = df_player_summary.copy().reset_index(drop=True)
    df_ranked.insert(0, "Rank", df_ranked.index + 1)
    ranked_view = df_ranked[["Rank", "player_name", "team", "wins", "total_fpl_points"]].rename(columns={
        "player_name": "Player",
        "team": "Team",
        "wins": "Wins",
        "total_fpl_points": "Total FPL Points",
    })
    st.dataframe(center_df(ranked_view), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# ALL GAMES
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
        "young_name": f"{TEAM_BBBSAS} player",
        "young_score": f"{TEAM_BBBSAS} score",
        "think_name": f"{TEAM_GEESE} player",
        "think_score": f"{TEAM_GEESE} score",
        "winner":"Winner",
    }).sort_values(["GW", f"{TEAM_BBBSAS} player"])

    if pre_season:
        for c in [f"{TEAM_BBBSAS} score", f"{TEAM_GEESE} score"]:
            tidy[c] = tidy[c].apply(lambda v: "—" if isinstance(v, int) and v == 0 else v)
        tidy["Winner"] = "—"

    st.dataframe(center_df(tidy), use_container_width=True)
