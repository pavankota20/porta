#!/usr/bin/env python3
"""
FastAPI routes for Porta Finance Assistant
"""

import asyncio
import time
import uuid
from typing import Dict, Any

from fastapi import HTTPException

from config import PORTFOLIO, WATCHLIST, REQUEST_RESULTS, REQUEST_LOCK, ACTIVE_REQUESTS, MAX_STORED_REQUESTS, REQUEST_QUEUE
from models import (
    ChatRequest, ChatResponse, AsyncChatRequest, AsyncChatResponse, 
    RequestStatusResponse
)

def _pf(user_id: str):
    """Get user portfolio, create if doesn't exist"""
    return PORTFOLIO.setdefault(user_id, {})

def _wl(user_id: str):
    """Get user watchlist, create if doesn't exist"""
    return WATCHLIST.setdefault(user_id, {})

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
    """Send a message to the Porta finance assistant"""
    try:
        # Try to get agent with error handling
        try:
            agent = get_agent()
        except Exception as e:
            return ChatResponse(
                response=f"AI agent not ready yet. Please try again in a moment. Error: {str(e)}",
                user_id=request.user_id,
                status="agent_not_ready"
            )
        
        # Convert chat history
        history = []
        for msg in request.chat_history:
            if msg.get("role") == "user":
                history.append({"role": "user", "content": msg.get("content", "")})
            elif msg.get("role") == "assistant":
                history.append({"role": "assistant", "content": msg.get("content", "")})
        
        # Invoke agent
        result = agent.invoke({
            "input": request.message,
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
        
        return ChatResponse(
            response=response_text,
            user_id=request.user_id,
            status="success"
        )
        
    except Exception as e:
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

async def get_user_portfolio(user_id: str):
    """Get user's portfolio"""
    return {"portfolio": _pf(user_id), "user_id": user_id}

async def get_user_watchlist(user_id: str):
    """Get user's watchlist"""
    return {"watchlist": sorted(_wl(user_id).values()), "user_id": user_id}
