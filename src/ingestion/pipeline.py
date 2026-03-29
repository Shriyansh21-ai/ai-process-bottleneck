from src.ingestion.loader import load_raw_data
from src.ingestion.validator import validate_schema, validate_timestamps
from src.ingestion.transformer import enrich_data
from src.utils.logger import get_logger

logger = get_logger("INGESTION_PIPELINE")

def run_pipeline(data_path, schema_path):
    logger.info("Starting ingestion pipeline")

    df = load_raw_data(data_path)
    logger.info("Raw data loaded")

    validate_schema(df, schema_path)
    logger.info("Schema validation passed")

    df = validate_timestamps(df)
    logger.info("Timestamp validation passed")

    df = enrich_data(df)
    logger.info("Data enrichment completed")

    logger.info("Ingestion pipeline completed successfully")
    return df
