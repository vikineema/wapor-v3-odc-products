import json
import logging
import os
from pathlib import Path

import click
from eodatasets3.serialise import to_path
from eodatasets3.stac import to_stac_item
from odc.aws import s3_dump

from iwmi_odr_odc_product_py import (
    prepare_iwmi_blue_et_monthly_metadata,
    prepare_iwmi_green_et_monthly_metadata,
)
from iwmi_odr_odc_product_py.common import get_logger
from iwmi_odr_odc_product_py.io import find_geotiff_files, is_s3_path

logger = get_logger(Path(__file__).stem, level=logging.INFO)


@click.command()
@click.option(
    "--product-name",
    help="Name of the product to generate the stac item files for",
)
@click.option(
    "--product-yaml",
    type=click.Path(),
    help="File path to the product definition yaml file",
)
@click.option("--geotiffs-dir", help="Directory containing the COG files")
@click.option(
    "--stac-output-dir",
    type=click.Path(),
    help="Directory to write the stac files docs to",
)
@click.option(
    "--metadata-output-dir",
    type=click.Path(),
    default=None,
    help="Directory to write the metadata docs to",
)
def create_stac_files(
    product_name: str,
    product_yaml,
    geotiffs_dir,
    stac_output_dir,
    metadata_output_dir,
):

    valid_product_names = ["iwmi_blue_et_monthly", "iwmi_green_et_monthly"]
    if product_name not in valid_product_names:
        raise NotImplementedError(
            f"Stac file generation has not been implemented for {product_name}"
        )
    if isinstance(metadata_output_dir, str):
        if is_s3_path(metadata_output_dir):
            raise RuntimeError("Metadata files require to be written to a local directory")
        else:
            metadata_output_dir = Path(metadata_output_dir).resolve()

    if isinstance(product_yaml, str):
        if not is_s3_path(product_yaml):
            product_yaml = Path(product_yaml).resolve()

    if isinstance(geotiffs_dir, str):
        if not is_s3_path(geotiffs_dir):
            geotiffs_dir = Path(geotiffs_dir).resolve()

    if isinstance(stac_output_dir, str):
        if not is_s3_path(stac_output_dir):
            stac_output_dir = Path(stac_output_dir).resolve()

    logger.info(f"Generating stac files for the product {product_name}")

    # Find all the geotiffs files in the directory
    geotiffs = find_geotiff_files(str(geotiffs_dir))
    print(f"Found {len(geotiffs)} geotiffs in {str(geotiffs_dir)}")

    for idx, geotiff in enumerate(geotiffs):
        logger.info(f"Generating stac file for {geotiff} {idx+1}/{len(geotiffs)}")

        # File system Path() to the dataset or S3 URL prefix (s3://bucket/key) to the dataset
        if not is_s3_path(geotiff):
            dataset_path = Path(geotiff)
        else:
            dataset_path = geotiff

        tile_id = os.path.basename(dataset_path).removesuffix(".tif")

        if metadata_output_dir is not None:
            metadata_output_path = Path(
                os.path.join(metadata_output_dir, f"{tile_id}.odc-metadata.yaml")
            )
            output_path = metadata_output_path
        else:
            metadata_output_path = None
            output_path = Path(os.path.join("/tmp", f"{tile_id}.odc-metadata.yaml"))

        if product_name == "iwmi_blue_et_monthly":
            dataset_doc = prepare_iwmi_blue_et_monthly_metadata.prepare_dataset(
                dataset_path=dataset_path, product_yaml=product_yaml, output_path=output_path
            )
        elif product_name == "iwmi_green_et_monthly":
            dataset_doc = prepare_iwmi_green_et_monthly_metadata.prepare_dataset(
                dataset_path=dataset_path, product_yaml=product_yaml, output_path=output_path
            )

        # Write the dataset doc to file
        if metadata_output_path is not None:
            to_path(metadata_output_path, dataset_doc)
            logger.info(f"Wrote dataset to {metadata_output_path}")

        stac_item_destination_url = os.path.join(stac_output_dir, f"{tile_id}.stac-item.json")

        stac_item = to_stac_item(
            dataset=dataset_doc, stac_item_destination_url=str(stac_item_destination_url)
        )

        if is_s3_path(stac_item_destination_url):
            s3_dump(
                data=json.dumps(stac_item, indent=2),
                url=stac_item_destination_url,
                ACL="bucket-owner-full-control",
                ContentType="application/json",
            )
        else:
            with open(stac_item_destination_url, "w") as file:
                json.dump(stac_item, file, indent=2)  # `indent=4` makes it human-readable

        logger.info(f"STAC written to {stac_item_destination_url}")

        print("manual break")
        break


if __name__ == "__main__":
    create_stac_files()
