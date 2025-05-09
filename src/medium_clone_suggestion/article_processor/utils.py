from bs4 import BeautifulSoup
import nltk, re
from nltk import pos_tag, word_tokenize, ne_chunk
from nltk.corpus import stopwords, wordnet
from gensim import corpora
from gensim.models import LdaModel
from typing import Dict, List
from gensim.utils import simple_preprocess

from medium_clone_suggestion.logger import get_logger

logger = get_logger(__name__)
nltk.download('stopwords', quiet=True)
STOPWORDS = set(stopwords.words('english'))
lda_model = LdaModel.load("src/medium_clone_suggestion/article_processor/models/trained_lda.model")
dictionary = corpora.Dictionary.load("src/medium_clone_suggestion/article_processor/models/lda_dictionary.dict")


"""
""Cleaning the HTML 
"""
def clean_article(article: Dict) -> Dict:
    text = BeautifulSoup(article['content'], 'html.parser').get_text()
    
    # If 'is_gibberish' is missing, initialize it to False
    if 'is_gibberish' not in article:
        article['is_gibberish'] = False
    
    if is_gibberish(text):
        article["is_gibberish"] = True
    else:
        article['content'] = text
    
    return article

def is_gibberish(text: str,
                 stopword_threshold: float = 0.2,
                 long_word_threshold: int = 15) -> bool:
    tokens = re.findall(r"[A-Za-z']+", text.lower())
    if not tokens:
        return True

    stopword_count = sum(t in STOPWORDS for t in tokens)
    stopword_ratio = stopword_count / len(tokens)

    long_words = sum(len(t) > long_word_threshold for t in tokens)
    long_word_ratio = long_words / len(tokens)

    # too few stopwords OR too many ridiculously long words => gibberish
    return (stopword_ratio < stopword_threshold) or (long_word_ratio > 0.3)

def add_entities(article: Dict) -> Dict:
    tokens = word_tokenize(article['content'])
    tagged = pos_tag(tokens)
    entities = ne_chunk(tagged)
    
    # Entity processing logic from extract_categorized_entities
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
    
    article['entities'] = {k: list(set(v)) for k, v in categories.items() if v}
    return article

def add_topics(article: Dict) -> Dict:
    # LDA topic modeling implementation from add_topic_modeling
    try:
        stop_words = set(stopwords.words('english'))
        tokens = [word for word in simple_preprocess(article['content'].lower()) if word not in stop_words]
        dictionary = dictionary
        corpus = [dictionary.doc2bow(tokens)]
        lda_model = lda_model
        topics = []
        for topic_id, words in lda_model.print_topics():
            words_list = [word.split('*')[1].strip().replace('"', '') for word in words.split('+')]
            topics.append(words_list[0])
        article['topics'] = topics
    except Exception as e:
        logger.warning(f"Topic modeling failed: {e}")
        article['topics'] = []
    
    return article