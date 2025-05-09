import os
import argparse
import logging
from dotenv import load_dotenv
from medium_clone_suggestion.article_processor.pipeline import SupabaseArticleProcessor
from medium_clone_suggestion.logger import get_logger

logger = get_logger(__name__)

def main():
    """Command-line interface for the article processor."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Process articles from Supabase and extract keywords")
    parser.add_argument("--table", default="posts", help="Supabase table name")
    parser.add_argument("--content-col", default="content", help="Column containing article content")
    parser.add_argument("--id-col", default="postid", help="Optional Id name from your supabase table `default is postid`")
    parser.add_argument("--keyword-col", default="keyword", help="Column to store keywords in")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of articles to process")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--filter-col", help="Optional column to filter on")
    parser.add_argument("--filter-val", help="Optional value to filter by")
    args = parser.parse_args()
    
    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY in .env file.")
        return 1
    
    # Initialize processor
    processor = SupabaseArticleProcessor(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        use_resource_management=True
    )
    print("Possible args ",args)
    # Fetch articles
    articles = processor.fetch_articles_from_supabase(
        table_name=args.table,
        id_column=args.id_col,
        content_column=args.content_col,
        filter_column=args.filter_col,
        filter_value=args.filter_val,
        limit=args.limit
    )
    
    if not articles:
        logger.info("No articles to process.")
        return 0
    
    # Process articles
    processed_articles = processor.process_batch(articles, max_workers=args.workers)
    
    # Update Supabase
    processor.update_supabase_keywords(
        processed_articles,
        table_name=args.table,
        keyword_column=args.keyword_col
    )
    
    logger.info(f"Successfully processed {len(processed_articles)} articles.")
    return 0

if __name__ == "__main__":
    exit(main())
