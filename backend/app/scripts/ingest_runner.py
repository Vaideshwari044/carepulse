import asyncio
import os
import sys

from app.database import get_session_factory
from app.services.dataset_ingestion import ingest_dataset_pipeline

async def main():
    factory = get_session_factory()
    async with factory() as db:
        target_path = "/app/data/dataset/patient_data.csv"
        if not os.path.exists(target_path):
            print(f"Dataset file not found at {target_path}!")
            sys.exit(1)


        print(f"Ingesting dataset from: {target_path}")
        dataset, ds_import, analysis = await ingest_dataset_pipeline(
            dataset_name="Clinical Vitals Dataset 60k",
            file_path=target_path,
            db=db,
        )
        print("Dataset ingestion successful!")
        print(f"Dataset ID: {dataset.id}")
        print(f"Total Rows: {analysis['total_rows']}")
        print(f"Valid Rows: {analysis['valid_rows']}")
        print(f"Quality Indicator: {analysis['quality_indicator']}")

if __name__ == "__main__":
    asyncio.run(main())
