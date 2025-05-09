# src/medium_clone_suggestion/main.py

import asyncio
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from medium_clone_suggestion.recommendation_engine import RecommendationSystem
from medium_clone_suggestion.article_processor.main import main as ArticleProcessingMain
from medium_clone_suggestion.user_processor.user_profile_builder import UserProfileBuilder
from medium_clone_suggestion.user_processor.config import Config as UserProcessorConfig

from medium_clone_suggestion.logger import get_logger

logging = get_logger(__name__)

app = FastAPI()
rec_sys = RecommendationSystem()
scheduler = AsyncIOScheduler()

### ── ARTICLE PROCESSING QUEUE ───────────────────────────────────────────────

POSTID_LIMIT = 1
postid_queue = []

class PostIDRequest(BaseModel):
    postid: uuid.UUID

class PostProcessResponse(BaseModel):
    message: str

async def _run_article_pipeline():
    """Offload blocking pipeline to thread when queue threshold is reached."""
    if len(postid_queue) >= POSTID_LIMIT:
        logging.info(f"Running article pipeline on {len(postid_queue)} items…")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, ArticleProcessingMain)
        postid_queue.clear()
        logging.info("Article pipeline complete.")

@app.post("/process", response_model=PostProcessResponse)
async def enqueue_post(post: PostIDRequest):
    postid_queue.append(post.postid)
    logging.info(f"Queued postid {post.postid}, queue size={len(postid_queue)}")
    if len(postid_queue) >= POSTID_LIMIT:
        asyncio.create_task(_run_article_pipeline())
    return {"message": "Post ID queued for processing"}

# schedule periodic full runs
def schedule_article_job():
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(_run_article_pipeline(), loop)
    
### ── USER PROFILE REBUILD ───────────────────────────────────────────────────

async def _run_user_profile_builder():
    loop = asyncio.get_running_loop()
    cfg = UserProcessorConfig()
    builder = UserProfileBuilder(cfg)
    # offload to thread
    await loop.run_in_executor(None, builder.process_users, cfg.USER_PROCESS_LIMIT)
    logging.info("User profiles rebuilt.")

def schedule_user_profile_job():
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(_run_user_profile_builder(), loop)

### ── RECOMMENDATION ENDPOINT ─────────────────────────────────────────────────



@app.get("/{profile_id}/suggest")
async def suggest(
    profile_id: str,
    num_recommendations: int = 10,
    exploration_ratio: float = 0.15,
    articles_per_field: int = 20
):
    try:
        recs = rec_sys.recommend_articles(
            user_id=profile_id,
            num_recommendations=num_recommendations,
            exploration_ratio=exploration_ratio,
            articles_per_field=articles_per_field,
        )
        return {"recommendations": recs}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"There was an error recommending: {e}")
        raise HTTPException(status_code=500, detail=str(e))

### ── STARTUP SCHEDULER ───────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    # one-off runs
    asyncio.create_task(_run_article_pipeline())
    asyncio.create_task(_run_user_profile_builder())

    # recurring jobs
    scheduler.add_job(_run_article_pipeline,        "interval", hours=3, id="article_job")
    scheduler.add_job(_run_user_profile_builder,    "interval", hours=1, id="user_profile_job")
    
    # Add more to the victorizer. 
    scheduler.add_job(      
        lambda: rec_sys._incremental_corpus_update(100),
        "interval",
        hours=8,
        id="corpus_update_job"
   )
    
    scheduler.start()

    logging.info("Schedulers started: articles every 3h, profiles every 1h")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("medium_clone_suggestion.main:app", host="127.0.0.1", port=8800, reload=True)
