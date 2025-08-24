#!/usr/bin/env python3
"""
FastAPI routes for Porta Finance Assistant
"""

import asyncio
import time
import uuid
import json
from datetime import datetime
from typing import Dict, Any

from fastapi import HTTPException

from config import REQUEST_RESULTS, REQUEST_LOCK, ACTIVE_REQUESTS, MAX_STORED_REQUESTS, REQUEST_QUEUE
from models import (
    ChatRequest, ChatResponse, AsyncChatRequest, AsyncChatResponse, 
    RequestStatusResponse
)
from database import db_service

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
    
    # Check if the result string contains the entire chat history (this should not happen)
    if "'input':" in result_str and "'chat_history':" in result_str:
        print(f"[DEBUG] WARNING: Result contains entire chat history, this indicates an agent configuration issue")
        # Try to extract just the output part if it exists
        if "'output':" in result_str:
            try:
                # Try to parse and extract just the output
                import ast
                parsed = ast.literal_eval(result_str)
                if isinstance(parsed, dict) and "output" in parsed:
                    output = parsed["output"]
                    print(f"[DEBUG] Extracted output from chat history: {output}")
                    return _extract_text_from_nested_content(str(output))
            except:
                pass
        # If we can't extract output, return a generic message
        return "I apologize, but there was an issue processing your request. Please try again."
    
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

# Database functions are now handled by database.py service

def get_agent():
    """Get or create the global agent instance"""
    from agent import agent_executor
    if agent_executor is None:
        from agent import build_agent
        agent_executor = build_agent()
    return agent_executor

async def root():
    """Health check endpoint"""
    return {
        "message": "Porta Finance Assistant API", 
        "status": "running",
        "version": "1.0.0"
    }

