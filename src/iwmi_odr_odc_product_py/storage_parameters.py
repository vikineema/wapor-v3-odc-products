import json
import logging
import os
from pathlib import Path

import click
import rasterio
from tqdm import tqdm

from iwmi_odr_odc_product_py.common import get_logger
from iwmi_odr_odc_product_py.io import (
    check_directory_exists,
    find_geotiff_files,
    get_filesystem,
)

logger = get_logger(Path(__file__).stem, level=logging.INFO)


@click.command()
@click.option(
    "--product-name",
    help="Name of the product to get the storage parameters for",
)
@click.option(
    "--geotiffs-dir", help="Directory containing the COG files to check the CRS and resolution"
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default=None,
    help="Directory to write the unique storage parameters text file to",
)
def get_storage_parameters(
    product_name: str,
    geotiffs_dir: str,
    output_dir: str,
):
    geotiffs_file_paths = find_geotiff_files(directory_path=geotiffs_dir)

    storage_parameters_list = []

    for file_path in tqdm(iterable=geotiffs_file_paths, total=len(geotiffs_file_paths)):
        with rasterio.open(file_path) as src:
            crs = src.crs  # Coordinate Reference System
            res_x, res_y = src.res  # Pixel resolution (x, y)
        item = {"crs": f"EPSG:{crs.to_epsg()}", "res_x": res_x, "res_y": res_y}
        storage_parameters_list.append(item)

    # Convert dicts to JSON strings to create a unique set
    unique_storage_parameters = [
        json.loads(s) for s in {json.dumps(d, sort_keys=True) for d in storage_parameters_list}
    ]
    storage_parameters_json_array = json.dumps(unique_storage_parameters)

    output_file = os.path.join(output_dir, f"{product_name}_storage_parameters")

    fs = get_filesystem(path=output_dir, anon=False)
    if not check_directory_exists(path=output_dir):
        fs.mkdirs(path=output_dir, exist_ok=True)
        logger.info(f"Created directory {output_dir}")

    with fs.open(output_file, "w") as file:
        file.write(storage_parameters_json_array)
    logger.info(f"Tasks chunks written to {output_file}")


if __name__ == "__main__":
    get_storage_parameters()
