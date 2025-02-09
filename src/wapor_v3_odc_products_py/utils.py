import calendar
import collections
import logging
import os
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta

from wapor_v3_odc_products_py.logs import get_logger
from wapor_v3_odc_products_py.io import is_gcsfs_path, is_url

logger = get_logger(Path(__file__).stem, level=logging.INFO)

BASE_URL = "https://data.apps.fao.org/gismgr/api/v2/catalog/workspaces/WAPOR-3/mapsets"


def get_WaPORv3_info(url: str) -> pd.DataFrame:
    """
    Get information on WaPOR v3 data. WaPOR v3 variables are stored in `mapsets`,
    which in turn contain `rasters` that contain the data for a particular date or period.

    Parameters
    ----------
    url : str
        URL to get information from
    Returns
    -------
    pd.DataFrame
        A table of the mapset attributes found.
    """
    data = {"links": [{"rel": "next", "href": url}]}

    output_dict = collections.defaultdict(list)
    while "next" in [x["rel"] for x in data["links"]]:
        url_ = [x["href"] for x in data["links"] if x["rel"] == "next"][0]
        response = requests.get(url_)
        response.raise_for_status()
        data = response.json()["response"]
        for item in data["items"]:
            for key in list(item.keys()):
                if key == "links":
                    output_dict[key].append(item[key][0]["href"])
                else:
                    output_dict[key].append(item[key])

    output_df = pd.DataFrame(output_dict)

    if "code" in output_df.columns:
        output_df.sort_values("code", inplace=True)
        output_df.reset_index(drop=True, inplace=True)
    return output_df


def get_mapset_rasters(wapor_v3_mapset_code: str) -> list[str]:
    wapor_v3_mapset_url = os.path.join(BASE_URL, wapor_v3_mapset_code, "rasters")
    wapor_v3_mapset_rasters = get_WaPORv3_info(wapor_v3_mapset_url)["downloadUrl"].to_list()
    logger.info(
        f"Found {len(wapor_v3_mapset_rasters)} rasters for the mapset {wapor_v3_mapset_code}"
    )
    return wapor_v3_mapset_rasters


def get_dekad(year: str | int, month: str | int, dekad_label: str) -> tuple:
    """
    Get the end date of the dekad that a date belongs to and the time range
    for the dekad.
    Every month has three dekads, such that the first two dekads
    have 10 days (i.e., 1-10, 11-20), and the third is comprised of the
    remaining days of the month.

    Parameters
    ----------
    year: int | str
        Year of the dekad
    month: int | str
        Month of the dekad
    dekad_label: str
        Label indicating whether the date falls in the 1st, 2nd or 3rd dekad
        in a month

    Returns
    -------
    tuple
        The end date of the dekad and the time range for the dekad.
    """
    if isinstance(year, str):
        year = int(year)

    if isinstance(month, str):
        month = int(month)

    first_day = datetime(year, month, 1)
    last_day = datetime(year, month, calendar.monthrange(year, month)[1])

    d1_start_date, d2_start_date, d3_start_date = pd.date_range(
        start=first_day, end=last_day, freq="10D", inclusive="left"
    )
    if dekad_label == "D1":
        input_datetime = (d2_start_date - relativedelta(days=1)).to_pydatetime()
        start_datetime = d1_start_date.to_pydatetime()
        end_datetime = input_datetime.replace(hour=23, minute=59, second=59)
    elif dekad_label == "D2":
        input_datetime = (d3_start_date - relativedelta(days=1)).to_pydatetime()
        start_datetime = d2_start_date.to_pydatetime()
        end_datetime = input_datetime.replace(hour=23, minute=59, second=59)
    elif dekad_label == "D3":
        input_datetime = last_day
        start_datetime = d3_start_date.to_pydatetime()
        end_datetime = input_datetime.replace(hour=23, minute=59, second=59)

    return input_datetime, (start_datetime, end_datetime)


def get_last_modified(file_path: str):
    """Returns the Last-Modified timestamp 
    of a given URL if available."""
    if is_gcsfs_path(file_path):
        url = file_path.replace("gs://", "https://storage.googleapis.com/")
    else:
        url = file_path
    response = requests.head(url, allow_redirects=True)
    last_modified = response.headers.get("Last-Modified")
    if last_modified:
        return parsedate_to_datetime(last_modified)
    else:
        return None
