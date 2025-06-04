"""
Model caller utility for making API calls to LLM services.

This module provides standardized functions for calling different language models,
ensuring consistency across the agent system. All model calls should go through
these functions rather than implementing custom API calls elsewhere.
"""
import os
import time
import json
import httpx
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

# Model IDs
GRANITE_INSTRUCT_MODEL = os.getenv("GRANITE_INSTRUCT_MODEL_NAME", "granite-3-1-8b-instruct-w4a16")
GRANITE_GUARDIAN_MODEL = os.getenv("GRANITE_GUARDIAN_MODEL_NAME", "granite3-guardian-2b")
GRANITE_EMBEDDING_MODEL = os.getenv("GRANITE_EMBEDDING_MODEL_NAME", "granite-embedding-278m-multilingual")

# API keys and URLs loaded from environment variables
GRANITE_INSTRUCT_API_KEY = os.getenv("GRANITE_INSTRUCT_API_KEY", "")
GRANITE_GUARDIAN_API_KEY = os.getenv("GRANITE_GUARDIAN_API_KEY", "")
GRANITE_EMBEDDING_API_KEY = os.getenv("GRANITE_EMBEDDING_API_KEY", "")

# Check if we have the direct URLs, otherwise fall back to the service URL
GRANITE_INSTRUCT_URL = os.getenv("GRANITE_INSTRUCT_URL", "") or os.getenv("EMBEDDING_SERVICE_URL", "")
GRANITE_GUARDIAN_URL = os.getenv("GRANITE_GUARDIAN_URL", "") or os.getenv("EMBEDDING_SERVICE_URL", "")
GRANITE_EMBEDDING_URL = os.getenv("GRANITE_EMBEDDING_URL", "") or os.getenv("EMBEDDING_SERVICE_URL", "")

