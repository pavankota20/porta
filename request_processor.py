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
    print(f"[DEBUG] Raw agent result: {result}")
    print(f"[DEBUG] Result type: {type(result)}")
    
    # Convert result to string first to handle all cases
    result_str = str(result)
    print(f"[DEBUG] Result as string: {result_str}")
    
    # Check if the result string contains JSON-like structures
    if "'text':" in result_str or '"text":' in result_str:
        print(f"[DEBUG] Detected text field in result string")
        return _extract_text_from_nested_content(result_str)
    
    if isinstance(result, dict):
        if "output" in result:
            output = result["output"]
            print(f"[DEBUG] Found 'output' field: {output}")
            return _extract_text_from_nested_content(str(output))
        elif "text" in result:
            text = result["text"]
            print(f"[DEBUG] Found 'text' field: {text}")
            return _extract_text_from_nested_content(str(text))
        elif "content" in result:
            content = result["content"]
            print(f"[DEBUG] Found 'content' field: {content}")
            return _extract_text_from_nested_content(str(content))
        else:
            print(f"[DEBUG] No recognized fields, converting to string")
            return _extract_text_from_nested_content(str(result))
    
    elif isinstance(result, list) and len(result) > 0:
        first_item = result[0]
        print(f"[DEBUG] First list item: {first_item}")
        if isinstance(first_item, dict):
            if "text" in first_item:
                text = first_item["text"]
                print(f"[DEBUG] Found 'text' in first item: {text}")
                return _extract_text_from_nested_content(str(text))
            elif "content" in first_item:
                content = first_item["content"]
                print(f"[DEBUG] Found 'content' in first item: {content}")
                return _extract_text_from_nested_content(str(content))
            else:
                print(f"[DEBUG] No recognized fields in first item, converting to string")
                return _extract_text_from_nested_content(str(first_item))
        else:
            print(f"[DEBUG] First item is not dict, converting to string")
            return _extract_text_from_nested_content(str(first_item))
    
    else:
        print(f"[DEBUG] Result is not dict or list, converting to string")
        return _extract_text_from_nested_content(str(result))

def _extract_text_from_nested_content(text_content: str) -> str:
    """
    Extract clean text from potentially nested JSON content.
    """
    if not isinstance(text_content, str):
        text_content = str(text_content)
    
    print(f"[DEBUG] Extracting text from: {text_content}")
    
    # First, try to handle the case where the content looks like a Python repr of a list
    # This handles cases like "[{'text': '...', 'type': 'text', 'index': 0}]"
    if text_content.startswith("[{") and text_content.endswith("}]"):
        print(f"[DEBUG] Detected Python repr of list, trying to extract text")
        try:
            # Try to evaluate it as Python literal (safer than eval)
            import ast
            parsed_content = ast.literal_eval(text_content)
            print(f"[DEBUG] Successfully parsed with ast.literal_eval: {parsed_content}")
            
            if isinstance(parsed_content, list) and len(parsed_content) > 0:
                first_item = parsed_content[0]
                print(f"[DEBUG] First parsed item: {first_item}")
                if isinstance(first_item, dict) and "text" in first_item:
                    final_text = first_item["text"]
                    print(f"[DEBUG] Extracted final text: {final_text}")
                    return final_text
                else:
                    final_text = str(first_item)
                    print(f"[DEBUG] Converted first item to string: {final_text}")
                    return final_text
            else:
                final_text = str(parsed_content)
                print(f"[DEBUG] Converted parsed content to string: {final_text}")
                return final_text
        except (ValueError, SyntaxError) as e:
            print(f"[DEBUG] ast.literal_eval failed: {e}, trying JSON parsing")
    
    # Check if it looks like a JSON string
    text_content = text_content.strip()
    if (text_content.startswith('[') and text_content.endswith(']')) or \
       (text_content.startswith('{') and text_content.endswith('}')):
        try:
            parsed_content = json.loads(text_content)
            print(f"[DEBUG] Successfully parsed JSON: {parsed_content}")
            
            if isinstance(parsed_content, list) and len(parsed_content) > 0:
                first_item = parsed_content[0]
                print(f"[DEBUG] First parsed item: {first_item}")
                if isinstance(first_item, dict) and "text" in first_item:
                    final_text = first_item["text"]
                    print(f"[DEBUG] Extracted final text: {final_text}")
                    return final_text
                else:
                    final_text = str(first_item)
                    print(f"[DEBUG] Converted first item to string: {final_text}")
                    return final_text
            elif isinstance(parsed_content, dict) and "text" in parsed_content:
                final_text = parsed_content["text"]
                print(f"[DEBUG] Extracted text from dict: {final_text}")
                return final_text
            else:
                final_text = str(parsed_content)
                print(f"[DEBUG] Converted parsed content to string: {final_text}")
                return final_text
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[DEBUG] JSON parsing failed: {e}, trying ast.literal_eval")
            try:
                import ast
                parsed_content = ast.literal_eval(text_content)
                print(f"[DEBUG] Successfully parsed with ast.literal_eval: {parsed_content}")
                
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
            except (ValueError, SyntaxError) as e2:
                print(f"[DEBUG] ast.literal_eval also failed: {e2}")
    
    print(f"[DEBUG] No JSON detected, returning original content: {text_content}")
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
