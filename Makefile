#!make
SHELL := /usr/bin/env bash

build:
	docker compose build

fix-file-permissions:
	docker compose exec -it jupyter sudo chown -R 1000:100 /home/jovyan/workspace

setup-explorer:
	# Initialise and create product summaries
	docker compose exec -T explorer cubedash-gen --init --all
	docker compose exec -T explorer cubedash-run --port 8081

get-jupyter-token:
	docker compose exec -T jupyter jupyter notebook list

init: ## Prepare the database
	docker compose exec -T jupyter datacube -v system init

add-products:
	docker compose exec -T jupyter datacube product add ./workspace/products/iwmi_blue_et_monthly.odc-product.yaml
	docker compose exec -T jupyter datacube product add ./workspace/products/iwmi_green_et_monthly.odc-product.yaml

get-storage-parameters-iwmi_blue_et_monthly:
	get-storage-parameters \
	--product-name="iwmi_blue_et_monthly" \
	--geotiffs-dir=s3://iwmi-datasets/Water_accounting_plus/Africa/Incremental_ET_M/ \
	--output-dir="data/Incremental_ET_M/" 

get-storage-parameters-iwmi_green_et_monthly:
	get-storage-parameters \
	--product-name="iwmi_green_et_monthly" \
	--geotiffs-dir=s3://iwmi-datasets/Water_accounting_plus/Africa/Rainfall_ET_M/ \
	--output-dir="data/Rainfall_ET_M/" 

create-stac-iwmi_blue_et_monthly:
	create-stac-files \
	 --product-name="iwmi_blue_et_monthly" \
	 --product-yaml="products/iwmi_blue_et_monthly.odc-product.yaml" \
	 --metadata-output-dir="data/Incremental_ET_M/" \
	 --stac-output-dir="data/Incremental_ET_M/" \
	 --geotiffs-dir=s3://iwmi-datasets/Water_accounting_plus/Africa/Incremental_ET_M/

create-stac-iwmi_green_et_monthly:
	create-stac-files \
	 --product-name="iwmi_green_et_monthly" \
	 --product-yaml="products/iwmi_green_et_monthly.odc-product.yaml" \
	 --metadata-output-dir="data/Rainfall_ET_M/" \
	 --stac-output-dir="data/Rainfall_ET_M/" \
	 --geotiffs-dir=s3://iwmi-datasets/Water_accounting_plus/Africa/Incremental_ET_M/

download-iwmi-odr-data:
	aws s3 cp --recursive  --no-sign-request s3://iwmi-datasets/Water_accounting_plus/Africa/ data/

up: ## Bring up your Docker environment
	docker compose up -d postgres
	docker composdae run checkdb
	docker compose up -d jupyter
	make fix-file-permissions
	docker compose up -d explorer

down:
	docker compose down --remove-orphans

logs:
	docker compose logs