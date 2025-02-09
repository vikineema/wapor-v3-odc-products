import json
import logging
import os
from pathlib import Path

import click
from eodatasets3.serialise import to_path
from eodatasets3.stac import to_stac_item
from odc.aws import s3_dump

from wapor_v3_odc_products_py import prepare_wapor_soil_moisture_metadata
from wapor_v3_odc_products_py.io import is_s3_path, is_url, is_gcsfs_path
from wapor_v3_odc_products_py.logs import get_logger
from wapor_v3_odc_products_py.utils import get_mapset_rasters

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
    stac_output_dir,
    metadata_output_dir,
):

    valid_product_names = ["wapor_soil_moisture"]
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

    if isinstance(stac_output_dir, str):
        if not is_s3_path(stac_output_dir):
            stac_output_dir = Path(stac_output_dir).resolve()

    logger.info(f"Generating stac files for the product {product_name}")

    if product_name == "wapor_soil_moisture":
        mapset_code = "L2-RSM-D"

    geotiffs = get_mapset_rasters(mapset_code)
    # Use a gsutil URI instead of the the public URL
    geotiffs = [i.replace("https://storage.googleapis.com/", "gs://") for i in geotiffs]

    for idx, geotiff in enumerate(geotiffs):
        logger.info(f"Generating stac file for {geotiff} {idx+1}/{len(geotiffs)}")

        # File system Path() to the dataset
        # or gsutil URI prefix  (gs://bucket/key) to the dataset.
        if not is_s3_path(geotiff) and not is_gcsfs_path(geotiff):
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

        if product_name == "wapor_soil_moisture":
            dataset_doc = prepare_wapor_soil_moisture_metadata.prepare_dataset(
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
