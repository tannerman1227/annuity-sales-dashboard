"""Colors and CSS shared by the charts and the Streamlit shell."""

from __future__ import annotations

NAVY = "#12344D"
INK = "#1C2833"
GOLD = "#A67C3D"
TEAL = "#1F6A62"
BRICK = "#8C4034"
SLATE = "#5C6B76"
PAPER = "#F6F3EC"
LINE = "#E4DDD0"
CARD = "#FFFFFF"

FONT = "Source Sans 3, Segoe UI, sans-serif"
SERIF = "Source Serif 4, Georgia, serif"

PRODUCT_COLORS = {
    "Fixed": NAVY,
    "Fixed Indexed": GOLD,
    "Variable": TEAL,
    "MYGA": BRICK,
}
CHANNEL_COLORS = {
    "Independent Agents": NAVY,
    "Banks": TEAL,
    "Broker-Dealers": GOLD,
}

MAP_SCALE = [
    [0.0, "#F3EFE6"],
    [0.2, "#E7D7A8"],
    [0.55, "#2F6F8F"],
    [1.0, NAVY],
]


def css() -> str:
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,520;8..60,650&display=swap');

html, body, [class*="css"] {
  font-family: "Source Sans 3", "Segoe UI", sans-serif;
}
.stApp {
  background: #F6F3EC;
  color: #1C2833;
}
.block-container {
  padding-top: 1.25rem;
  padding-bottom: 2.5rem;
  max-width: 1240px;
}
header[data-testid="stHeader"] {
  background: transparent;
}
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {
  visibility: hidden;
  height: 0;
}
[data-testid="stSidebar"] {
  background: #FBF9F4;
  border-right: 1px solid #E4DDD0;
}
[data-testid="stSidebar"] .block-container {
  padding-top: 1.4rem;
}
h2.section-title, h1.hero-title {
  font-family: "Source Serif 4", Georgia, serif;
  color: #12344D;
  letter-spacing: -0.02em;
  font-weight: 650;
}
h1.hero-title {
  font-size: 3rem;
  line-height: 1;
  margin: 0.15rem 0 0.45rem;
}
h2.section-title {
  font-size: 1.55rem;
  margin: 1.35rem 0 0.15rem;
}
[data-testid="stSidebar"] [data-testid="stAlert"] {
  padding: 0.45rem 0.7rem;
}
.eyebrow {
  color: #A67C3D;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-size: 0.75rem;
}
.lede, .chart-label {
  font-family: "Source Serif 4", Georgia, serif;
  color: #12344D;
  font-size: 1.2rem;
  margin: 0.55rem 0 0;
}
.section-caption, .scope {
  color: #5C6B76;
  font-size: 0.98rem;
  line-height: 1.45;
  margin: 0 0 0.35rem;
}
.banner {
  background: #12344D;
  color: #F6F3EC;
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 0.92rem;
  line-height: 1.4;
  margin: 0.8rem 0 1rem;
}
.scope {
  margin-top: 0.2rem;
}
.brand {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 0.4rem;
}
.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 9px;
  background: #12344D;
  color: #F3E6C4;
  display: grid;
  place-items: center;
  font-family: "Source Serif 4", Georgia, serif;
  font-size: 1.05rem;
  font-weight: 650;
}
.brand-name {
  font-family: "Source Serif 4", Georgia, serif;
  color: #12344D;
  font-size: 1.15rem;
  line-height: 1.1;
}
.brand-sub {
  color: #5C6B76;
  font-size: 0.82rem;
}
.kpi {
  background: #FFFFFF;
  border: 1px solid #E4DDD0;
  border-top: 3px solid #12344D;
  border-radius: 12px;
  padding: 14px 16px 12px;
  min-height: 128px;
  box-shadow: 0 1px 1px rgba(18, 52, 77, 0.04);
}
.kpi-label {
  color: #5C6B76;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.kpi-value {
  color: #12344D;
  font-family: "Source Serif 4", Georgia, serif;
  font-size: 1.85rem;
  line-height: 1.15;
  margin-top: 0.25rem;
}
.kpi-note {
  color: #5C6B76;
  font-size: 0.88rem;
  margin-top: 0.35rem;
  line-height: 1.35;
}
.kpi-note.up { color: #1F6A62; font-weight: 600; }
.kpi-note.down { color: #8C4034; font-weight: 600; }
.insight {
  background: #FFFFFF;
  border: 1px solid #E4DDD0;
  border-left: 3px solid #A67C3D;
  border-radius: 10px;
  padding: 12px 14px;
  color: #1C2833;
  font-size: 0.95rem;
  line-height: 1.45;
  min-height: 118px;
}
.note, .panel {
  background: #FFFFFF;
  border: 1px solid #E4DDD0;
  border-radius: 12px;
  padding: 12px 14px;
}
.note {
  color: #1C2833;
  font-size: 0.94rem;
  line-height: 1.5;
}
table.compare {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
}
table.compare th {
  text-align: left;
  color: #5C6B76;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 700;
  padding: 0 0 8px;
  border-bottom: 1px solid #E4DDD0;
}
table.compare td {
  padding: 8px 8px 8px 0;
  border-bottom: 1px solid #F0EBE1;
  color: #1C2833;
}
table.compare td.num, table.compare th.num { text-align: right; padding-right: 0; }
table.compare td.up { color: #1F6A62; font-weight: 700; text-align: right; }
table.compare td.down { color: #8C4034; font-weight: 700; text-align: right; }
table.compare td.flat { color: #5C6B76; font-weight: 700; text-align: right; }
.footer {
  color: #5C6B76;
  font-size: 0.92rem;
  margin-top: 0.6rem;
  padding-top: 0.8rem;
  border-top: 1px solid #E4DDD0;
}
.footer a { color: #12344D; font-weight: 600; text-decoration: none; }
.footer a:hover { text-decoration: underline; }
div[data-testid="stExpander"] {
  background: #FFFFFF;
  border: 1px solid #E4DDD0;
  border-radius: 12px;
}
</style>
"""
