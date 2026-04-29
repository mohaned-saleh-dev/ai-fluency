#!/usr/bin/env python3
"""
Build Excel workbook: FY2025 (without AI path) and FY2026 (with AI Agent) on two sheets.
Edit DATA_2026 below with your real numbers. Regenerate: python3 build_care_scaling_excel.py
"""

import os

import xlsxwriter

OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "Care_Scaling_2025_2026.xlsx",
)

# --- 2026: source slide "Throughout 2026" (with AI Chat Agent) ---
DATA_2026 = {
    "contact_rate": 0.01,  # 1%
    "chats_m": 6.0,
    "containment_rate": 0.89,  # chats fully supported by AI
    "handoffs_m": 0.66,  # 660k handed to humans (11% of 6M)
    # Staffing index vs 2025 stress path (2.0 = double): slide "Care agents 40%" mapped as 0.40 * 2.0 = 0.8 on same scale
    "advisor_index": 0.80,
    "business_growth_yoy": 0.50,  # 50%
    "annualized_savings_musd": 1.27,
    "label_period": "Throughout 2026",
}

# 2025 without AI (slide "2025 Performance vs. Projections")
Y25_BASE = {"contact_rate": 0.022, "chats_m": 4.9, "handoffs_m": 1.0, "advisor_index": 1.0}
Y25_PROJ = {"contact_rate": 0.022, "chats_m": 8.0, "handoffs_m": 1.7, "advisor_index": 2.0}

TEAL_DEEP = "#0D4F52"
TEAL_GLOW = "#2DD4BF"
CORAL = "#F97316"
AMBER = "#FBBF24"
NAVY = "#0F172A"
SLATE = "#94A3B8"
GRID_DIM = "#334155"
GRID = "#E8ECEF"
PLOT_TOP = "#1E293B"
PLOT_BOTTOM = "#0B1120"
TEAL = "#0D7377"


def grad_linear(angle: int, *stops: tuple[int, str]) -> dict:
    return {
        "type": "gradient",
        "gradient": {
            "angle": angle,
            "colors": [{"position": p, "color": c} for p, c in stops],
        },
    }


def plotarea_dramatic() -> dict:
    return {
        "border": {"none": True},
        "fill": grad_linear(270, (0, PLOT_TOP), (100, PLOT_BOTTOM)),
    }


def chartarea_frame() -> dict:
    return {
        "border": {"color": GRID_DIM, "width": 0.5},
        "fill": grad_linear(135, (0, "#111827"), (100, "#020617")),
    }


