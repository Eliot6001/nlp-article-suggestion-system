import logging
import os
from dotenv import load_dotenv

from medium_clone_suggestion.article_processor.pipeline import ProcessingPipeline

from medium_clone_suggestion.logger import get_logger

logger = get_logger(__name__)

def main():
    load_dotenv()
    pipeline = ProcessingPipeline()
    results = pipeline.run()
    logger.info(f"Processing complete: {results}")

if __name__ == "__main__":
    main()