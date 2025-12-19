"""
新闻获取工具
"""
import feedparser
from typing import Dict, Any, List
from datetime import datetime
from logger import info, error
from .schemas import ToolDefinition, ToolResult, ToolStatus

# --- Tool Definitions ---

FETCH_RSS_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "fetch_rss",
        "description": "Fetch the latest news from an RSS feed URL.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the RSS feed."
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of items to return.",
                    "default": 5
                }
            },
            "required": ["url"]
        }
    }
)

# --- Tool Handlers ---

class NewsToolHandlers:
    def __init__(self):
        pass

    async def fetch_rss(self, args: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        try:
            url = args["url"]
            limit = args.get("limit", 5)
            
            info(f"[NewsTool] Fetching RSS: {url}")
            feed = feedparser.parse(url)
            
            if hasattr(feed, 'bozo_exception') and feed.bozo_exception:
                 # Warning but proceed if entries exist
                 info(f"[NewsTool] Feed parse warning: {feed.bozo_exception}")

            if not feed.entries:
                 return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="fetch_rss",
                    status=ToolStatus.ERROR,
                    error="No entries found in feed or feed is invalid."
                )

            items = []
            for entry in feed.entries[:limit]:
                items.append({
                    "title": entry.get("title", "No Title"),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", entry.get("updated", "")),
                    "summary": entry.get("summary", "")[:200] + "..." if entry.get("summary") else ""
                })
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="fetch_rss",
                status=ToolStatus.SUCCESS,
                data={
                    "feed_title": feed.feed.get("title", "Unknown Feed"),
                    "items": items
                }
            )

        except Exception as e:
            error(f"[NewsTool] Failed: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="fetch_rss",
                status=ToolStatus.ERROR,
                error=str(e)
            )

def register_news_tools(tool_registry):
    handlers = NewsToolHandlers()
    # Simple wrapper to match sync/async expectation if needed, but our executor handles async
    async def wrapper(args, ctx):
        return await handlers.fetch_rss(args, ctx)
        
    tool_registry.register_tool(FETCH_RSS_TOOL, wrapper, category="news")


