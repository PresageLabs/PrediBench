from __future__ import annotations

import pandas as pd
from pydantic import BaseModel


class DataPoint(BaseModel):
    date: str
    value: float

    @staticmethod
    def list_datapoints_from_series(series: pd.Series) -> list["DataPoint"]:
        series = series.sort_index()  # Ensure dates are sorted before conversion

        # Assert that the series is properly sorted
        index_list = list(series.index)
        for i in range(1, len(index_list)):
            assert index_list[i] >= index_list[i - 1], (
                f"Series not sorted at index {i}: {index_list[i - 1]} -> {index_list[i]}"
            )

        result = [
            DataPoint(date=str(date), value=float(value))
            for date, value in series.items()
        ]

        # Assert that the resulting DataPoints are sorted by date string
        for i in range(1, len(result)):
            assert result[i].date >= result[i - 1].date, (
                f"DataPoint not sorted at index {i}: {result[i - 1].date} -> {result[i].date}"
            )

        return result

    @staticmethod
    def series_from_list_datapoints(list: list["DataPoint"]) -> pd.Series:
        return pd.Series(
            [data_point.value for data_point in list],
            index=[data_point.date for data_point in list],
        )