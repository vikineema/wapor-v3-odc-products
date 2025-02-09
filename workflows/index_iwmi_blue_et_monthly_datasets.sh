#!/bin/bash

# Directory containing metadata files
METADATA_DIR="./data/Incremental_ET_M"

if [[ ! -d "$METADATA_DIR" ]]; then
    echo "Directory $METADATA_DIR does not exist. Exiting."
    exit 1
fi

# Loop over each file in the metadata directory
shopt -s nullglob  # Avoids executing loop if no matches
for metadata_file in "$METADATA_DIR"/*.stac-item.json; do
  # Check if the file is a regular file
  if [[ -f "$metadata_file" ]]; then
    echo "Adding product from metadata file: $metadata_file"
    # Run the datacube product add command
    datacube dataset add "$metadata_file"
  else
    echo "Skipping non-regular file: $metadata_file"
  fi
done