def main():
    wb = xlsxwriter.Workbook(OUT, {"nan_inf_to_errors": True})

    fmt_title = wb.add_format(
        {"bold": True, "font_size": 14, "font_color": NAVY, "font_name": "Calibri"}
    )
    fmt_h1 = wb.add_format(
        {
            "bold": True,
            "font_size": 11,
            "font_color": "white",
            "bg_color": TEAL,
            "border": 1,
            "border_color": TEAL,
            "align": "center",
            "valign": "vcenter",
        }
    )
    fmt_h2 = wb.add_format(
        {
            "bold": True,
            "font_size": 10,
            "font_color": NAVY,
            "bg_color": GRID,
            "border": 1,
            "border_color": "#CCD3D9",
            "align": "left",
            "indent": 1,
        }
    )
    fmt_num = wb.add_format(
        {
            "font_size": 11,
            "border": 1,
            "border_color": "#CCD3D9",
            "align": "center",
            "num_format": "0.0",
        }
    )
    fmt_pct = wb.add_format(
        {
            "font_size": 11,
            "border": 1,
            "border_color": "#CCD3D9",
            "align": "center",
            "num_format": "0.0%",
        }
    )
    fmt_note = wb.add_format(
        {
            "italic": True,
            "font_size": 9,
            "font_color": SLATE,
            "text_wrap": True,
            "font_name": "Calibri",
        }
    )
    fmt_head_note = wb.add_format(
        {"bold": True, "font_size": 10, "font_color": NAVY, "font_name": "Calibri"}
    )
    fmt_usd_m = wb.add_format(
        {
            "font_size": 11,
            "border": 1,
            "border_color": "#CCD3D9",
            "align": "center",
            "num_format": r'[$$-409]#,##0.00"M"',
        }
    )
    fmt_ratio_x = wb.add_format(
        {
            "font_size": 11,
            "border": 1,
            "border_color": "#CCD3D9",
            "align": "center",
            "num_format": '0.00"x"',
        }
    )
    fmt_delta_pct = wb.add_format(
        {
            "font_size": 11,
            "border": 1,
            "border_color": "#CCD3D9",
            "align": "center",
            "num_format": "0.00%",
        }
    )
    fmt_delta_num = wb.add_format(
        {
            "font_size": 11,
            "border": 1,
            "border_color": "#CCD3D9",
            "align": "center",
            "num_format": "0.0",
        }
    )

    lbl_light = {"color": "#F1F5F9", "size": 10, "bold": True}
    lbl_axis = {"color": "#CBD5E1", "size": 10}
    legend_font = {"color": "#E2E8F0", "size": 9}
    dl = {
        "value": True,
        "num_format": "0.00",
        "position": "above",
        "font": {"color": "#F8FAFC", "size": 9, "bold": True},
    }

    # ========== Sheet: 2025 ==========
    s25 = wb.add_worksheet("2025")
    s25.set_tab_color(TEAL)
    s25.set_column("A:A", 36)
    s25.set_column("B:D", 16)

    s25.merge_range("A1:D1", "2025 performance vs. projections (without AI Chat Agent)", fmt_title)
    s25.write("A3", "Scenario", fmt_head_note)
    s25.merge_range(
        "B3:D3",
        "If we had not shipped the AI Chat Agent: constant contact rate, volume scales with business growth.",
        fmt_note,
    )
    s25.write_row(4, 0, ["Metric", "Baseline 2025", "Projected EoY 2025", "Delta"], fmt_h1)
    # Main metrics: B/C inputs; C6 projected contact = flat rate (=B6); D = C-B
    s25.write(5, 0, "Contact rate", fmt_h2)
    s25.write_number(5, 1, Y25_BASE["contact_rate"], fmt_pct)
    s25.write_formula(5, 2, "=B6", fmt_pct)
    s25.write_formula(5, 3, "=C6-B6", fmt_delta_pct)

    s25.write(6, 0, "Chats per year (millions)", fmt_h2)
    s25.write_number(6, 1, Y25_BASE["chats_m"], fmt_num)
    s25.write_number(6, 2, Y25_PROJ["chats_m"], fmt_num)
    s25.write_formula(6, 3, "=C7-B7", fmt_delta_num)

    s25.write(7, 0, "Handed off to human agents (millions)", fmt_h2)
    s25.write_number(7, 1, Y25_BASE["handoffs_m"], fmt_num)
    s25.write_number(7, 2, Y25_PROJ["handoffs_m"], fmt_num)
    s25.write_formula(7, 3, "=C8-B8", fmt_delta_num)

    s25.write(8, 0, "Care advisor need (relative scale)", fmt_h2)
    s25.write_number(8, 1, Y25_BASE["advisor_index"], fmt_num)
    s25.write_number(8, 2, Y25_PROJ["advisor_index"], fmt_num)
    s25.write_formula(8, 3, "=C9-B9", fmt_delta_num)

    r = 9
    s25.write(r, 0, "Business growth (YoY), driving volume", fmt_h2)
    s25.write_number(r, 1, 0.65, fmt_pct)
    s25.write(r, 2, "", fmt_note)
    s25.write(r, 3, "", fmt_note)

    s25.write(r + 2, 0, "Notes for the deck", fmt_head_note)
    s25.merge_range(
        r + 3,
        0,
        r + 5,
        3,
        "Edit baseline (B) and projected (C) as needed. C6 = B6 (flat contact rate). Delta is C-B. "
        "Business growth % is B10. Chart blocks reference the main table via formulas.",
        fmt_note,
    )

    # Chart helper block (2025) — row indices 0-based for xlsxwriter
    cr = 14
    s25.write(cr, 0, "Chart data (used by graphs below)", fmt_head_note)
    s25.write_row(cr + 1, 0, ["Series / period", "Baseline 2025", "Projected EoY 2025", "Change"], fmt_h1)
    s25.write(cr + 2, 0, "Chats per year (M)", fmt_h2)
    s25.write_formula(cr + 2, 1, "=$B$7", fmt_num)
    s25.write_formula(cr + 2, 2, "=$C$7", fmt_num)
    s25.write_formula(cr + 2, 3, "=$C$7/$B$7", fmt_ratio_x)
    s25.write(cr + 3, 0, "Handoffs to agents (M)", fmt_h2)
    s25.write_formula(cr + 3, 1, "=$B$8", fmt_num)
    s25.write_formula(cr + 3, 2, "=$C$8", fmt_num)
    s25.write_formula(cr + 3, 3, "=$C$8/$B$8", fmt_ratio_x)
    s25.write(cr + 4, 0, "Care advisor need (index)", fmt_h2)
    s25.write_formula(cr + 4, 1, "=$B$9", fmt_num)
    s25.write_formula(cr + 4, 2, "=$C$9", fmt_num)
    s25.write_formula(cr + 4, 3, "=$C$9/$B$9", fmt_ratio_x)

    tr = cr + 6
    s25.write(tr, 0, "Trend chart (normalized)", fmt_head_note)
    s25.write_row(tr + 1, 0, ["Point", "Chats", "Handoffs", "Advisor need"], fmt_h1)
    s25.write(tr + 2, 0, "Baseline 2025", fmt_h2)
    s25.write_number(tr + 2, 1, 1.0, fmt_num)
    s25.write_number(tr + 2, 2, 1.0, fmt_num)
    s25.write_number(tr + 2, 3, 1.0, fmt_num)
    s25.write(tr + 3, 0, "Projected EoY 2025", fmt_h2)
    s25.write_formula(tr + 3, 1, "=$C$7/$B$7", fmt_num)
    s25.write_formula(tr + 3, 2, "=$C$8/$B$8", fmt_num)
    s25.write_formula(tr + 3, 3, "=$C$9/$B$9", fmt_num)

    # Ranges: volume chart uses rows cr+2 .. cr+4 col 0, baseline col 1, proj col 2
    r_cat0, r_cat1 = cr + 2, cr + 3
    r_adv = cr + 4
    r_tr0, r_tr1 = tr + 2, tr + 3

    s25.hide_gridlines(2)

    col_chart = wb.add_chart({"type": "column", "subtype": "clustered"})
    col_chart.add_series(
        {
            "name": "Baseline 2025",
            "categories": ["2025", r_cat0, 0, r_cat1, 0],
            "values": ["2025", r_cat0, 1, r_cat1, 1],
            "fill": grad_linear(180, (0, "#0F766E"), (55, "#14B8A6"), (100, TEAL_GLOW)),
            "border": {"color": "#042F2E", "width": 0.75},
            "data_labels": {
                "value": True,
                "num_format": "0.0",
                "position": "outside_end",
                "font": lbl_light,
            },
        }
    )
    col_chart.add_series(
        {
            "name": "Projected EoY 2025 (no AI Chat Agent)",
            "categories": ["2025", r_cat0, 0, r_cat1, 0],
            "values": ["2025", r_cat0, 2, r_cat1, 2],
            "fill": grad_linear(180, (0, "#7C2D12"), (50, CORAL), (100, AMBER)),
            "border": {"color": "#431407", "width": 0.75},
            "data_labels": {
                "value": True,
                "num_format": "0.0",
                "position": "outside_end",
                "font": {"color": "#FFEDD5", "size": 10, "bold": True},
            },
        }
    )
    col_chart.set_title(
        {
            "name": "The volume cliff\nChats and human handoffs (M per year) if nothing changes but the business grows",
            "name_font": {"size": 15, "bold": True, "color": "#F8FAFC"},
        }
    )
    col_chart.set_y_axis(
        {
            "name": "Millions per year",
            "name_font": {"color": SLATE, "size": 10},
            "num_font": lbl_axis,
            "num_format": "0.0",
            "major_gridlines": {"visible": True, "line": {"color": "#1E293B", "transparency": 35}},
            "line": {"color": GRID_DIM},
            "min": 0,
        }
    )
    col_chart.set_x_axis({"text_axis": True, "num_font": lbl_axis, "line": {"color": GRID_DIM}})
    col_chart.set_legend({"position": "bottom", "font": legend_font})
    col_chart.set_chartarea(chartarea_frame())
    col_chart.set_plotarea(plotarea_dramatic())
    col_chart.set_size({"width": 920, "height": 420})
    s25.insert_chart("F2", col_chart)

    adv_chart = wb.add_chart({"type": "column", "subtype": "clustered"})
    adv_chart.add_series(
        {
            "name": "Baseline 2025",
            "categories": ["2025", r_adv, 0, r_adv, 0],
            "values": ["2025", r_adv, 1, r_adv, 1],
            "fill": grad_linear(180, (0, "#0F766E"), (100, "#5EEAD4")),
            "border": {"color": "#042F2E", "width": 0.75},
            "data_labels": {
                "value": True,
                "num_format": "0.0",
                "position": "outside_end",
                "font": lbl_light,
            },
        }
    )
    adv_chart.add_series(
        {
            "name": "Projected EoY 2025 (no AI Chat Agent)",
            "categories": ["2025", r_adv, 0, r_adv, 0],
            "values": ["2025", r_adv, 2, r_adv, 2],
            "fill": grad_linear(180, (0, "#9A3412"), (100, "#FDBA74")),
            "border": {"color": "#431407", "width": 0.75},
            "data_labels": {
                "value": True,
                "num_format": "0.0",
                "position": "outside_end",
                "font": {"color": "#FFEDD5", "size": 10, "bold": True},
            },
        }
    )
    adv_chart.set_title(
        {
            "name": "People scale follows volume\nCare advisor capacity (index)",
            "name_font": {"size": 12, "bold": True, "color": "#F8FAFC"},
        }
    )
    adv_chart.set_y_axis(
        {
            "name": "Index (baseline = 1.0)",
            "name_font": {"color": SLATE, "size": 10},
            "num_font": lbl_axis,
            "num_format": "0.0",
            "major_gridlines": {"visible": True, "line": {"color": "#1E293B", "transparency": 40}},
            "line": {"color": GRID_DIM},
            "min": 0,
            "max": 2.5,
        }
    )
    adv_chart.set_x_axis({"text_axis": True, "num_font": lbl_axis, "line": {"color": GRID_DIM}})
    adv_chart.set_legend({"position": "bottom", "font": legend_font})
    adv_chart.set_chartarea(chartarea_frame())
    adv_chart.set_plotarea(plotarea_dramatic())
    adv_chart.set_size({"width": 520, "height": 340})
    s25.insert_chart("F28", adv_chart)

    line_chart = wb.add_chart({"type": "line"})
    line_chart.add_series(
        {
            "name": "Chats (normalized)",
            "categories": ["2025", r_tr0, 0, r_tr1, 0],
            "values": ["2025", r_tr0, 1, r_tr1, 1],
            "line": {"color": TEAL_GLOW, "width": 5, "smooth": True},
            "marker": {
                "type": "circle",
                "size": 12,
                "fill": {"color": "#14B8A6"},
                "border": {"color": "#ECFEFF", "width": 1.5},
            },
            "data_labels": dl,
        }
    )
    line_chart.add_series(
        {
            "name": "Handoffs (normalized)",
            "categories": ["2025", r_tr0, 0, r_tr1, 0],
            "values": ["2025", r_tr0, 2, r_tr1, 2],
            "line": {"color": "#FB7185", "width": 5, "smooth": True},
            "marker": {
                "type": "circle",
                "size": 12,
                "fill": {"color": "#F43F5E"},
                "border": {"color": "#FFF1F2", "width": 1.5},
            },
            "data_labels": dl,
        }
    )
    line_chart.add_series(
        {
            "name": "Advisor need (index)",
            "categories": ["2025", r_tr0, 0, r_tr1, 0],
            "values": ["2025", r_tr0, 3, r_tr1, 3],
            "line": {"color": "#A78BFA", "width": 4, "smooth": True, "dash_type": "dash"},
            "marker": {
                "type": "diamond",
                "size": 10,
                "fill": {"color": "#7C3AED"},
                "border": {"color": "#EDE9FE", "width": 1.25},
            },
            "data_labels": dl,
        }
    )
    line_chart.set_title(
        {
            "name": "One trajectory, three signals\nIndexed to baseline = 1.0 (flat contact rate, 65% business growth)",
            "name_font": {"size": 14, "bold": True, "color": "#F8FAFC"},
        }
    )
    line_chart.set_y_axis(
        {
            "name": "Index vs baseline (1.0 = start of 2025)",
            "name_font": {"color": SLATE, "size": 10},
            "num_font": lbl_axis,
            "num_format": "0.0",
            "major_gridlines": {"visible": True, "line": {"color": "#1E293B", "transparency": 35}},
            "line": {"color": GRID_DIM},
            "min": 0,
            "max": 2.5,
        }
    )
    line_chart.set_x_axis({"text_axis": True, "num_font": lbl_axis, "line": {"color": GRID_DIM}})
    line_chart.set_legend({"position": "bottom", "font": legend_font})
    line_chart.set_chartarea(chartarea_frame())
    line_chart.set_plotarea(plotarea_dramatic())
    line_chart.set_size({"width": 920, "height": 400})
    s25.insert_chart("F50", line_chart)

    # ========== Sheet: 2026 ==========
    s26 = wb.add_worksheet("2026")
    s26.set_tab_color("#7C3AED")
    s26.set_column("A:A", 38)
    s26.set_column("B:E", 15)

    d6 = DATA_2026

    s26.merge_range("A1:E1", "2026 operating view (with AI Chat Agent)", fmt_title)
    s26.write("A3", "Scenario", fmt_head_note)
    s26.merge_range(
        "B3:E3",
        f"Operating view with the AI Chat Agent. Period: {d6['label_period']}. "
        "Numbers match leadership slide; edit DATA_2026 in this script to regenerate.",
        fmt_note,
    )

    s26.write_row(
        4,
        0,
        [
            "Metric",
            "2025 proj EoY (no AI ref)",
            "2026 (with AI Agent)",
            "Delta vs stress path",
        ],
        fmt_h1,
    )
    # Rows 6-12 Excel: stress ref (B) pulls from 2025 sheet where comparable; C is 2026 actuals
    s26.write(5, 0, "Contact rate", fmt_h2)
    s26.write_formula(5, 1, "='2025'!C6", fmt_pct)
    s26.write_number(5, 2, d6["contact_rate"], fmt_pct)
    s26.write_formula(5, 3, "=C6-B6", fmt_delta_pct)

    s26.write(6, 0, "Chats per year (millions)", fmt_h2)
    s26.write_formula(6, 1, "='2025'!C7", fmt_num)
    s26.write_number(6, 2, d6["chats_m"], fmt_num)
    s26.write_formula(6, 3, "=C7-B7", fmt_delta_num)

    s26.write(7, 0, "Handed off to human agents (millions)", fmt_h2)
    s26.write_formula(7, 1, "='2025'!C8", fmt_num)
    s26.write_number(7, 2, d6["handoffs_m"], fmt_num)
    s26.write_formula(7, 3, "=C8-B8", fmt_delta_num)

    s26.write(8, 0, "Chats fully supported by AI (containment)", fmt_h2)
    s26.write(8, 1, "-", fmt_num)
    s26.write_formula(8, 2, "=1-C8/C7", fmt_pct)
    s26.write(8, 3, "", fmt_note)

    s26.write(9, 0, "Care staffing (index; 2.0 = stress-path double)", fmt_h2)
    s26.write_formula(9, 1, "='2025'!C9", fmt_num)
    s26.write_number(9, 2, d6["advisor_index"], fmt_num)
    s26.write_formula(9, 3, "=C10-B10", fmt_delta_num)

    s26.write(10, 0, "Business growth (YoY)", fmt_h2)
    s26.write_formula(10, 1, "='2025'!$B$10", fmt_pct)
    s26.write_number(10, 2, d6["business_growth_yoy"], fmt_pct)
    s26.write_formula(10, 3, "=C11-B11", fmt_delta_pct)

    s26.write(11, 0, "Annualized savings (USD, millions)", fmt_h2)
    s26.write(11, 1, "-", fmt_num)
    s26.write_number(11, 2, d6["annualized_savings_musd"], fmt_usd_m)
    s26.write(11, 3, "", fmt_note)

    rr = 12

    s26.write(rr + 1, 0, "Notes", fmt_head_note)
    s26.merge_range(
        rr + 2,
        0,
        rr + 3,
        3,
        "Column B references the 2025 sheet (stress path) where applicable. Containment = 1 minus (handoffs / chats). "
        "Edit C6:C12 for 2026 inputs; B updates from 2025 automatically. Chart block below uses formulas.",
        fmt_note,
    )

    # Chart helpers: mirror main table (Excel rows 7-8 chats/handoffs, 10 staffing)
    c6 = rr + 6
    s26.write(c6, 0, "Chart data (linked to table above)", fmt_head_note)
    s26.write_row(c6 + 1, 0, ["Metric", "Stress (no AI ref)", "With AI (2026)"], fmt_h1)
    s26.write(c6 + 2, 0, "Chats per year (M)", fmt_h2)
    s26.write_formula(c6 + 2, 1, "=$B$7", fmt_num)
    s26.write_formula(c6 + 2, 2, "=$C$7", fmt_num)
    s26.write(c6 + 3, 0, "Handoffs to agents (M)", fmt_h2)
    s26.write_formula(c6 + 3, 1, "=$B$8", fmt_num)
    s26.write_formula(c6 + 3, 2, "=$C$8", fmt_num)
    s26.write(c6 + 4, 0, "Care staffing (index)", fmt_h2)
    s26.write_formula(c6 + 4, 1, "=$B$10", fmt_num)
    s26.write_formula(c6 + 4, 2, "=$C$10", fmt_num)

    c6b = c6 + 6
    s26.write(c6b, 0, "Contact rate (linked)", fmt_head_note)
    s26.write_row(c6b + 1, 0, ["", "Stress (no AI ref)", "With AI (2026)"], fmt_h1)
    s26.write(c6b + 2, 0, "Contact rate", fmt_h2)
    s26.write_formula(c6b + 2, 1, "=$B$6", fmt_pct)
    s26.write_formula(c6b + 2, 2, "=$C$6", fmt_pct)

    s26.hide_gridlines(2)

    m0, m1, m2 = c6 + 2, c6 + 3, c6 + 4
    cmp_chart = wb.add_chart({"type": "column", "subtype": "clustered"})
    cmp_chart.add_series(
        {
            "name": "2025 proj EoY (no AI ref)",
            "categories": ["2026", m0, 0, m2, 0],
            "values": ["2026", m0, 1, m2, 1],
            "fill": grad_linear(180, (0, "#7C2D12"), (50, CORAL), (100, AMBER)),
            "border": {"color": "#431407", "width": 0.75},
            "data_labels": {
                "value": True,
                "num_format": "0.0",
                "position": "outside_end",
                "font": {"color": "#FFEDD5", "size": 10, "bold": True},
            },
        }
    )
    cmp_chart.add_series(
        {
            "name": "2026 with AI Agent",
            "categories": ["2026", m0, 0, m2, 0],
            "values": ["2026", m0, 2, m2, 2],
            "fill": grad_linear(180, (0, "#065F46"), (55, "#34D399"), (100, "#A7F3D0")),
            "border": {"color": "#022C22", "width": 0.75},
            "data_labels": {
                "value": True,
                "num_format": "0.0",
                "position": "outside_end",
                "font": lbl_light,
            },
        }
    )
    cmp_chart.set_title(
        {
            "name": "Volume and staffing pressure\nStress path vs 2026 with AI (millions / index)",
            "name_font": {"size": 15, "bold": True, "color": "#F8FAFC"},
        }
    )
    cmp_chart.set_y_axis(
        {
            "name": "Scale (M or index)",
            "name_font": {"color": SLATE, "size": 10},
            "num_font": lbl_axis,
            "num_format": "0.0",
            "major_gridlines": {"visible": True, "line": {"color": "#1E293B", "transparency": 35}},
            "line": {"color": GRID_DIM},
            "min": 0,
        }
    )
    cmp_chart.set_x_axis({"text_axis": True, "num_font": lbl_axis, "line": {"color": GRID_DIM}})
    cmp_chart.set_legend({"position": "bottom", "font": legend_font})
    cmp_chart.set_chartarea(chartarea_frame())
    cmp_chart.set_plotarea(plotarea_dramatic())
    cmp_chart.set_size({"width": 920, "height": 440})
    s26.insert_chart("G2", cmp_chart)

    cr0 = c6b + 2
    rate_chart = wb.add_chart({"type": "column", "subtype": "clustered"})
    rate_chart.add_series(
        {
            "name": "Stress (no AI ref)",
            "categories": ["2026", cr0, 0, cr0, 0],
            "values": ["2026", cr0, 1, cr0, 1],
            "fill": grad_linear(180, (0, "#9A3412"), (100, "#FDBA74")),
            "border": {"color": "#431407", "width": 0.75},
            "data_labels": {
                "value": True,
                "num_format": "0.0%",
                "position": "outside_end",
                "font": {"color": "#FFEDD5", "size": 10, "bold": True},
            },
        }
    )
    rate_chart.add_series(
        {
            "name": "With AI (2026)",
            "categories": ["2026", cr0, 0, cr0, 0],
            "values": ["2026", cr0, 2, cr0, 2],
            "fill": grad_linear(180, (0, "#047857"), (100, "#6EE7B7")),
            "border": {"color": "#022C22", "width": 0.75},
            "data_labels": {
                "value": True,
                "num_format": "0.0%",
                "position": "outside_end",
                "font": lbl_light,
            },
        }
    )
    rate_chart.set_title(
        {
            "name": "Contact rate\nStress path vs 2026 with AI",
            "name_font": {"size": 13, "bold": True, "color": "#F8FAFC"},
        }
    )
    rate_chart.set_y_axis(
        {
            "name": "Percent of attempts",
            "name_font": {"color": SLATE, "size": 10},
            "num_font": lbl_axis,
            "num_format": "0.0%",
            "major_gridlines": {"visible": True, "line": {"color": "#1E293B", "transparency": 40}},
            "line": {"color": GRID_DIM},
            "min": 0,
            "max": 0.03,
        }
    )
    rate_chart.set_x_axis({"text_axis": True, "num_font": lbl_axis, "line": {"color": GRID_DIM}})
    rate_chart.set_legend({"position": "bottom", "font": legend_font})
    rate_chart.set_chartarea(chartarea_frame())
    rate_chart.set_plotarea(plotarea_dramatic())
    rate_chart.set_size({"width": 520, "height": 320})
    s26.insert_chart("G30", rate_chart)

    wb.close()
    print(f"Wrote: {OUT}")


if __name__ == "__main__":
    main()
