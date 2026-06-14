from backend.inventory.inventory_ingestion import (
    process_inventory_upload,
    initialize_inventory_datasets
)

# Proactively run legacy dataset migration on package startup
initialize_inventory_datasets()

__all__ = ["process_inventory_upload", "initialize_inventory_datasets"]
