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
	docker compose exec -T jupyter datacube product add ./workspace/products/wapor_soil_moisture.odc-product.yaml

get-storage-parameters-wapor_soil_moisture:
	get-storage-parameters \
	--product-name="wapor_soil_moisture" \
	--output-dir="data/wapor_soil_moisture/" 

create-stac-wapor_soil_moisture:
	create-stac-files \
	 --product-name="wapor_soil_moisture" \
	 --product-yaml="products/wapor_soil_moisture.odc-product.yaml" \
	 --metadata-output-dir="data/wapor_soil_moisture/" \
	 --stac-output-dir="data/wapor_soil_moisture/" 

up: ## Bring up your Docker environment
	docker compose up -d postgres
	docker compose run checkdb
	docker compose up -d jupyter
	# make fix-file-permissions
	docker compose up -d explorer
	make init

down:
	docker compose down --remove-orphans

logs:
	docker compose logs

shell:
	docker compose exec jupyter bash -c "cd /home/jovyan/workspace && exec bash"