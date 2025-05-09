import os
import time
import logging
import psutil
import nltk
from nltk import pos_tag, word_tokenize, ne_chunk
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor,  as_completed
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from transformers import BartForConditionalGeneration, BartTokenizer
from supabase import create_client, Client
from gensim import corpora
from gensim.models import LdaModel
from gensim.utils import simple_preprocess
from nltk.corpus import stopwords
from nltk.corpus import wordnet as wn

####
###
##
## This is a mockup phase of my code creation, not the be used for reference
## Kept here for "Pre-building phase" to compare. 
## Do not Use any code from here if you want it to function.
#####




# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Download necessary NLTK data
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('maxent_ne_chunker', quiet=True)
nltk.download('words', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet')

class SupabaseArticleProcessor:
    """
    Article processing pipeline that fetches data from Supabase,
    processes articles, and stores keywords back to Supabase.
    
    Contains both testing (mockup) and production (Supabase) parts.
    """
    # Constants
    MAX_WORD_COUNT = 384  # Max words before summarization is triggered
    DEFAULT_SUMMARY_LENGTH = 150  # Target summary length

    def __init__(self, 
                 supabase_url: str,
                 supabase_key: str,
                 use_resource_management: bool = True,
                 summary_model_name: str = "facebook/bart-large-cnn",
                 heavy_model_name: str = "all-mpnet-base-v2",
                 light_model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize pipeline components and Supabase client.
        """
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.use_resource_management = use_resource_management
        self.summary_model_name = summary_model_name
        self.heavy_model_name = heavy_model_name
        self.light_model_name = light_model_name

        # Lazy-loaded models
        self._summary_model = None
        self._summary_tokenizer = None
        self._heavy_model = None
        self._light_model = None
        self._keybert_model = None

        logger.info("Supabase article processor initialized successfully")

    # Utility Functions
    def _get_available_memory_mb(self) -> float:
        """Return available memory in MB."""
        return psutil.virtual_memory().available / (1024 * 1024)

    def _wait_for_memory(self, threshold_percent: int = 99, check_interval: int = 5):
        """Wait until RAM usage is below threshold."""
        while psutil.virtual_memory().percent >= threshold_percent:
            logger.warning(f"⚠️  High RAM usage detected ({psutil.virtual_memory().percent}%+). Waiting...")
            time.sleep(check_interval)

    def count_words(self, text: str) -> int:
        """Count words in the given text."""
        return len(nltk.word_tokenize(text))

    def strip_html(self, html_text: str) -> str:
        """Strip HTML tags from text."""
        soup = BeautifulSoup(html_text, 'html.parser')
        return soup.get_text()

    # Lazy-Loaded Properties
    @property
    def summary_model(self):
        """Lazy-load the summarization model and tokenizer."""
        if self._summary_model is None:
            if self.use_resource_management:
                self._wait_for_memory()
                available_memory = self._get_available_memory_mb()
                if available_memory < 1000:  # Less than 1GB
                    logger.info("⚡ Low RAM detected! Using DistilBART for summarization.")
                    self._summary_model = BartForConditionalGeneration.from_pretrained("sshleifer/distilbart-cnn-12-6")
                    self._summary_tokenizer = BartTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
                else:
                    logger.info("🎯 Sufficient RAM. Using BART for summarization.")
                    self._summary_model = BartForConditionalGeneration.from_pretrained(self.summary_model_name)
                    self._summary_tokenizer = BartTokenizer.from_pretrained(self.summary_model_name)
            else:
                self._summary_model = BartForConditionalGeneration.from_pretrained(self.summary_model_name)
                self._summary_tokenizer = BartTokenizer.from_pretrained(self.summary_model_name)
        return self._summary_model, self._summary_tokenizer

    @property
    def keyword_model(self):
        """Return the keyword extraction model based on available memory."""
        if self.use_resource_management:
            self._wait_for_memory()
            available_memory = self._get_available_memory_mb()
            if available_memory < 1000:
                if self._light_model is None:
                    logger.info("⚡ Low RAM detected! Using MiniLM for keyword extraction.")
                    self._light_model = SentenceTransformer(self.light_model_name)
                return self._light_model
            else:
                if self._heavy_model is None:
                    logger.info("🎯 Sufficient RAM. Using MPNet for keyword extraction.")
                    self._heavy_model = SentenceTransformer(self.heavy_model_name)
                return self._heavy_model
        else:
            if self._heavy_model is None:
                self._heavy_model = SentenceTransformer(self.heavy_model_name)
            return self._heavy_model

    @property
    def keybert_extractor(self):
        """Lazy-load the KeyBERT model."""
        if self._keybert_model is None:
            self._keybert_model = KeyBERT(model=self.keyword_model)
        return self._keybert_model

    # Supabase and Mockup Data Fetching
    def fetch_articles_from_supabase(self, table_name: str = "posts", 
                                     id_column: str = "postid",
                                     content_column: str = "content",
                                     filter_column: str = None,
                                     filter_value: str = None,
                                     limit: int = 100) -> List[Dict]:
        """
        Fetch articles either from Supabase or mockup file (for testing).
        """
        # Production (Supabase) query is commented for testing:
        """
        query = self.supabase.table(table_name).select(f"{id_column}, title, {content_column}")
        if filter_column and filter_value is not None:
            query = query.eq(filter_column, filter_value)
        response = query.limit(limit).execute()
        articles = []
        for item in response.data:
            item['content'] = item.pop(content_column, '')
            item['id'] = item.pop(id_column, None)
            articles.append(item)
        logger.info(f"Fetched {len(articles)} articles from Supabase table '{table_name}'")
        """
        # Testing: load from mockup.txt
        articles = []
        with open('mockup.txt', 'r', encoding='utf-8') as f:
            current_article = {}
            for line in f:
                line = line.strip()
                if line.startswith('ID: '):
                    if current_article:
                        articles.append(current_article)
                    current_article = {'id': line[4:]}
                elif line.startswith('Title: '):
                    current_article['title'] = line[7:]
                elif line.startswith('Content: '):
                    current_article['content'] = line[9:]
            if current_article:
                articles.append(current_article)
        logger.info(f"Loaded {len(articles)} articles from mockup.txt")
        return articles

    # Text Processing Functions
    def summarize_text(self, text: str, max_length: int = DEFAULT_SUMMARY_LENGTH) -> str:
        """
        Summarize text using the loaded BART/DistilBART model.
        """
        model, tokenizer = self.summary_model
        inputs = tokenizer.encode("summarize: " + text,
                                  return_tensors="pt",
                                  max_length=1024,
                                  truncation=True)
        summary_ids = model.generate(inputs,
                                     max_length=max_length,
                                     min_length=40,
                                     length_penalty=2.0,
                                     num_beams=4,
                                     early_stopping=True)
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        logger.info(f"Summarized text from {self.count_words(text)} to {self.count_words(summary)} words")
        return summary

    def extract_keywords(self, text: str, top_n: int = 5, keyphrase_ngram_range: tuple = (1, 1),
                         use_mmr: bool = False, diversity: float = 0.7, candidates: List[str] = None) -> List[Tuple[str, float]]:
        """
        Extract keywords using KeyBERT.
        """
        keywords = self.keybert_extractor.extract_keywords(
            text,
            top_n=top_n,
            keyphrase_ngram_range=keyphrase_ngram_range,
            use_mmr=use_mmr,
            diversity=diversity,
            candidates=candidates
        )
        logger.info(f"Extracted {len(keywords)} keywords: {keywords}")
        return keywords

    def classify_keywords_hierarchically(self, keywords: List[str]) -> Dict[str, List[str]]:
        """
        Organize keywords into predefined hierarchical categories.
        """
        try:
           

            categories = {
                'technology': [],
                'business': [],
                'politics': [],
                'science': [],
                'health': [],
                'entertainment': [],
                'sports': [],
                'other': []
            }
            category_keywords = {
                'technology': ['tech', 'software', 'hardware', 'app', 'digital', 'computer', 'internet', 'cyber', 'programming', 'ai', 'data'],
                'business': ['company', 'market', 'finance', 'economy', 'stock', 'investor', 'startup', 'entrepreneur', 'trade', 'corporate'],
                'politics': ['government', 'policy', 'election', 'president', 'congress', 'democrat', 'republican', 'senate', 'vote', 'law'],
                'science': ['research', 'study', 'discovery', 'physics', 'chemistry', 'biology', 'scientist', 'experiment', 'theory'],
                'health': ['medical', 'doctor', 'hospital', 'disease', 'treatment', 'patient', 'medicine', 'health', 'therapy', 'wellness'],
                'entertainment': ['movie', 'music', 'actor', 'celebrity', 'film', 'show', 'tv', 'game', 'award', 'media'],
                'sports': ['player', 'team', 'game', 'championship', 'tournament', 'league', 'score', 'match', 'coach', 'athlete']
            }

            for keyword in keywords:
                keyword_lower = keyword.lower()
                assigned = False
                for category, indicators in category_keywords.items():
                    if any(indicator in keyword_lower for indicator in indicators):
                        categories[category].append(keyword)
                        assigned = True
                        break

                if not assigned:
                    try:
                        synsets = wn.synsets(keyword_lower)
                        if synsets:
                            hypernyms = []
                            for synset in synsets[:2]:
                                hypernyms.extend(synset.hypernyms())
                            for hypernym in hypernyms:
                                hypernym_name = hypernym.name().split('.')[0]
                                for category, indicators in category_keywords.items():
                                    if any(indicator in hypernym_name for indicator in indicators):
                                        categories[category].append(keyword)
                                        assigned = True
                                        break
                                if assigned:
                                    break
                    except Exception as e:
                        logger.warning(f"WordNet error: {e}")

                if not assigned:
                    categories['other'].append(keyword)

            return {k: v for k, v in categories.items() if v}
        except Exception as e:
            logger.warning(f"Hierarchical classification failed: {e}")
            return {'other': keywords}

    def format_keywords_for_storage(self, keywords: List[Tuple[str, float]]) -> List[str]:
        """Format keywords for storage by removing scores."""
        return [keyword for keyword, _ in keywords]

    def extract_categorized_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract and categorize named entities from text using NLTK.
        """
        try:
            tokens = word_tokenize(text)
            tagged = pos_tag(tokens)
            entities = ne_chunk(tagged)
            categories = {
                'PERSON': [],
                'ORGANIZATION': [],
                'LOCATION': [],
                'GPE': [],
                'FACILITY': [],
                'PRODUCT': [],
                'EVENT': [],
                'OTHER': []
            }
            for chunk in entities:
                if hasattr(chunk, 'label'):
                    entity_text = ' '.join(c[0] for c in chunk)
                    entity_type = chunk.label()
                    if entity_type in categories:
                        categories[entity_type].append(entity_text)
                    else:
                        categories['OTHER'].append(entity_text)
            return {k: list(set(v)) for k, v in categories.items() if v}
        except Exception as e:
            logger.warning(f"Entity categorization failed: {e}")
            return {}

    def add_topic_modeling(self, text: str, num_topics: int = 3) -> List[str]:
        """
        Extract topics from text using LDA.
        """
        try:
            
            
            stop_words = set(stopwords.words('english'))
            tokens = [word for word in simple_preprocess(text.lower()) if word not in stop_words]
            dictionary = corpora.Dictionary([tokens])
            corpus = [dictionary.doc2bow(tokens)]
            lda_model = LdaModel(corpus=corpus, id2word=dictionary, num_topics=num_topics, passes=10)
            topics = []
            for topic_id, words in lda_model.print_topics():
                words_list = [word.split('*')[1].strip().replace('"', '') for word in words.split('+')]
                topics.append(words_list[0])
            return topics
        except Exception as e:
            logger.warning(f"Topic modeling failed: {e}")
            return []

    # Article Processing Functions
    def process_article(self, article: Dict) -> Dict:
        """
        Process a single article by cleaning its content, extracting keywords,
        summarizing (if necessary), performing topic modeling, and categorizing keywords.
        This function is the heart of the pipeline, so pay attention.

        Steps:
        1. Clean HTML tags.
        2. Count words.
        3. Extract named entities and prepare candidate keywords.
        4. Extract keywords from full content.
        5. If content is too long, summarize and extract keywords from the summary.
        6. Perform topic modeling to get additional keyword candidates.
        7. Extract keywords from the title (with a boost).
        8. Merge all keywords, boost those that are proper nouns, and select top keywords.
        9. Format and store the final results.
        """
        # Strip HTML tags from content
        article['content'] = self.strip_html(article['content'])
        result = article.copy()

        # Count words for further processing decisions
        word_count = self.count_words(article['content'])
        result['word_count'] = word_count

        # Extract named entities and flatten them into a list (for candidate keywords)
        entities = self.extract_categorized_entities(article['content'])
        proper_nouns = [entity for sublist in entities.values() for entity in sublist]

        # Extract keywords from the full content using KeyBERT.
        # Use proper_nouns as candidates if available; otherwise, use default behavior.
        keywords_full = self.extract_keywords(
            article['content'],
            top_n=8,
            keyphrase_ngram_range=(1, 3),
            use_mmr=True,
            diversity=0.6,
            candidates=proper_nouns if proper_nouns else None  # Use candidates only if list isn't empty
        )

        keywords_summary = []
        # If the content exceeds the max word count, generate a summary and extract keywords from it.
        if word_count > self.MAX_WORD_COUNT:
            summary = self.summarize_text(article['content'])
            result['summary'] = summary
            keywords_summary = self.extract_keywords(
                summary,
                top_n=6,
                keyphrase_ngram_range=(1, 2),
                use_mmr=True,
                diversity=0.5
            )
            # Boost summary keywords to give them extra weight
            keywords_summary = [(kw, score * 1.2) for kw, score in keywords_summary]

        # Perform topic modeling (LDA) to extract additional topics as keywords
        topics = self.add_topic_modeling(article['content'])
        topic_keywords = [(topic, 0.8) for topic in topics]

        # Combine all keyword sources
        all_keywords = keywords_full + keywords_summary + topic_keywords

        # Extract keywords from the title and boost their importance
        if article.get('title'):
            title_keywords = self.extract_keywords(
                article['title'],
                top_n=3,
                keyphrase_ngram_range=(1, 2)
            )
            title_keywords = [(kw, score * 1.5) for kw, score in title_keywords]
            all_keywords += title_keywords

        # Merge keywords, boosting the score for those that are proper nouns, and keeping the highest score
        keyword_dict = {}
        for kw, score in all_keywords:
            if kw in proper_nouns:
                score += 0.2  # Boost for proper noun presence
            if kw not in keyword_dict or score > keyword_dict[kw]:
                keyword_dict[kw] = score

        # Sort keywords by score in descending order and pick the top 8
        sorted_keywords = sorted(keyword_dict.items(), key=lambda x: x[1], reverse=True)
        top_keywords = sorted_keywords[:8]
        print(f"top keywords: f{top_keywords}")  # Debug print for top keywords

        # Format keywords for storage (strip scores)
        result['keywords'] = self.format_keywords_for_storage(top_keywords)
        # Store full keyword scores and hierarchical categorization
        result['keyword_scores'] = dict(top_keywords)
        result['categories'] = self.classify_keywords_hierarchically([kw for kw, _ in top_keywords])
        result['entities'] = entities


        return result


    
    def process_batch(self, articles: List[Dict], max_workers: int = 4) -> List[Dict]:
        """
        Process a batch of articles in parallel.
        """
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.process_article, article) for article in articles]
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.error(f"Error processing article: {e}")
        return results
    
    # Supabase Update Functions (Production)
    def update_supabase_keywords(self, processed_articles: List[Dict], 
                                 table_name: str = "posts",
                                 keyword_column: str = "keyword",
                                 id_column: str = "postid") -> None:
        """
        Update Supabase table with extracted keywords.
        (Currently a placeholder for production)
        """
        pass

    def mark_articles_as_processed(self, processed_articles: List[Dict],
                                   table_name: str = "posts",
                                   processed_column: str = "processed",
                                   id_column: str = "postid") -> None:
        """
        Mark articles as processed in Supabase.
        """
        successful_updates = 0
        failed_updates = 0
        for article in processed_articles:
            try:
                self.supabase.table(table_name).update({processed_column: True}).eq(id_column, article['id']).execute()
                successful_updates += 1
            except Exception as e:
                failed_updates += 1
                logger.error(f"Error marking article ID {article.get('id')} as processed: {e}")
        logger.info(f"Marked {successful_updates} articles as processed (Failed: {failed_updates})")

    def save_keywords(self, processed_articles: List[Dict]) -> None:
        file_path = os.path.abspath("result.txt")
        print("Saving results to:", file_path)
        with open('result.txt', 'w', encoding='utf-8') as f:
            for article in processed_articles:
                f.write(f"Article ID: {article['id']}\n")
                f.write(f"Title: {article.get('title', 'No title')}\n")
                f.write(f"Word count: {article['word_count']}\n")
                if 'summary' in article:
                    f.write(f"Summary: {article['summary']}\n")
                f.write("Keywords: " + ", ".join(article['keywords']) + "\n")
                f.write("Categories:\n")
                for category, words in article['categories'].items():
                    f.write(f"  {category}: {', '.join(words)}\n")
                f.write("Entities:\n")
                for entity_type, entities in article['entities'].items():
                    f.write(f"  {entity_type}: {', '.join(entities)}\n")
                f.write("\n" + "=" * 50 + "\n\n")
        logger.info(f"Saved results for {len(processed_articles)} articles to {file_path}")


    def run_pipeline(self, table_name: str = "posts",
                     content_column: str = "content",
                     keyword_column: str = "keyword",
                     processed_column: str = "processed",
                     filter_column: str = None,
                     filter_value: str = None,
                     limit: int = 100,
                     max_workers: int = 4) -> Dict:
        """
        Run the complete pipeline: fetching, processing, updating, and saving.
        """
        start_time = time.time()
        articles = self.fetch_articles_from_supabase(
            table_name=table_name,
            content_column=content_column,
            filter_column=filter_column,
            filter_value=filter_value,
            limit=limit
        )
        if not articles:
            logger.info("No articles to process.")
            return {"articles_fetched": 0, "articles_processed": 0, "articles_updated": 0, "elapsed_time": time.time() - start_time}
        
        processed_articles = self.process_batch(articles, max_workers=max_workers)
         #self.update_supabase_keywords(processed_articles, table_name=table_name, keyword_column=keyword_column)
        print("Saving result.txt to:", os.path.abspath("result.txt"))

        self.save_keywords(processed_articles)
        if processed_column:
            self.mark_articles_as_processed(processed_articles, table_name=table_name, processed_column=processed_column)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Pipeline completed in {elapsed_time:.2f} seconds")
        return {
            "articles_fetched": len(articles),
            "articles_processed": len(processed_articles),
            "articles_updated": len(processed_articles),
            "elapsed_time": elapsed_time
        }


def main():
    """Main function for running the pipeline."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        logger.error("Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY environment variables.")
        return

    processor = SupabaseArticleProcessor(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        use_resource_management=True
    )
    stats = processor.run_pipeline(
        table_name="posts",
        content_column="content",
        keyword_column="keyword",
        processed_column="processed",
        filter_column="processed",
        filter_value=False,
        limit=50
    )
    logger.info(f"Pipeline summary: {stats}")


if __name__ == "__main__":
    main()
