"""Hearth & Cedar Life — synthetic annuity sales dashboard.

Streamlit entry point. Metrics, checks, and charts live under src/ so they can
be tested without a browser. Every figure on the page is computed from the
seeded file in data/annuity_sales.csv.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from src.charts import (
    PLOT_CONFIG,
    chart_cumulative_ytd,
    chart_distributors,
    chart_forecast,
    chart_map,
    chart_mom,
    chart_monthly,
    chart_product_channel,
    chart_product_mix,
    chart_profile,
    format_delta,
    growth_class,
)
from src.constants import (
    AGE_BANDS,
    CHANNELS,
    PRODUCTS,
    SEED,
    STATE_WEIGHTS,
)
from src.forecast import forecast_monthly_premium
from src.formatting import format_count, format_day, format_pct, format_premium
from src.insights import build_insights
from src.metrics import (
    apply_filters,
    attach_growth,
    average_premium,
    breakdown,
    concentration,
    cumulative_ytd,
    growth_rate,
    monthly_frame,
    policy_count,
    prior_window_supported,
    product_channel,
    resolve_window,
    shift_years,
    state_rollup,
    top_distributors,
    total_premium,
    training_series,
    ytd_bounds,
)
from src.theme import BRICK, GOLD, NAVY, TEAL, css
from src.validation import validate_sales

DATA_PATH = Path(__file__).resolve().parent / "data" / "annuity_sales.csv"


@st.cache_data(show_spinner="Loading the synthetic book…")
def load_sales(path: str) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["issue_date"])
    frame["guarantee_years"] = frame["guarantee_years"].astype(int)
    return frame


def _ytd_note(current: float, prior: float, year: int) -> str:
    if prior <= 0:
        return '<div class="kpi-note">Prior YTD is not in this book</div>'
    gap = current - prior
    word = "ahead of" if gap >= 0 else "behind"
    return (
        f'<div class="kpi-note {growth_class(gap)}">'
        f"{format_premium(abs(gap))} {word} {year - 1} YTD</div>"
    )


def _note(growth, suffix: str) -> str:
    if growth is None or pd.isna(growth):
        return f'<div class="kpi-note">— {escape(suffix)}</div>'
    klass = growth_class(growth)
    return f'<div class="kpi-note {klass}">{escape(format_delta(growth))} {escape(suffix)}</div>'


def _kpi(label: str, value: str, note: str, accent: str) -> str:
    return (
        f'<div class="kpi" style="border-top-color:{accent}">'
        f'<div class="kpi-label">{escape(label)}</div>'
        f'<div class="kpi-value">{escape(value)}</div>'
        f"{note}</div>"
    )


def _scope(products, channels, states) -> str:
    def phrase(selected, noun: str) -> str:
        if not selected:
            return f"all {noun}"
        if len(selected) == 1:
            return str(selected[0])
        return f"{len(selected)} {noun}"

    return (
        f"{phrase(products, 'products')} · {phrase(channels, 'channels')} · "
        f"{phrase(states, 'states')}"
    )


def _comparison_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return '<div class="panel"><p class="section-caption">No premium in this year-to-date window.</p></div>'
    rows = []
    for record in frame.itertuples(index=False):
        growth = getattr(record, "premium_growth", None)
        prior = getattr(record, "prior_premium", None)
        growth_value = None if growth is None or pd.isna(growth) else float(growth)
        prior_value = None if prior is None or pd.isna(prior) else float(prior)
        rows.append(
            "<tr>"
            f"<td>{escape(str(record.product))}</td>"
            f"<td class='num'>{format_premium(record.premium)}</td>"
            f"<td class='num'>{format_premium(prior_value)}</td>"
            f"<td class='{growth_class(growth_value)}'>{format_pct(growth_value)}</td>"
            "</tr>"
        )
    return (
        '<div class="panel"><table class="compare"><thead><tr>'
        "<th>Product</th><th class='num'>YTD</th><th class='num'>Prior YTD</th><th class='num'>Growth</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _money_table(frame: pd.DataFrame, label: str, heading: str) -> pd.DataFrame:
    table = frame[[label, "premium", "policies", "avg_premium", "share"]].copy()
    table = table.rename(columns={label: heading})
    table["premium_m"] = table["premium"] / 1_000_000
    table["avg_k"] = table["avg_premium"] / 1_000
    table["share_pct"] = table["share"] * 100
    keep = [heading, "premium_m", "policies", "avg_k", "share_pct"]
    if "channel" in frame.columns and heading != "Channel":
        table.insert(1, "channel", frame["channel"].to_numpy())
        keep = [heading, "channel", "premium_m", "policies", "avg_k", "share_pct"]
    return table[keep]


def _column_config(name_label: str) -> dict:
    return {
        name_label: name_label,
        "channel": "Channel",
        "premium_m": st.column_config.NumberColumn("Premium ($M)", format="%.1f"),
        "policies": st.column_config.NumberColumn("Policies", format="%d"),
        "avg_k": st.column_config.NumberColumn("Average ($K)", format="%.0f"),
        "share_pct": st.column_config.NumberColumn("Share %", format="%.1f"),
    }


def render() -> None:
    st.set_page_config(
        page_title="Annuity Sales Dashboard",
        page_icon="▣",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(css(), unsafe_allow_html=True)

    if not DATA_PATH.exists():
        st.error("Missing data/annuity_sales.csv. From the repo root run `python -m src.data_gen`.")
        return

    sales = load_sales(str(DATA_PATH))
    validation = validate_sales(sales)
    data_min = pd.Timestamp(sales["issue_date"].min())
    data_max = pd.Timestamp(sales["issue_date"].max())

    st.sidebar.markdown(
        """
        <div class="brand">
          <div class="brand-mark">HC</div>
          <div>
            <div class="brand-name">Hearth &amp; Cedar</div>
            <div class="brand-sub">Annuity sales</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Fictional carrier. Synthetic book for a leadership sales review.")
    if validation.ok:
        st.sidebar.success(f"Validated · {validation.row_count:,} rows")
    else:
        st.sidebar.error("Validation failed")
        for issue in validation.issues:
            st.sidebar.write(issue)
        st.error("The synthetic dataset failed validation. Regenerate it with `python -m src.data_gen`.")
        for issue in validation.issues:
            st.write(f"- {issue}")
        return

    preset_labels = {
        "ytd": f"{data_max.year} YTD",
        "last_12": "Last 12 months",
        "since_2024": "Since 2024",
        "full": "Full history",
        "custom": "Custom range",
    }
    preset = st.sidebar.radio(
        "Date range",
        options=list(preset_labels),
        format_func=lambda key: preset_labels[key],
        index=0,
    )
    custom_start = custom_end = None
    if preset == "custom":
        picked = st.sidebar.date_input(
            "Issue dates",
            value=(data_min.date(), data_max.date()),
            min_value=data_min.date(),
            max_value=data_max.date(),
        )
        if isinstance(picked, tuple) and len(picked) == 2:
            custom_start, custom_end = picked
        else:
            st.sidebar.caption("Select both a start and an end date.")
            custom_start, custom_end = data_min.date(), data_max.date()

    products = st.sidebar.multiselect("Product", PRODUCTS, placeholder="All products")
    channels = st.sidebar.multiselect("Channel", CHANNELS, placeholder="All channels")
    states = st.sidebar.multiselect("State", list(STATE_WEIGHTS), placeholder="All states")
    st.sidebar.caption("Leave a list blank to include every value. Names in the book are fictional.")

    start, end = resolve_window(preset, data_min, data_max, custom_start, custom_end)
    product_filter = products or None
    channel_filter = channels or None
    state_filter = states or None

    population = apply_filters(sales, data_min, data_max, product_filter, channel_filter, state_filter)
    current = apply_filters(population, start, end)
    prior_start, prior_end = shift_years(start, end)
    matched = prior_window_supported(prior_start, data_min)
    prior = apply_filters(population, prior_start, prior_end) if matched else population.iloc[0:0]

    premium = total_premium(current)
    policies = policy_count(current)
    average = average_premium(current)
    period_growth = growth_rate(premium, total_premium(prior)) if matched else None
    policy_growth = growth_rate(policies, policy_count(prior)) if matched else None
    average_growth = (
        growth_rate(average, average_premium(prior)) if matched and average is not None else None
    )

    ytd_start, ytd_end = ytd_bounds(end)
    prior_ytd_start, prior_ytd_end = shift_years(ytd_start, ytd_end)
    ytd = apply_filters(population, ytd_start, ytd_end)
    prior_ytd = apply_filters(population, prior_ytd_start, prior_ytd_end)
    ytd_premium = total_premium(ytd)
    prior_ytd_premium = total_premium(prior_ytd)
    ytd_growth = growth_rate(ytd_premium, prior_ytd_premium)
    ytd_label = f"{ytd_end.year} YTD through {format_day(ytd_end)}"

    product_table = breakdown(current, "product", prior if matched else None, PRODUCTS)
    channel_table = breakdown(current, "channel", prior if matched else None, CHANNELS)
    region_table = breakdown(current, "region")
    age_table = breakdown(current, "annuitant_age_band", order=AGE_BANDS)
    tax_table = breakdown(current, "tax_status", order=["Qualified", "Non-qualified"])
    myga_current = current[current["product"] == "MYGA"]
    term_table = breakdown(myga_current, "guarantee_years", order=[3, 5, 7])
    if not term_table.empty:
        term_table = term_table.copy()
        term_table["term"] = term_table["guarantee_years"].map(lambda year: f"{int(year)}-year")
    ytd_products = breakdown(ytd, "product", prior_ytd, PRODUCTS)
    distributors = top_distributors(current, n=10)
    states_table = state_rollup(current)
    cross = product_channel(current)
    monthly = attach_growth(monthly_frame(current), monthly_frame(population))
    ytd_curve = cumulative_ytd(population, end, data_min)
    history, history_note = training_series(population, end)
    outlook = forecast_monthly_premium(history, horizon=6)
    top10 = concentration(current, n=10)
    insights = build_insights(
        premium=premium,
        policies=policies,
        period_growth=period_growth,
        prior_premium=total_premium(prior) if matched else None,
        period_start_text=format_day(start),
        period_end_text=format_day(end),
        ytd_growth=ytd_growth,
        ytd_label=ytd_label,
        products=product_table,
        channels=channel_table,
        regions=region_table,
        top10_share=top10,
    )

    st.sidebar.markdown("---")
    st.sidebar.write(f"Showing **{policies:,}** policies · {format_premium(premium)}")
    st.sidebar.download_button(
        "Download filtered rows",
        data=current.to_csv(index=False).encode("utf-8"),
        file_name="synthetic_annuity_sales_filtered.csv",
        mime="text/csv",
    )
    st.sidebar.caption(f"Synthetic book · seed {SEED}.")
    st.sidebar.markdown(
        '<div class="footer">Tanner Allred<br>'
        '<a href="https://github.com/tannerman1227" target="_blank">GitHub</a> · '
        '<a href="https://www.linkedin.com/in/tanner-allred" target="_blank">LinkedIn</a></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div id="anchor-overview"></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="eyebrow">Hearth &amp; Cedar Life · Fictional carrier · Leadership view</div>
        <h1 class="hero-title">Annuity sales</h1>
        <p class="lede">Issued premium for a synthetic book of fixed, fixed indexed, variable, and MYGA
        contracts. The page is a year-to-date sales review: what came in, where it came from,
        and a short planning outlook.</p>
        <div class="banner">Synthetic data, seeded and fully invented. Distributor and agent names are
        fictional. This is not the production, in-force block, or financial statement of any insurer.</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="scope">Window {escape(format_day(start))} – {escape(format_day(end))} · '
        f"{escape(_scope(products, channels, states))}</p>",
        unsafe_allow_html=True,
    )

    insight_columns = st.columns(len(insights))
    for column, text in zip(insight_columns, insights, strict=True):
        column.markdown(f'<div class="insight">{escape(text)}</div>', unsafe_allow_html=True)

    prior_suffix = "vs the same dates last year" if matched else "matched prior year is outside the book"
    cards = [
        _kpi("Selected premium", format_premium(premium), _note(period_growth, prior_suffix), NAVY),
        _kpi("Policies", format_count(policies), _note(policy_growth, prior_suffix), TEAL),
        _kpi(
            "Average premium",
            format_premium(average),
            _note(average_growth, prior_suffix),
            GOLD,
        ),
        _kpi(
            f"{ytd_end.year} YTD growth",
            format_pct(ytd_growth),
            _ytd_note(ytd_premium, prior_ytd_premium, ytd_end.year),
            BRICK,
        ),
    ]
    for column, card in zip(st.columns(4), cards, strict=True):
        column.markdown(card, unsafe_allow_html=True)

    if policies == 0:
        st.info("Nothing was issued in this window for the current filters.")
        return

    st.markdown('<div id="anchor-ytd"></div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-title">Year to date vs prior year</h2>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="section-caption">Calendar {ytd_end.year} through {escape(format_day(ytd_end))} '
        f"versus {escape(format_day(prior_ytd_start))} – {escape(format_day(prior_ytd_end))}. "
        "January stays in the comparison even when the date window starts later. "
        "Product, channel, and state filters still apply.</p>",
        unsafe_allow_html=True,
    )
    chart_col, table_col = st.columns([1.45, 1])
    with chart_col:
        st.plotly_chart(chart_cumulative_ytd(ytd_curve), width="stretch", config=PLOT_CONFIG)
    with table_col:
        st.markdown(
            _comparison_table(ytd_products.sort_values("premium", ascending=False)),
            unsafe_allow_html=True,
        )
        st.caption(
            f"YTD premium {format_premium(ytd_premium)} · prior YTD {format_premium(prior_ytd_premium)}."
        )

    st.markdown('<div id="anchor-trends"></div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-title">Trend</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-caption">Bars are issued premium inside the selected window. '
        "The gold line is growth against the same month a year earlier. That base month uses the "
        "product, channel, and state filters even when it falls outside the date window.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="chart-label">Monthly premium and year-over-year growth</p>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(chart_monthly(monthly), width="stretch", config=PLOT_CONFIG)
    st.plotly_chart(chart_mom(monthly), width="stretch", config=PLOT_CONFIG)
    st.caption("Month-over-month change uses only months inside the selected window. The first month has no comparison.")

    st.markdown('<h2 class="section-title">Mix</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-caption">Fixed indexed is the core product in this constructed book. '
        "Banks write a large share of MYGA, and variable premium sits mostly with broker-dealers.</p>",
        unsafe_allow_html=True,
    )
    mix_columns = st.columns(3)
    with mix_columns[0]:
        st.plotly_chart(chart_product_mix(product_table), width="stretch", config=PLOT_CONFIG)
    with mix_columns[1]:
        st.plotly_chart(
            chart_profile(channel_table, "channel", "By channel"),
            width="stretch",
            config=PLOT_CONFIG,
        )
    with mix_columns[2]:
        st.plotly_chart(
            chart_profile(region_table, "region", "By region"),
            width="stretch",
            config=PLOT_CONFIG,
        )
    st.plotly_chart(chart_product_channel(cross), width="stretch", config=PLOT_CONFIG)

    st.markdown('<div id="anchor-geography"></div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-title">Geography</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-caption">State of issue. Shares are of the filtered window, not of the industry.</p>',
        unsafe_allow_html=True,
    )
    map_col, state_col = st.columns([1.35, 1])
    with map_col:
        st.plotly_chart(chart_map(states_table), width="stretch", config=PLOT_CONFIG)
    with state_col:
        state_view = states_table.loc[states_table["premium"] > 0].copy()
        state_view["premium_m"] = state_view["premium"] / 1_000_000
        state_view["share_pct"] = state_view["share"] * 100
        st.dataframe(
            state_view[["state", "region", "premium_m", "policies", "share_pct"]],
            hide_index=True,
            height=500,
            column_config={
                "state": "State",
                "region": "Region",
                "premium_m": st.column_config.NumberColumn("Premium ($M)", format="%.1f"),
                "policies": st.column_config.NumberColumn("Policies", format="%d"),
                "share_pct": st.column_config.NumberColumn("Share %", format="%.1f"),
            },
        )

    st.markdown('<h2 class="section-title">Distributors</h2>', unsafe_allow_html=True)
    share_text = f"{top10:.1%} of premium" if top10 is not None else "—"
    st.markdown(
        f'<p class="section-caption">Ten largest firms in this window. Together they hold {share_text}. '
        "Every firm name is invented.</p>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(chart_distributors(distributors), width="stretch", config=PLOT_CONFIG)
    if not distributors.empty:
        dist_view = _money_table(distributors, "distributor_name", "Distributor")
        st.dataframe(
            dist_view,
            hide_index=True,
            column_config=_column_config("Distributor"),
        )

    st.markdown('<h2 class="section-title">Contract profile</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-caption">Annuitant age band and tax status of contracts issued in the window. '
        "The third chart is MYGA premium by guarantee period. Variable rows use guarantee year 0 "
        "because they do not have a multi-year rate guarantee, and they are left off that chart.</p>",
        unsafe_allow_html=True,
    )
    profile_cols = st.columns(3)
    with profile_cols[0]:
        st.plotly_chart(
            chart_profile(age_table, "annuitant_age_band", "Annuitant age"),
            width="stretch",
            config=PLOT_CONFIG,
        )
    with profile_cols[1]:
        st.plotly_chart(
            chart_profile(tax_table, "tax_status", "Tax status"),
            width="stretch",
            config=PLOT_CONFIG,
        )
    with profile_cols[2]:
        st.plotly_chart(
            chart_profile(term_table, "term", "MYGA guarantee"),
            width="stretch",
            config=PLOT_CONFIG,
        )

    st.markdown('<div id="anchor-forecast"></div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-title">Outlook</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-caption">Next six months of issued premium for the selected product, channel, '
        "and state. The fit uses every complete month through the end of the date window, including "
        "months before the window starts, and it ignores months after that end date.</p>",
        unsafe_allow_html=True,
    )
    if history_note:
        st.caption(history_note)
    next_three = None if outlook.forecast.empty else float(outlook.forecast["forecast"].iloc[:3].sum())
    next_six = None if outlook.forecast.empty else float(outlook.forecast["forecast"].sum())
    mape_text = "—" if outlook.in_sample_mape is None else f"{outlook.in_sample_mape:.1%}"
    outlook_cards = [
        _kpi("Next 3 months", format_premium(next_three), '<div class="kpi-note">Point forecast</div>', NAVY),
        _kpi("Next 6 months", format_premium(next_six), '<div class="kpi-note">Point forecast</div>', GOLD),
        _kpi("In-sample MAPE", mape_text, '<div class="kpi-note">Fit window, not a backtest holdout</div>', TEAL),
    ]
    for column, card in zip(st.columns(3), outlook_cards, strict=True):
        column.markdown(card, unsafe_allow_html=True)
    st.plotly_chart(
        chart_forecast(history, outlook.forecast),
        width="stretch",
        config=PLOT_CONFIG,
    )
    st.markdown(f'<div class="note">{escape(outlook.narrative)}</div>', unsafe_allow_html=True)

    with st.expander("How the numbers are defined"):
        st.markdown(
            """
- **Premium** is issued premium in US dollars for one contract. It is not account value, not annualized, and not a deposit net of free-look cancellations.
- **A policy** is one issued contract. Counts use distinct policy ids.
- **YTD** is January 1 through the end date of the selected window, for the filters in force.
- **Prior-year window** is the selected start and end shifted back one year. Growth is hidden when that window begins before January 2022, because the book does not contain the missing months.
- **Year-over-year** on the monthly chart compares each plotted month with the same month one year earlier.
- **Month-over-month** compares each plotted month with the previous plotted month.
- **Outlook** is a seasonal baseline: month-of-year indices and a straight-line trend on the deseasonalized series. The band is ± one in-sample residual standard deviation. It is not a prediction interval and it is not a pricing, reserving, or hedging model.
- **Validation** checks the schema, date range, premium bounds, product and channel lists, state/region pairs, distributor identity, and that each writing agent sits on that distributor's roster.
- **Source file** is `data/annuity_sales.csv`, regenerated by `python -m src.data_gen` with seed 1227.
            """
        )

    st.markdown(
        '<div class="footer">Portfolio project by Tanner Allred · '
        '<a href="https://github.com/tannerman1227" target="_blank">GitHub</a> · '
        '<a href="https://www.linkedin.com/in/tanner-allred" target="_blank">LinkedIn</a></div>',
        unsafe_allow_html=True,
    )


render()
