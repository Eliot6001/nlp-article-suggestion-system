import torch

from transformers import BartForConditionalGeneration, BartTokenizer
from sentence_transformers import SentenceTransformer, util
from keybert import KeyBERT
import psutil

from typing import Tuple
from medium_clone_suggestion.logger import get_logger

logger = get_logger(__name__)

class ModelManager:
    def __init__(self, use_cuda: bool = True):
        self.use_cuda = use_cuda and torch.cuda.is_available()
        self.device = "cuda" if self.use_cuda else "cpu"
        self._models = {}

    def get_model(self, model_name: str, model_class, **kwargs):
        if model_name not in self._models:
            self._check_memory()
            if model_class == SentenceTransformer:
                model = model_class(model_name, **kwargs)
            else:
                model = model_class.from_pretrained(model_name, **kwargs)
            self._models[model_name] = model.to(self.device)
        return self._models[model_name]

    def _check_memory(self):
        if self.use_cuda:
            free_mem = torch.cuda.mem_get_info()[0] / (1024**3)
            if free_mem < 0.5:  # 0.5GB threshold
                raise RuntimeError(f"Insufficient GPU memory: {free_mem:.1f}GB free")
        else:
            ram = psutil.virtual_memory()
            if ram.available < 0.5 * 1024**3:  # 0.5GB threshold
                raise RuntimeError(f"Insufficient RAM: {ram.available/(1024**3):.1f}GB free")

class SummarizationModel:
    def __init__(self, model_manager: ModelManager):
        # initialize model using the manager.
        self.model = model_manager.get_model(
            "facebook/bart-large-cnn", #you can swap it w/another model here
            BartForConditionalGeneration
        )
        self.tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
        
    def summarize(self, article_text: str) -> str:
        inputs = self.tokenizer.encode(article_text, return_tensors="pt", max_length=1024, truncation=True)
        summary_ids = self.model.generate(inputs, num_beams=4, min_length=50, max_length=200, early_stopping=True)
        summary = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        return summary

