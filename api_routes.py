#!/usr/bin/env python3
"""
FastAPI routes for Porta Finance Assistant
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import HTTPException

from config import REQUEST_RESULTS, REQUEST_LOCK, ACTIVE_REQUESTS, MAX_STORED_REQUESTS, REQUEST_QUEUE
from models import (
    ChatRequest, ChatResponse, AsyncChatRequest, AsyncChatResponse, 
    RequestStatusResponse
)
from database import db_service

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
        existing_messages = await db_service.get_session_messages(session_id, limit=50)
        
        # Convert existing messages to chat history format for the agent
        history = []
        for msg in existing_messages:
            if msg["role"] in ["user", "assistant"]:
                history.append({"role": msg["role"], "content": msg["content"]})
        
        # Calculate next sequence number
        next_sequence = len(existing_messages) + 1
        
        # Store user message FIRST
        user_message_id = await db_service.store_message(
            session_id=session_id,
            user_id=request.user_id,
            message_type="user",
            content=request.message,
            role="user",
            sequence_number=next_sequence
        )
        
        # Create enhanced history that includes the current user message
        enhanced_history = history + [{"role": "user", "content": request.message}]
        
        # Invoke agent with full conversation context
        result = agent.invoke({
            "input": request.message,
            "chat_history": enhanced_history
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
        
        # Store assistant response
        assistant_message_id = await db_service.store_message(
            session_id=session_id,
            user_id=request.user_id,
            message_type="assistant",
            content=response_text,
            role="assistant",
            sequence_number=next_sequence + 1
        )
        
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