async def health_check():
    """Detailed health check"""
    try:
        from tools import TOOLS
        with REQUEST_LOCK:
            queue_size = REQUEST_QUEUE.qsize()
            active_requests = ACTIVE_REQUESTS
            
        return {
            "status": "healthy",
            "agent_ready": True,
            "tools_available": len(TOOLS),
            "tool_names": [tool.name for tool in TOOLS],
            "async_processing": {
                "queue_size": queue_size,
                "active_requests": active_requests,
                "max_concurrent": 5
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def chat_with_agent(request: ChatRequest):
    """Send a message to the Porta finance assistant with session management"""
    try:
        # Initialize database service
        await db_service.initialize()
        
        # Try to get agent with error handling
        try:
            agent = get_agent()
        except Exception as e:
            return ChatResponse(
                response=f"AI agent not ready yet. Please try again in a moment. Error: {str(e)}",
                user_id=request.user_id,
                session_id="",
                status="agent_not_ready"
            )
        
        # Get or create session
        session_id = request.session_id
        if not session_id:
            session_id = await db_service.get_or_create_session(
                user_id=request.user_id,
                session_name=f"Chat Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
        else:
            # Verify session exists and belongs to user
            try:
                # This will be implemented when we add session validation
                pass
            except Exception:
                # Create new session if validation fails
                session_id = await db_service.get_or_create_session(
                    user_id=request.user_id,
                    session_name=f"Chat Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
        
        # Get existing session messages for context (before adding new ones)
        existing_messages = await db_service.get_session_messages(session_id, limit=100)
        
        # Convert existing messages to chat history format for the agent
        history = []
        for msg in existing_messages:
            if msg["role"] in ["user", "assistant"]:
                history.append({"role": msg["role"], "content": msg["content"]})
        
        # Calculate next sequence number more robustly
        # Find the highest sequence number in existing messages
        max_sequence = 0
        if existing_messages:
            max_sequence = max(msg.get("sequence_number", 0) for msg in existing_messages)
        
        # Use the next available sequence number
        next_sequence = max_sequence + 1
        
        print(f"[DEBUG] Session {session_id}: max_sequence={max_sequence}, next_sequence={next_sequence}")
        
        # Store user message FIRST
        try:
            user_message_id = await db_service.store_message(
                session_id=session_id,
                user_id=request.user_id,
                message_type="user",
                content=request.message,
                role="user",
                sequence_number=next_sequence
            )
            print(f"[DEBUG] Stored user message with sequence {next_sequence}")
        except Exception as e:
            print(f"[ERROR] Failed to store user message: {str(e)}")
            # Try to get a fresh sequence number
            try:
                # Get fresh count and try again
                fresh_messages = await db_service.get_session_messages(session_id, limit=100)
                fresh_max_sequence = max(msg.get("sequence_number", 0) for msg in fresh_messages) if fresh_messages else 0
                fresh_next_sequence = fresh_max_sequence + 1
                print(f"[DEBUG] Retrying with fresh sequence: {fresh_next_sequence}")
                
                user_message_id = await db_service.store_message(
                    session_id=session_id,
                    user_id=request.user_id,
                    message_type="user",
                    content=request.message,
                    role="user",
                    sequence_number=fresh_next_sequence
                )
                next_sequence = fresh_next_sequence
                print(f"[DEBUG] Successfully stored user message with sequence {next_sequence}")
            except Exception as retry_e:
                print(f"[ERROR] Retry also failed: {str(retry_e)}")
                return ChatResponse(
                    response="I apologize, but there was an issue processing your request. Please try again.",
                    user_id=request.user_id,
                    session_id=session_id,
                    status="database_error"
                )
        
        # Create enhanced history that includes the current user message
        enhanced_history = history + [{"role": "user", "content": request.message}]
        
        # Pre-load user preferences to avoid fetching them on every message
        user_preferences = None
        try:
            from config import AUTO_LOAD_USER_PREFERENCES
            if AUTO_LOAD_USER_PREFERENCES:
                from tools import get_user_preferences
                prefs_result = get_user_preferences(request.user_id)
                if prefs_result.get('ok'):
                    user_preferences = prefs_result.get('preferences')
                    print(f"[DEBUG] Pre-loaded user preferences for {request.user_id}")
                else:
                    print(f"[DEBUG] No user preferences found for {request.user_id}")
            else:
                print(f"[DEBUG] Auto-loading user preferences disabled")
        except Exception as e:
            print(f"[DEBUG] Could not pre-load user preferences: {str(e)}")
        
        # Invoke agent with full conversation context
        print(f"[DEBUG] Invoking agent with input: {request.message}")
        print(f"[DEBUG] Chat history length: {len(enhanced_history)}")
        print(f"[DEBUG] User preferences loaded: {user_preferences is not None}")
        
        try:
            # Prepare agent input with user preferences
            agent_input = {
                "input": request.message,
                "chat_history": enhanced_history
            }
            
            # Add user preferences to agent input if available
            if user_preferences:
                agent_input["user_preferences"] = user_preferences
                print(f"[DEBUG] Added user preferences to agent input")
            
            result = agent.invoke(agent_input)
            print(f"[DEBUG] Agent invocation successful, result type: {type(result)}")
        except Exception as e:
            print(f"[ERROR] Agent invocation failed: {str(e)}")
            return ChatResponse(
                response="I apologize, but there was an issue processing your request. Please try again.",
                user_id=request.user_id,
                session_id=session_id,
                status="agent_error"
            )
        
        # Handle response format
        response_text = clean_agent_response(result)
        
        # Check if response is suspiciously long (might contain entire chat history)
        if len(response_text) > 2000:  # Arbitrary threshold
            print(f"[DEBUG] WARNING: Response is very long ({len(response_text)} chars), might contain chat history")
            # Try to extract just the last meaningful response
            if "'output':" in response_text:
                try:
                    import ast
                    parsed = ast.literal_eval(response_text)
                    if isinstance(parsed, dict) and "output" in parsed:
                        output = parsed["output"]
                        if isinstance(output, list) and len(output) > 0:
                            last_item = output[-1]
                            if isinstance(last_item, dict) and "text" in last_item:
                                response_text = last_item["text"]
                                print(f"[DEBUG] Extracted last response text: {response_text[:100]}...")
                except:
                    pass
            
            # If still too long, truncate and add note
            if len(response_text) > 1000:
                response_text = response_text[:1000] + "...\n\n[Response truncated due to length]"
                print(f"[DEBUG] Response truncated to {len(response_text)} chars")
        
        # Ensure response is string
        if not isinstance(response_text, str):
            response_text = str(response_text)
        
        # Store assistant response
        try:
            assistant_message_id = await db_service.store_message(
                session_id=session_id,
                user_id=request.user_id,
                message_type="assistant",
                content=response_text,
                role="assistant",
                sequence_number=next_sequence + 1
            )
            print(f"[DEBUG] Stored assistant message with sequence {next_sequence + 1}")
        except Exception as e:
            print(f"[ERROR] Failed to store assistant message: {str(e)}")
            # Try to get a fresh sequence number for the assistant message
            try:
                fresh_messages = await db_service.get_session_messages(session_id, limit=100)
                fresh_max_sequence = max(msg.get("sequence_number", 0) for msg in fresh_messages) if fresh_messages else 0
                fresh_next_sequence = fresh_max_sequence + 1
                print(f"[DEBUG] Retrying assistant message with fresh sequence: {fresh_next_sequence}")
                
                assistant_message_id = await db_service.store_message(
                    session_id=session_id,
                    user_id=request.user_id,
                    message_type="assistant",
                    content=response_text,
                    role="assistant",
                    sequence_number=fresh_next_sequence
                )
                print(f"[DEBUG] Successfully stored assistant message with sequence {fresh_next_sequence}")
            except Exception as retry_e:
                print(f"[ERROR] Assistant message retry also failed: {str(retry_e)}")
                # Continue without storing the assistant message, but return the response
                print(f"[WARNING] Could not store assistant message, but continuing with response")
        
        return ChatResponse(
            response=response_text,
            user_id=request.user_id,
            session_id=session_id,
            status="success"
        )
        
    except Exception as e:
        print(f"[ERROR] Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

async def chat_with_agent_async(request: AsyncChatRequest):
    """Send a message to the Porta finance assistant (asynchronous)"""
    try:
        request_id = str(uuid.uuid4())
        
        request_data = {
            "request_id": request_id,
            "message": request.message,
            "user_id": request.user_id,
            "chat_history": request.chat_history
        }
        
        with REQUEST_LOCK:
            REQUEST_RESULTS[request_id] = {
                "request_id": request_id,
                "status": "queued",
                "response": None,
                "user_id": request.user_id,
                "error": None,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "completed_at": None
            }
        
        REQUEST_QUEUE.put(request_data)
        
        return AsyncChatResponse(
            request_id=request_id,
            status="queued",
            message="Request queued for processing"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error queuing request: {str(e)}")

async def get_request_status(request_id: str):
    """Get the status and result of an async request"""
    try:
        with REQUEST_LOCK:
            if request_id not in REQUEST_RESULTS:
                raise HTTPException(status_code=404, detail="Request not found")
            
            result = REQUEST_RESULTS[request_id]
            return RequestStatusResponse(**result)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving request status: {str(e)}")

async def list_active_requests():
    """List all active and recent requests"""
    try:
        with REQUEST_LOCK:
            return {
                "active_requests": ACTIVE_REQUESTS,
                "queue_size": REQUEST_QUEUE.qsize(),
                "recent_requests": list(REQUEST_RESULTS.values())[-10:]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing requests: {str(e)}")

async def get_user_sessions(user_id: str):
    """Get user's chat sessions"""
    try:
        await db_service.initialize()
        sessions = await db_service.get_user_sessions(user_id, limit=20)
        return {"sessions": sessions, "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sessions: {str(e)}")

async def get_session_messages(session_id: str, user_id: str):
    """Get messages for a specific session"""
    try:
        await db_service.initialize()
        messages = await db_service.get_session_messages(session_id, limit=100)
        return {"messages": messages, "session_id": session_id, "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving messages: {str(e)}")

async def close_chat_session(session_id: str, user_id: str):
    """Close a chat session"""
    try:
        await db_service.initialize()
        success = await db_service.close_session(session_id)
        if success:
            return {"message": "Session closed successfully", "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error closing session: {str(e)}")
