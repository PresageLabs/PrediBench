from datetime import date, datetime

import pandas as pd
from plotly import graph_objects as go

from predibench.logger_config import get_logger

logger = get_logger(__name__)

FONT_FAMILY = "Arial"
BOLD_FONT_FAMILY = "Arial"


def date_to_string(date: datetime) -> str:
    """Convert a datetime object to YYYY-MM-DD string format."""
    return date.strftime("%Y-%m-%d")


def string_to_date(date_str: str) -> datetime:
    """Convert a YYYY-MM-DD string to datetime object."""
    return datetime.strptime(date_str, "%Y-%m-%d")


def convert_polymarket_time_to_datetime(time_str: str) -> datetime:
    """Convert a Polymarket time string to a datetime object."""
    return datetime.fromisoformat(time_str.replace("Z", "")).replace(tzinfo=None)


def apply_template(
    fig: go.Figure,
    template="none",
    annotation_text="",
    title=None,
    width=600,
    height=500,
    font_size=14,
):
    """Applies template in-place to input fig."""
    layout_updates = {
        "template": template,
        "width": width,
        "height": height,
        "font": dict(family=FONT_FAMILY, size=font_size),
        "title_font_family": BOLD_FONT_FAMILY,
        "title_font_size": 24,
        "title_xanchor": "center",
        "title_font_weight": "bold",
        "legend": dict(
            itemsizing="constant",
            title_font_family=BOLD_FONT_FAMILY,
            font=dict(family=BOLD_FONT_FAMILY, size=font_size),
            itemwidth=30,
        ),
    }
    if len(annotation_text) > 0:
        layout_updates["annotations"] = [
            dict(
                text=f"<i>{annotation_text}</i>",
                xref="paper",
                yref="paper",
                x=1.05,
                y=-0.05,
                xanchor="left",
                yanchor="top",
                showarrow=False,
                font=dict(size=font_size),
            )
        ]
    # Don't save titles in JSON figures - titles will be handled in React
    # if title is not None:
    #     layout_updates["title"] = title
    fig.update_layout(layout_updates)
    fig.update_xaxes(
        title_font_family=FONT_FAMILY,
        tickfont_family=FONT_FAMILY,
        tickfont_size=font_size,
        linewidth=1,
    )
    fig.update_yaxes(
        title_font_family=FONT_FAMILY,
        tickfont_family=FONT_FAMILY,
        tickfont_size=font_size,
        linewidth=1,
    )
    return


def _to_date_index(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with index converted to Python date objects.

    Ensures consistent comparisons and intersections between positions (date)
    and prices indices. Duplicates (same day) keep the last value.
    """
    if df is None or len(df.index) == 0:
        return df
    new_index: list[date] = []
    for idx in df.index:
        if isinstance(idx, datetime):
            new_index.append(idx.date())
        elif hasattr(idx, "date") and not isinstance(idx, date):
            # e.g., pandas Timestamp
            new_index.append(idx.date())
        else:
            new_index.append(idx)
    df2 = df.copy()
    df2.index = pd.Index(new_index)
    # remove duplicates by keeping last
    df2 = df2[~df2.index.duplicated(keep="last")]
    return df2

def get_model_color(model_name: str, model_index: int) -> str:
    """Get consistent color for model using canonical provider brand colors."""
    # OpenAI models - different greys (avoid black due to black background)
    if any(name in model_name for name in ["GPT-5 Mini", "GPT-5", "GPT-4.1", "GPT-OSS"]):
        if "GPT-5 Mini" in model_name:
            return "#606060"  # Dark grey for GPT-5 Mini
        elif "GPT-5" in model_name:
            return "#404040"  # Darker grey for GPT-5
        elif "GPT-OSS 120B" in model_name:
            return "#808080"  # Medium grey for GPT-OSS
        else:  # GPT-4.1
            return "#505050"  # Mid-dark grey for GPT-4.1

    # Anthropic Claude - canonical warm terra cotta
    elif "Claude" in model_name:
        return "#CC785C"  # Anthropic's Antique Brass/Terra Cotta

    # Google Gemini - canonical Google Blue
    elif "Gemini" in model_name:
        return "#4285F4"  # Google Blue for all Gemini models

    # xAI Grok - grey (avoid black due to black background)
    elif "Grok" in model_name:
        return "#707070"  # Grey for Grok (xAI uses black but we need contrast)

    # Perplexity Sonar - canonical turquoise
    elif "Sonar" in model_name:
        return "#20B8CD"  # Perplexity's turquoise

    # DeepSeek - canonical blue
    elif "DeepSeek" in model_name:
        return "#0D28F3"  # DeepSeek's bold blue

    # Qwen (Alibaba) - canonical violet/purple
    elif "Qwen" in model_name:
        return "#8B5CF6"  # Qwen's violet

    # Meta models - Azure Blue
    elif any(name in model_name for name in ["Meta", "Llama"]):
        return "#0082FB"  # Meta Azure Radiance

    # Baseline - neutral grey
    elif "Baseline" in model_name:
        return "#808080"  # Neutral grey for baseline

    else:
        # Fallback colors for any other models
        additional_colors = ["#F59E0B", "#EF4444", "#06B6D4", "#84CC16", "#EC4899"]
        return additional_colors[model_index % len(additional_colors)]