class ModelResponse:
    """Standard response object for model calls."""
    
    def __init__(
        self, 
        content: str, 
        model_id: str, 
        processing_time_ms: int,
        response_id: str = None,
        raw_response: Optional[Dict[str, Any]] = None,
        usage: Optional[Dict[str, int]] = None,
        finish_reason: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize a model response.
        
        Args:
            content: The text content of the response
            model_id: The ID of the model that generated the response
            processing_time_ms: Processing time in milliseconds
            response_id: Unique ID for the response
            raw_response: The raw API response
            usage: Token usage statistics
            finish_reason: Reason for finishing generation
            tool_calls: Any tool calls made by the model
        """
        self.content = content
        self.model_id = model_id
        self.processing_time_ms = processing_time_ms
        self.id = response_id or f"response-{uuid.uuid4()}"
        self.raw_response = raw_response
        self.usage = usage or {}
        self.finish_reason = finish_reason
        self.tool_calls = tool_calls or []
        
    def __str__(self) -> str:
        """String representation of the response."""
        return f"ModelResponse(model={self.model_id}, content_length={len(self.content)}, time={self.processing_time_ms}ms)"

async def call_granite_instruct(
    messages: List[Dict[str, str]],
    max_tokens: int = 1024,
    temperature: float = 0.7,
    tools: Optional[List[Dict]] = None
) -> ModelResponse:
    """
    Call the Granite Instruct model.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        max_tokens: Maximum number of tokens to generate
        temperature: Sampling temperature (0.0 to 1.0)
        tools: Optional list of tools to make available to the model
        
    Returns:
        ModelResponse object with the model's response
    """
    start_time = time.time()
    
    # Check if API key and URL are available
    if not GRANITE_INSTRUCT_API_KEY or not GRANITE_INSTRUCT_URL:
        error_msg = "Granite Instruct API key or URL not configured"
        logger.error(error_msg)
        return ModelResponse(
            content=f"Error: {error_msg}",
            model_id=GRANITE_INSTRUCT_MODEL,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
    
    try:
        # Normalize the URL
        base_url = GRANITE_INSTRUCT_URL
        if base_url.endswith('/v1/chat/completions'):
            base_url = base_url[:-len('/v1/chat/completions')]
        elif base_url.endswith('/'):
            base_url = base_url[:-1]
        
        # Prepare the request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GRANITE_INSTRUCT_API_KEY}"
        }
        
        request_data = {
            "model": GRANITE_INSTRUCT_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Add tools if provided
        if tools:
            request_data["tools"] = tools
            
        # Log the request (with masked key)
        masked_key = GRANITE_INSTRUCT_API_KEY[:4] + "*" * (len(GRANITE_INSTRUCT_API_KEY) - 8) + GRANITE_INSTRUCT_API_KEY[-4:]
        logger.debug(f"Calling Granite Instruct at {base_url}/v1/chat/completions with API key {masked_key}")
        
        # Make the API call
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json=request_data
            )
            
            # Handle response
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Extract tool calls if present
                tool_calls = None
                if "tool_calls" in result.get("choices", [{}])[0].get("message", {}):
                    tool_calls = result["choices"][0]["message"]["tool_calls"]
                
                return ModelResponse(
                    content=content,
                    model_id=GRANITE_INSTRUCT_MODEL,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    response_id=result.get("id"),
                    raw_response=result,
                    usage=result.get("usage"),
                    finish_reason=result.get("choices", [{}])[0].get("finish_reason"),
                    tool_calls=tool_calls
                )
            else:
                error_detail = response.text
                try:
                    error_json = response.json()
                    if "error" in error_json:
                        error_detail = error_json["error"].get("message", str(error_json["error"]))
                except json.JSONDecodeError:
                    pass  # Keep original text if not JSON
                
                error_msg = f"HTTP {response.status_code}: {error_detail}"
                logger.error(f"Granite Instruct API error: {error_msg}")
                return ModelResponse(
                    content=f"Error: {error_msg}",
                    model_id=GRANITE_INSTRUCT_MODEL,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
    
    except Exception as e:
        error_msg = f"Error calling Granite Instruct: {str(e)}"
        logger.exception(error_msg)
        return ModelResponse(
            content=f"Error: {error_msg}",
            model_id=GRANITE_INSTRUCT_MODEL,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )

async def call_granite_guardian(
    messages: List[Dict[str, str]],
    max_tokens: int = 256,
    temperature: float = 0.3
) -> ModelResponse:
    """
    Call the Granite Guardian model for content safety checking.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        max_tokens: Maximum number of tokens to generate
        temperature: Sampling temperature (0.0 to 1.0)
        
    Returns:
        ModelResponse object with the model's response
    """
    start_time = time.time()
    
    # Check if API key and URL are available
    if not GRANITE_GUARDIAN_API_KEY or not GRANITE_GUARDIAN_URL:
        error_msg = "Granite Guardian API key or URL not configured"
        logger.error(error_msg)
        return ModelResponse(
            content=f"Error: {error_msg}",
            model_id=GRANITE_GUARDIAN_MODEL,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
    
    try:
        # Normalize the URL
        base_url = GRANITE_GUARDIAN_URL
        if base_url.endswith('/v1/chat/completions'):
            base_url = base_url[:-len('/v1/chat/completions')]
        elif base_url.endswith('/'):
            base_url = base_url[:-1]
        
        # Prepare the request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GRANITE_GUARDIAN_API_KEY}"
        }
        
        request_data = {
            "model": GRANITE_GUARDIAN_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Log the request (with masked key)
        masked_key = GRANITE_GUARDIAN_API_KEY[:4] + "*" * (len(GRANITE_GUARDIAN_API_KEY) - 8) + GRANITE_GUARDIAN_API_KEY[-4:]
        logger.debug(f"Calling Granite Guardian at {base_url}/v1/chat/completions with API key {masked_key}")
        
        # Make the API call
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json=request_data
            )
            
            # Handle response
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                return ModelResponse(
                    content=content,
                    model_id=GRANITE_GUARDIAN_MODEL,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    response_id=result.get("id"),
                    raw_response=result,
                    usage=result.get("usage"),
                    finish_reason=result.get("choices", [{}])[0].get("finish_reason")
                )
            else:
                error_detail = response.text
                try:
                    error_json = response.json()
                    if "error" in error_json:
                        error_detail = error_json["error"].get("message", str(error_json["error"]))
                except json.JSONDecodeError:
                    pass  # Keep original text if not JSON
                
                error_msg = f"HTTP {response.status_code}: {error_detail}"
                logger.error(f"Granite Guardian API error: {error_msg}")
                return ModelResponse(
                    content=f"Error: {error_msg}",
                    model_id=GRANITE_GUARDIAN_MODEL,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
    
    except Exception as e:
        error_msg = f"Error calling Granite Guardian: {str(e)}"
        logger.exception(error_msg)
        return ModelResponse(
            content=f"Error: {error_msg}",
            model_id=GRANITE_GUARDIAN_MODEL,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )

async def call_granite_embedding(
    text: str
) -> Tuple[Optional[List[float]], ModelResponse]:
    """
    Call the Granite Embedding model to generate embeddings for text.
    
    Args:
        text: The text to generate embeddings for
        
    Returns:
        Tuple of (embedding vector, ModelResponse)
        If an error occurs, embedding vector will be None
    """
    start_time = time.time()
    
    # Check if API key and URL are available
    if not GRANITE_EMBEDDING_API_KEY or not GRANITE_EMBEDDING_URL:
        error_msg = "Granite Embedding API key or URL not configured"
        logger.error(error_msg)
        response = ModelResponse(
            content=f"Error: {error_msg}",
            model_id=GRANITE_EMBEDDING_MODEL,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        return None, response
    
    try:
        # Normalize the URL
        base_url = GRANITE_EMBEDDING_URL
        if base_url.endswith('/v1/embeddings'):
            base_url = base_url[:-len('/v1/embeddings')]
        elif base_url.endswith('/'):
            base_url = base_url[:-1]
        
        # Prepare the request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GRANITE_EMBEDDING_API_KEY}"
        }
        
        request_data = {
            "model": GRANITE_EMBEDDING_MODEL,
            "input": text
        }
        
        # Log the request (with masked key)
        masked_key = GRANITE_EMBEDDING_API_KEY[:4] + "*" * (len(GRANITE_EMBEDDING_API_KEY) - 8) + GRANITE_EMBEDDING_API_KEY[-4:]
        logger.debug(f"Calling Granite Embedding at {base_url}/v1/embeddings with API key {masked_key}")
        
        # Make the API call
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{base_url}/v1/embeddings",
                headers=headers,
                json=request_data
            )
            
            # Handle response
            if response.status_code == 200:
                result = response.json()
                embeddings = result.get("data", [{}])[0].get("embedding", [])
                
                response_obj = ModelResponse(
                    content="Embedding generated successfully",
                    model_id=GRANITE_EMBEDDING_MODEL,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    response_id=result.get("id"),
                    raw_response=result,
                    usage=result.get("usage")
                )
                
                return embeddings, response_obj
            else:
                error_detail = response.text
                try:
                    error_json = response.json()
                    if "error" in error_json:
                        error_detail = error_json["error"].get("message", str(error_json["error"]))
                except json.JSONDecodeError:
                    pass  # Keep original text if not JSON
                
                error_msg = f"HTTP {response.status_code}: {error_detail}"
                logger.error(f"Granite Embedding API error: {error_msg}")
                response_obj = ModelResponse(
                    content=f"Error: {error_msg}",
                    model_id=GRANITE_EMBEDDING_MODEL,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
                return None, response_obj
    
    except Exception as e:
        error_msg = f"Error calling Granite Embedding: {str(e)}"
        logger.exception(error_msg)
        response_obj = ModelResponse(
            content=f"Error: {error_msg}",
            model_id=GRANITE_EMBEDDING_MODEL,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        return None, response_obj

# Helper function to convert Message objects to dictionary format
def convert_messages_to_dict(messages: List[Any]) -> List[Dict[str, str]]:
    """
    Convert Message objects to dictionaries for API requests.
    
    This function handles both dictionary inputs and object inputs with
    role and content attributes.
    
    Args:
        messages: List of messages (dicts or objects with role/content)
        
    Returns:
        List of dictionaries with 'role' and 'content' keys
    """
    result = []
    
    for msg in messages:
        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
            # Already in the right format
            result.append({
                'role': msg['role'], 
                'content': msg['content']
            })
        elif hasattr(msg, 'role') and hasattr(msg, 'content'):
            # Convert object to dict
            result.append({
                'role': msg.role.value if hasattr(msg.role, 'value') else str(msg.role),
                'content': msg.content
            })
        else:
            # Log warning about unexpected format
            logger.warning(f"Unexpected message format: {type(msg)}. Skipping.")
            
    return result