from .api import router
from logger import info

def init_plugin(llm_service, content_manager, data_dir, gpt_sovits_url, tts_service, conversation_manager=None):
    """Initialize the PDF Narrator plugin."""
    from . import api
    
    # Inject dependencies
    api.llm_service = llm_service
    api.content_manager = content_manager
    api.DATA_DIR = data_dir
    api.GPT_SOVITS_URL = gpt_sovits_url
    api.tts_service = tts_service
    api.conversation_manager = conversation_manager
    
    # Default to disabled or enabled? 
    # Usually enabled by default unless user turned it off.
    # But for "switch" logic, we start with whatever default is.
    api._enabled = True 
    
    info("[PdfNarrator] Plugin initialized.")
    return router

async def startup():
    pass

async def shutdown():
    from . import api
    api._enabled = False
    info("[PdfNarrator] Plugin shutdown (disabled).")


