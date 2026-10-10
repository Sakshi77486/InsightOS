from pathlib import Path
from datetime import datetime
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from xml.sax.saxutils import escape


REPORT_DIR = Path("data/reports")
REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# HELPERS
# =========================================================

def clean_ai_text(text):
    if not text:
        return ""

    text = text.replace("###", "")
    text = text.replace("##", "")
    text = text.replace("#", "")
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("`", "")

    return text.strip()


def make_table(data, col_widths=None, font_size=8):

    table = Table(
        data,
        colWidths=col_widths,
        repeatRows=1
    )

    table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.lightgrey
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                font_size
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),
            (
                "PADDING",
                (0, 0),
                (-1, -1),
                5
            )
        ])
    )

    return table


# =========================================================
# REPORT GENERATOR
# =========================================================

def generate_report(
    dataset_id,
    dataset_name,
    analytics,
    anomalies,
    forecast_data=None,
    ai_insight=None
):

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    safe_name = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        Path(dataset_name).stem
    )

    file_path = (
        REPORT_DIR
        / f"report_{dataset_id}_{safe_name}_{timestamp}.pdf"
    )

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    title_style.alignment = TA_CENTER

    heading_style = styles["Heading2"]
    subheading_style = styles["Heading3"]
    normal_style = styles["BodyText"]

    story = []

    # =====================================================
    # HEADER
    # =====================================================

    story.append(
        Paragraph(
            "INSIGHTOS",
            title_style
        )
    )

    story.append(
        Paragraph(
            "AI ANALYTICS REPORT",
            heading_style
        )
    )

    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            f"<b>Dataset:</b> "
            f"{escape(dataset_name)}",
            normal_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Dataset ID:</b> "
            f"{dataset_id}",
            normal_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Generated:</b> "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            normal_style
        )
    )

    story.append(Spacer(1, 20))

    # =====================================================
    # 1. EXECUTIVE SUMMARY
    # =====================================================

    story.append(
        Paragraph(
            "1. Executive Summary",
            heading_style
        )
    )

    summary_data = [
        ["Metric", "Value"],
        [
            "Total Records",
            analytics.get("rows", 0)
        ],
        [
            "Total Columns",
            analytics.get("columns", 0)
        ],
        [
            "Missing Values",
            analytics.get("missing_values", 0)
        ],
        [
            "Duplicate Rows",
            analytics.get("duplicate_rows", 0)
        ],
        [
            "Numeric Columns",
            len(
                analytics.get(
                    "numeric_columns",
                    []
                )
            )
        ],
        [
            "Categorical Columns",
            len(
                analytics.get(
                    "categorical_columns",
                    []
                )
            )
        ],
        [
            "Date Columns",
            len(
                analytics.get(
                    "datetime_columns",
                    []
                )
            )
        ]
    ]

    story.append(
        make_table(
            summary_data,
            [250, 150]
        )
    )

    story.append(Spacer(1, 15))

    # =====================================================
    # KEY FINDINGS
    # =====================================================

    story.append(
        Paragraph(
            "Key Findings",
            heading_style
        )
    )

    trends = analytics.get(
        "trend",
        {}
    )

    for column, trend in trends.items():

        growth = trend.get(
            "growth_percentage"
        )

        direction = trend.get(
            "direction",
            "unknown"
        )

        if growth is not None:

            text = (
                f"{escape(str(column))} "
                f"is showing a "
                f"{direction} trend "
                f"with an overall change "
                f"of {growth:.2f}%."
            )

        else:

            text = (
                f"{escape(str(column))} "
                f"has an {direction} trend."
            )

        story.append(
            Paragraph(
                f"• {text}",
                normal_style
            )
        )

    story.append(Spacer(1, 15))

    # =====================================================
    # 2. DATA QUALITY
    # =====================================================

    story.append(
        Paragraph(
            "2. Data Quality",
            heading_style
        )
    )

    quality_data = [
        ["Metric", "Value"],
        [
            "Rows",
            analytics.get("rows", 0)
        ],
        [
            "Columns",
            analytics.get("columns", 0)
        ],
        [
            "Missing Values",
            analytics.get(
                "missing_values",
                0
            )
        ],
        [
            "Duplicate Rows",
            analytics.get(
                "duplicate_rows",
                0
            )
        ],
        [
            "Numeric Columns",
            ", ".join(
                map(
                    str,
                    analytics.get(
                        "numeric_columns",
                        []
                    )
                )
            )
        ],
        [
            "Categorical Columns",
            ", ".join(
                map(
                    str,
                    analytics.get(
                        "categorical_columns",
                        []
                    )
                )
            )
        ],
        [
            "Date Columns",
            ", ".join(
                map(
                    str,
                    analytics.get(
                        "datetime_columns",
                        []
                    )
                )
            )
        ]
    ]

    story.append(
        make_table(
            quality_data,
            [200, 200]
        )
    )

    story.append(Spacer(1, 15))

    # =====================================================
    # 3. PERFORMANCE ANALYSIS
    # =====================================================

    story.append(
        Paragraph(
            "3. Performance Analysis",
            heading_style
        )
    )

    statistics = analytics.get(
        "statistics",
        {}
    )

    for column, stats in statistics.items():

        story.append(
            Paragraph(
                escape(str(column)),
                subheading_style
            )
        )

        performance_data = [
            ["Metric", "Value"],
            [
                "Count",
                stats.get("count", 0)
            ],
            [
                "Total",
                stats.get("sum", 0)
            ],
            [
                "Average",
                stats.get("mean", 0)
            ],
            [
                "Median",
                stats.get("median", 0)
            ],
            [
                "Minimum",
                stats.get("minimum", 0)
            ],
            [
                "Maximum",
                stats.get("maximum", 0)
            ],
            [
                "Standard Deviation",
                stats.get("std", 0)
            ],
            [
                "Variance",
                stats.get("variance", 0)
            ],
            [
                "Range",
                stats.get("range", 0)
            ]
        ]

        story.append(
            make_table(
                performance_data,
                [200, 200]
            )
        )

        story.append(Spacer(1, 12))

    # =====================================================
    # 4. ADVANCED TREND ANALYSIS
    # =====================================================

    story.append(
        Paragraph(
            "4. Trend Analysis",
            heading_style
        )
    )

    trend_data = [
        [
            "Column",
            "Growth",
            "Period Growth",
            "MA Growth",
            "Direction"
        ]
    ]

    for column, trend in trends.items():

        trend_data.append([
            str(column),

            (
                f"{trend.get('growth_percentage'):.2f}%"
                if trend.get(
                    "growth_percentage"
                ) is not None
                else "-"
            ),

            (
                f"{trend.get('period_growth_percentage'):.2f}%"
                if trend.get(
                    "period_growth_percentage"
                ) is not None
                else "-"
            ),

            (
                f"{trend.get('moving_average_growth_percentage'):.2f}%"
                if trend.get(
                    "moving_average_growth_percentage"
                ) is not None
                else "-"
            ),

            trend.get(
                "direction",
                "-"
            )
        ])

    story.append(
        make_table(
            trend_data,
            [90, 80, 100, 90, 80]
        )
    )

    story.append(Spacer(1, 10))

    # Detailed trend metrics

    for column, trend in trends.items():

        story.append(
            Paragraph(
                escape(str(column)),
                subheading_style
            )
        )

        detailed_trend = [
            ["Metric", "Value"],

            [
                "First Value",
                trend.get(
                    "first_value",
                    "-"
                )
            ],

            [
                "Last Value",
                trend.get(
                    "last_value",
                    "-"
                )
            ],

            [
                "First Period Average",
                trend.get(
                    "first_period_average",
                    "-"
                )
            ],

            [
                "Last Period Average",
                trend.get(
                    "last_period_average",
                    "-"
                )
            ],

            [
                "Moving Average Window",
                trend.get(
                    "moving_average_window",
                    "-"
                )
            ],

            [
                "Current Moving Average",
                trend.get(
                    "moving_average_current",
                    "-"
                )
            ],

            [
                "Mean",
                trend.get(
                    "mean",
                    "-"
                )
            ],

            [
                "Median",
                trend.get(
                    "median",
                    "-"
                )
            ],

            [
                "Volatility (CV)",
                (
                    f"{trend.get('coefficient_of_variation'):.2f}%"
                    if trend.get(
                        "coefficient_of_variation"
                    ) is not None
                    else "-"
                )
            ]
        ]

        story.append(
            make_table(
                detailed_trend,
                [200, 200]
            )
        )

        story.append(Spacer(1, 10))

        best = trend.get(
            "best_record",
            {}
        )

        worst = trend.get(
            "worst_record",
            {}
        )

        story.append(
            Paragraph(
                f"<b>Best Record:</b> "
                f"{best.get('value', '-')}"
                f" "
                f"{best.get('date', '')}",
                normal_style
            )
        )

        story.append(
            Paragraph(
                f"<b>Worst Record:</b> "
                f"{worst.get('value', '-')}"
                f" "
                f"{worst.get('date', '')}",
                normal_style
            )
        )

    story.append(Spacer(1, 15))

    # =====================================================
    # 5. ANOMALY ANALYSIS
    # =====================================================

    story.append(
        Paragraph(
            "5. Anomaly Analysis",
            heading_style
        )
    )

    total_records = anomalies.get(
        "total_records",
        0
    )

    anomaly_count = anomalies.get(
        "anomalies_found",
        0
    )

    anomaly_rate = anomalies.get(
        "anomaly_rate"
    )

    if anomaly_rate is None:

        anomaly_rate = (
            (
                anomaly_count
                / total_records
            ) * 100
            if total_records
            else 0
        )

    anomaly_summary = [
        ["Metric", "Value"],

        [
            "Records Analyzed",
            total_records
        ],

        [
            "Anomalies Detected",
            anomaly_count
        ],

        [
            "Anomaly Rate",
            f"{anomaly_rate:.2f}%"
        ],

        [
            "Features Used",
            ", ".join(
                map(
                    str,
                    anomalies.get(
                        "features_used",
                        []
                    )
                )
            )
        ]
    ]

    story.append(
        make_table(
            anomaly_summary,
            [200, 200]
        )
    )

    story.append(Spacer(1, 10))

    anomaly_rows = anomalies.get(
        "anomalies",
        []
    )

    if anomaly_rows:

        story.append(
            Paragraph(
                "Detected Anomalies",
                subheading_style
            )
        )

        anomaly_table = [
            [
                "Date / Record",
                "Value",
                "Type",
                "Deviation",
                "Z-Score"
            ]
        ]

        for item in anomaly_rows[:20]:

            record = item.get(
                "record",
                {}
            )

            details = item.get(
                "details",
                {}
            )

            detail_values = list(
                details.values()
            )

            if not detail_values:
                continue

            detail = detail_values[0]

            date_value = ""

            for key, value in record.items():

                if (
                    "date" in str(key).lower()
                    or "time" in str(key).lower()
                ):

                    date_value = str(value)
                    break

            anomaly_table.append([
                date_value,

                detail.get(
                    "value",
                    "-"
                ),

                str(
                    detail.get(
                        "type",
                        "-"
                    )
                ).upper(),

                (
                    f"{detail.get('deviation_percentage'):.2f}%"
                    if detail.get(
                        "deviation_percentage"
                    ) is not None
                    else "-"
                ),

                detail.get(
                    "z_score",
                    "-"
                )
            ])

        story.append(
            make_table(
                anomaly_table,
                [105, 75, 65, 85, 65],
                font_size=7
            )
        )

    else:

        story.append(
            Paragraph(
                "No anomalies were detected.",
                normal_style
            )
        )

    story.append(Spacer(1, 15))

    # =====================================================
    # 6. FORECAST
    # =====================================================

    story.append(
        Paragraph(
            "6. Forecast",
            heading_style
        )
    )

    if forecast_data:

        forecast_rows = forecast_data.get(
            "forecast",
            []
        )

        if forecast_rows:

            forecast_summary = [
                ["Metric", "Value"],

                [
                    "Historical Records",
                    forecast_data.get(
                        "historical_records",
                        "-"
                    )
                ],

                [
                    "Latest Value",
                    forecast_data.get(
                        "latest_value",
                        "-"
                    )
                ],

                [
                    "Historical Average",
                    forecast_data.get(
                        "historical_average",
                        "-"
                    )
                ],

                [
                    "Forecast Periods",
                    forecast_data.get(
                        "periods",
                        "-"
                    )
                ],

                [
                    "Forecast Average",
                    forecast_data.get(
                        "forecast_average",
                        "-"
                    )
                ],

                [
                    "Forecast Minimum",
                    forecast_data.get(
                        "forecast_minimum",
                        "-"
                    )
                ],

                [
                    "Forecast Maximum",
                    forecast_data.get(
                        "forecast_maximum",
                        "-"
                    )
                ],

                [
                    "Expected Growth",
                    (
                        f"{forecast_data.get('expected_growth_percentage'):.2f}%"
                        if forecast_data.get(
                            "expected_growth_percentage"
                        ) is not None
                        else "-"
                    )
                ],

                [
                    "Forecast Direction",
                    forecast_data.get(
                        "direction",
                        "-"
                    )
                ]
            ]

            story.append(
                make_table(
                    forecast_summary,
                    [200, 200]
                )
            )

            story.append(Spacer(1, 10))

            forecast_table = [
                [
                    "Date",
                    "Forecast Value"
                ]
            ]

            for row in forecast_rows:

                forecast_table.append([
                    str(
                        row.get(
                            "date",
                            "-"
                        )
                    ),

                    str(
                        row.get(
                            "value",
                            "-"
                        )
                    )
                ])

            story.append(
                make_table(
                    forecast_table,
                    [200, 200]
                )
            )

        else:

            story.append(
                Paragraph(
                    "Forecast data was not available.",
                    normal_style
                )
            )

    else:

        story.append(
            Paragraph(
                "Forecast could not be generated "
                "for this dataset.",
                normal_style
            )
        )

    story.append(Spacer(1, 15))

    # =====================================================
    # 7. AI BUSINESS INSIGHTS
    # =====================================================

    story.append(
        Paragraph(
            "7. AI Business Insights",
            heading_style
        )
    )

    if ai_insight:

        cleaned = clean_ai_text(
            ai_insight
        )

        lines = cleaned.splitlines()

        for line in lines:

            line = line.strip()

            if not line:
                continue

            if line.upper() in {
                "INSIGHTS",
                "RECOMMENDATIONS"
            }:

                story.append(
                    Paragraph(
                        f"<b>{escape(line)}</b>",
                        normal_style
                    )
                )

                story.append(
                    Spacer(1, 5)
                )

                continue

            line = re.sub(
                r"^\d+\.\s*",
                "",
                line
            )

            line = re.sub(
                r"^[•*-]\s*",
                "",
                line
            )

            if line:

                story.append(
                    Paragraph(
                        f"• {escape(line)}",
                        normal_style
                    )
                )

                story.append(
                    Spacer(1, 3)
                )

    else:

        story.append(
            Paragraph(
                "AI insights were not available.",
                normal_style
            )
        )

    story.append(Spacer(1, 15))

    # =====================================================
    # 8. DATA-DRIVEN RECOMMENDATIONS
    # =====================================================

    story.append(
        Paragraph(
            "8. Recommendations",
            heading_style
        )
    )

    recommendations = []

    # Trend recommendations

    for column, trend in trends.items():

        direction = trend.get(
            "direction"
        )

        period_growth = trend.get(
            "period_growth_percentage"
        )

        volatility = trend.get(
            "coefficient_of_variation"
        )

        if direction == "increasing":

            recommendations.append(
                f"Monitor the continued growth "
                f"of {column} and evaluate the "
                f"factors associated with the "
                f"positive trend."
            )

        elif direction == "decreasing":

            recommendations.append(
                f"Investigate the decline in "
                f"{column} and review the periods "
                f"where performance weakened."
            )

        else:

            recommendations.append(
                f"Continue monitoring {column} "
                f"for meaningful changes."
            )

        if (
            period_growth is not None
            and period_growth > 10
        ):

            recommendations.append(
                f"The recent-period growth in "
                f"{column} is significant; "
                f"monitor whether the improvement "
                f"continues."
            )

        if (
            volatility is not None
            and volatility > 20
        ):

            recommendations.append(
                f"{column} shows relatively high "
                f"variability; investigate periods "
                f"with unusually large fluctuations."
            )

    # Anomaly recommendation

    if anomaly_count > 0:

        recommendations.append(
            f"Review the {anomaly_count} detected "
            f"anomalous records to determine "
            f"whether they represent genuine "
            f"business events or data-quality issues."
        )

    # Forecast recommendation

    if forecast_data:

        forecast_direction = forecast_data.get(
            "direction"
        )

        expected_growth = forecast_data.get(
            "expected_growth_percentage"
        )

        if (
            forecast_direction == "increasing"
            and expected_growth is not None
        ):

            recommendations.append(
                f"The forecast indicates an expected "
                f"increase of {expected_growth:.2f}%; "
                f"monitor upcoming performance against "
                f"this projection."
            )

        elif (
            forecast_direction == "decreasing"
            and expected_growth is not None
        ):

            recommendations.append(
                f"The forecast indicates an expected "
                f"decline of {abs(expected_growth):.2f}%; "
                f"investigate potential performance risks."
            )

    # Limit repetitive recommendations

    unique_recommendations = []

    for recommendation in recommendations:

        if recommendation not in unique_recommendations:

            unique_recommendations.append(
                recommendation
            )

    for index, recommendation in enumerate(
        unique_recommendations[:6],
        start=1
    ):

        story.append(
            Paragraph(
                f"{index}. "
                f"{escape(recommendation)}",
                normal_style
            )
        )

        story.append(
            Spacer(1, 5)
        )

    # =====================================================
    # 9. DETAILED STATISTICS
    # =====================================================

    story.append(
        Paragraph(
            "9. Detailed Statistics",
            heading_style
        )
    )

    for column, stats in statistics.items():

        detailed = [
            ["Metric", "Value"]
        ]

        for key, value in stats.items():

            detailed.append([
                key.replace(
                    "_",
                    " "
                ).title(),

                str(value)
            ])

        story.append(
            Paragraph(
                escape(str(column)),
                subheading_style
            )
        )

        story.append(
            make_table(
                detailed,
                [200, 200]
            )
        )

        story.append(
            Spacer(1, 10)
        )

    # =====================================================
    # BUILD PDF
    # =====================================================

    doc.build(story)

    return str(file_path)