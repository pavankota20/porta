#!/usr/bin/env python3
"""
Asynchronous request processing for Porta Finance Assistant
"""

import asyncio
import time
import threading
import json
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from typing import Dict, Any

from config import MAX_CONCURRENT_REQUESTS, MAX_STORED_REQUESTS

# Import shared variables from config
from config import REQUEST_QUEUE, REQUEST_RESULTS, REQUEST_LOCK, ACTIVE_REQUESTS

executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS)

def clean_agent_response(result: Any) -> str:
    """
    Clean and normalize agent response to extract clean text content.
    Handles nested JSON strings and various response formats.
    """
    if isinstance(result, dict):
        if "output" in result:
            return str(result["output"])
        elif "text" in result:
            return _extract_text_from_nested_content(result["text"])
        elif "content" in result:
            return str(result["content"])
        else:
            return str(result)
    
    elif isinstance(result, list) and len(result) > 0:
        first_item = result[0]
        if isinstance(first_item, dict):
            if "text" in first_item:
                return _extract_text_from_nested_content(first_item["text"])
            elif "content" in first_item:
                return str(first_item["content"])
            else:
                return str(first_item)
        else:
            return str(first_item)
    
    else:
        return str(result)

def _extract_text_from_nested_content(text_content: str) -> str:
    """
    Extract clean text from potentially nested JSON content.
    """
    if not isinstance(text_content, str):
        return str(text_content)
    
    # Check if it looks like a JSON string
    text_content = text_content.strip()
    if (text_content.startswith('[') and text_content.endswith(']')) or \
       (text_content.startswith('{') and text_content.endswith('}')):
        try:
            parsed_content = json.loads(text_content)
            if isinstance(parsed_content, list) and len(parsed_content) > 0:
                first_item = parsed_content[0]
                if isinstance(first_item, dict) and "text" in first_item:
                    return first_item["text"]
                else:
                    return str(first_item)
            elif isinstance(parsed_content, dict) and "text" in parsed_content:
                return parsed_content["text"]
            else:
                return str(parsed_content)
        except (json.JSONDecodeError, ValueError):
            # If parsing fails, return the original content
            pass
    
    return text_content

def process_request_sync(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single request synchronously"""
    import config
    
    request_id = request_data["request_id"]
    message = request_data["message"]
    user_id = request_data["user_id"]
    chat_history = request_data["chat_history"]
    
    try:
        with config.REQUEST_LOCK:
            config.REQUEST_RESULTS[request_id]["status"] = "processing"
        
        # Get agent with error handling
        try:
            from api_routes import get_agent
            agent = get_agent()
        except Exception as e:
            error_msg = f"AI agent not ready: {str(e)}"
            with config.REQUEST_LOCK:
                config.REQUEST_RESULTS[request_id].update({
                    "status": "error",
                    "error": error_msg,
                    "completed_at": time.strftime("%Y-%m-%d %H:%M:%S")
                })
            return {"status": "error", "error": error_msg}
        
        # Convert chat history
        history = []
        for msg in chat_history:
            if msg.get("role") == "user":
                history.append({"role": "user", "content": msg.get("content", "")})
            elif msg.get("role") == "assistant":
                history.append({"role": "assistant", "content": msg.get("content", "")})
        
        # Invoke agent
        result = agent.invoke({
            "input": message,
            "chat_history": history
        })
        
        # Handle response format using the utility function
        response_text = clean_agent_response(result)
        
        # Ensure response is string
        if not isinstance(response_text, str):
            response_text = str(response_text)
        
        # Update results
        with config.REQUEST_LOCK:
            config.REQUEST_RESULTS[request_id].update({
                "status": "completed",
                "response": response_text,
                "completed_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # Cleanup old requests
            if len(config.REQUEST_RESULTS) > MAX_STORED_REQUESTS:
                old_requests = [
                    rid for rid, data in config.REQUEST_RESULTS.items()
                    if data["status"] in ["completed", "error"]
                ]
                if len(old_requests) > MAX_STORED_REQUESTS // 2:
                    for rid in old_requests[:len(old_requests) - MAX_STORED_REQUESTS // 2]:
                        config.REQUEST_RESULTS.pop(rid, None)
        
        return {"status": "success", "response": response_text}
        
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        print(f"Error in request {request_id}: {error_msg}")
        
        with config.REQUEST_LOCK:
            config.REQUEST_RESULTS[request_id].update({
                "status": "error",
                "error": error_msg,
                "completed_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {"status": "error", "error": error_msg}

async def process_request_queue():
    """Background task to process queued requests"""
    import config
    
    while True:
        try:
            with config.REQUEST_LOCK:
                if config.ACTIVE_REQUESTS < MAX_CONCURRENT_REQUESTS and not config.REQUEST_QUEUE.empty():
                    request_data = config.REQUEST_QUEUE.get_nowait()
                    config.ACTIVE_REQUESTS += 1
                else:
                    await asyncio.sleep(0.1)
                    continue
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(executor, process_request_sync, request_data)
            
            with config.REQUEST_LOCK:
                config.ACTIVE_REQUESTS -= 1
                
        except Exception as e:
            print(f"Error in request queue processor: {e}")
            await asyncio.sleep(1)