class KeywordModel:
    def __init__(self, model_manager: ModelManager):
        self.encoder = model_manager.get_model(
            "all-mpnet-base-v2",
            SentenceTransformer
        )
        self.keybert = KeyBERT(model=self.encoder)
        #Needed for broader categorization
        self.fields = {
        "History": "The study of past events, civilizations, ancient history (Egypt, Greece, Rome, Mesopotamia), medieval times (feudalism, knights, castles, Crusades), modern history (Renaissance, Enlightenment, Industrial Revolution, World Wars, Cold War), monarchy, wars (battles, conflicts, treaties), revolutions (political upheaval, social change), cultural heritage (artifacts, monuments, traditions), historical figures (leaders, thinkers, artists, scientists), archaeology, paleontology, timelines, primary sources, historiography.",
        "Culture": "Arts (painting, sculpture, architecture, performing arts), traditions (rituals, ceremonies, folklore), customs (etiquette, social behavior), heritage (tangible, intangible, natural), languages (linguistics, dialects, scripts), literature (poetry, novels, drama, essays), music (genres, instruments, composers), dance (styles, choreography), philosophy (ethics, metaphysics, epistemology), social norms (values, beliefs), anthropology (societies, cultures, human development), religion (faith, spirituality, deities, practices), mythology (legends, myths, folklore), cuisine, fashion, festivals, social movements.",
        "Science": "Physics (mechanics, thermodynamics, electromagnetism, optics, quantum mechanics, relativity, particle physics), chemistry (organic, inorganic, biochemistry, materials science, chemical reactions, elements, compounds), biology (botany, zoology, ecology, evolution, genetics, microbiology, anatomy, physiology, neuroscience (brain, neurons, cognition), environmental science (ecology, conservation, pollution), climate change (global warming, greenhouse gases, sustainability), scientific research (experiments, hypotheses, data analysis), medicine (health, diseases, treatments, anatomy, physiology, pharmacology), technology-driven discoveries (innovation, inventions, breakthroughs).",
        "Technology": "Artificial intelligence (machine learning, deep learning, natural language processing, computer vision, expert systems), robotics (automation, sensors, actuators), machine learning (algorithms, data science, predictive modeling), software development (programming languages, frameworks, databases, web development, mobile apps), cybersecurity (network security, data protection, cryptography), blockchain (cryptocurrencies, distributed ledgers), quantum computing (qubits, superposition, entanglement), space exploration (astronomy, astrophysics, cosmology, rockets, satellites, planets), IT (information technology, networks, hardware, software), engineering (civil, mechanical, electrical, chemical, aerospace, biomedical), gadgets, internet of things (IoT), virtual reality (VR), augmented reality (AR).",
        "Geography": "Physical geography (landforms, climate, weather, oceans, rivers, mountains, deserts, ecosystems), human geography (population, urbanization, culture, economics, political systems), cartography (maps, globes, GIS), environmental geography, regional geography, continents, countries, capitals, natural resources, climate zones, topography.",
        "Politics": "Government (democracy, monarchy, dictatorship, republic), political systems (legislative, executive, judicial), ideologies (liberalism, conservatism, socialism, communism, fascism), elections, political parties, international relations, diplomacy, law, legislation, public policy, political philosophy, human rights, activism, governance, sovereignty.",
        "Economics": "Microeconomics (supply and demand, consumer behavior, market structures), macroeconomics (GDP, inflation, unemployment, monetary policy, fiscal policy), finance (investment, banking, stock market), international trade, economic development, capitalism, socialism, communism, economic indicators, econometrics, labor economics, behavioral economics.",
        "Mathematics": "Algebra, calculus, geometry, trigonometry, statistics, probability, number theory, logic, mathematical analysis, discrete mathematics, applied mathematics, mathematical theorems, equations, formulas, proofs.",
        "Literature": "Poetry (sonnets, haikus, epics), novels (fiction, non-fiction, genres), drama (plays, scripts), short stories, essays, literary theory, authors, literary movements (Romanticism, Modernism), literary analysis, prose, verse, narrative.",
        "Performing Arts": "Music (orchestral, chamber, opera, jazz, blues, rock, pop, electronic), Dance (ballet, contemporary, folk, hip-hop, tap), Theater (acting, directing, stage design), Opera, Musical Theatre, Circus, Puppetry, Performance Art.",
        "Visual Arts": "Painting (oil, watercolor, acrylic), Sculpture (stone, metal, wood), Drawing (pencil, charcoal, ink), Photography, Film (cinematography, directing, screenwriting), Architecture, Design (graphic, industrial, fashion), Illustration, Ceramics, Textiles.",
        "Health & Wellness": "Medicine (diseases, treatments, prevention), Nutrition (diet, vitamins, minerals), Fitness (exercise, strength training, cardio), Mental health (psychology, therapy, well-being), Public health, Anatomy, Physiology, Pharmacology, Alternative medicine, Mindfulness, Stress management.",
        "Sports": "Team sports (football, basketball, soccer, baseball, hockey), Individual sports (tennis, golf, swimming, running), Combat sports (boxing, martial arts), Athletics, Olympics, Leagues, Tournaments, Rules, Strategies, Athletes.",
        "Business & Finance": "Management, Marketing, Sales, Entrepreneurship, Accounting, Investment banking, Financial markets, Economics, Business strategy, Leadership, Innovation, Corporate finance, Startups.",
        "Food & Drink": "Cuisine (national, regional, ethnic), Cooking techniques, Recipes, Ingredients, Beverages (alcoholic, non-alcoholic), Gastronomy, Food science, Nutrition, Restaurants, Chefs.",
        "Travel & Tourism": "Destinations (countries, cities, landmarks), Accommodation (hotels, hostels), Transportation (flights, trains, cars), Culture, Adventure travel, Ecotourism, History, Sightseeing, Vacation, Exploration.",
        "Environment": "Ecology, Conservation, Biodiversity, Pollution (air, water, land), Climate change, Sustainability, Renewable energy, Natural resources, Ecosystems, Wildlife, Environmental policy.",
        "Fashion & Beauty": "Clothing, Accessories, Style, Trends, Designers, Cosmetics, Skincare, Haircare, Modeling, Fashion shows, Retail, Textiles.",
        "Philosophy & Religion": "Ethics, Metaphysics, Epistemology, Logic, Political philosophy, Aesthetics, Theology, Spirituality, Deities, Religious texts, Practices, Beliefs, World religions, Mythology.",
        "Law & Justice": "Legal systems, Criminal law, Civil law, Constitutional law, Human rights, Courts, Judges, Lawyers, Legislation, Justice system, Legal theory, International law."
    }
        
        self.field_embeddings = {
            field: self.encoder.encode(desc, convert_to_tensor=True)
            for field, desc in self.fields.items()
        }
        
    def extract_keywords(self, text: str, top_n: int = 5, **kwargs) -> list[Tuple[str, float]]:
        return self.keybert.extract_keywords(text, top_n=top_n, **kwargs)
    
    def assign_field(self, keywords: list[str]) -> str:
        print(f"received : {keywords}")
        if keywords and isinstance(keywords[0], tuple):
            keyword_strings = [str(kw[0]) for kw in keywords if isinstance(kw, tuple)]
        else:
            keyword_strings = [str(kw) for kw in keywords if isinstance(kw, (str, float, int))]
        
        if not keyword_strings:
            return None

        keyword_embeddings = self.encoder.encode(keyword_strings, convert_to_tensor=True)
        print(f"Gotten keyword embeddings: {keyword_embeddings}")
        # Compute cosine similarity between keywords and field representations
        similarities = {
            field: util.pytorch_cos_sim(keyword_embeddings, field_emb).mean().item()
            for field, field_emb in self.field_embeddings.items()
        }

        return max(similarities, key=similarities.get)  # Assign field with highest similarity