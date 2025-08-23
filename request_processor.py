#!/usr/bin/env python3
"""
Asynchronous request processing for Porta Finance Assistant
"""

import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from typing import Dict, Any

from config import MAX_CONCURRENT_REQUESTS, MAX_STORED_REQUESTS

# Import shared variables from config
from config import REQUEST_QUEUE, REQUEST_RESULTS, REQUEST_LOCK, ACTIVE_REQUESTS

executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS)

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
        
        # Handle response format
        if isinstance(result, dict) and "output" in result:
            response_text = result["output"]
        elif isinstance(result, list) and len(result) > 0:
            first_item = result[0]
            if isinstance(first_item, dict):
                if "text" in first_item:
                    response_text = first_item["text"]
                elif "content" in first_item:
                    response_text = first_item["content"]
                else:
                    response_text = str(first_item)
            else:
                response_text = str(first_item)
        else:
            response_text = str(result)
        
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
