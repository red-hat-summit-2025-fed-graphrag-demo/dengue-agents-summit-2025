"""
WebSocket router for agent interactions.

This module provides WebSocket endpoints for real-time agent interactions.
"""
import os
import sys
import json
import logging
import asyncio
import traceback
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Dict, Any, List, Optional, Union
import uuid
from datetime import datetime

# Import from the backend - set up sys.path to allow importing from backend
# REMOVED: sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

# Import the backend components
from src.registries.agent_registry import AgentRegistry
from src.registries.prompt_registry import PromptRegistry
from src.agent_system.core.message import Message, MessageRole

# Configure logging
logger = logging.getLogger("api.ws")

# Create router
router = APIRouter(prefix="/ws", tags=["websocket"])

"""
WebSocket endpoints for real-time agent and workflow interactions.
These endpoints enable bidirectional communication for agent processing.
"""

# Create connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_registry = AgentRegistry()
        self.prompt_registry = PromptRegistry()
        
    async def connect(self, websocket: WebSocket, client_id: str) -> str:
        """Connect a WebSocket client."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client connected: {client_id}")
        return client_id
        
    def disconnect(self, client_id: str):
        """Disconnect a WebSocket client."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client disconnected: {client_id}")
    
    async def send_message(self, client_id: str, message: Dict[str, Any]):
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
            
    async def stream_callback(self, agent_id: str, message_type: str, content: str, data: Any = None):
        """Callback for streaming agent updates to the websocket."""
        # Find which client is associated with this agent call
        # For now, we broadcast to all clients - in a real app, you'd map sessions to clients
        for client_id, websocket in self.active_connections.items():
            message = {
                "type": "agent_stream",
                "agent_id": agent_id,
                "message_type": message_type,
                "content": content,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_json(message)
            logger.debug(f"Streamed update to client {client_id}: {message_type}")
    
    async def process_agent_request(self, client_id: str, agent_id: str, message_content: str):
        """Process a request using the specified agent."""
        try:
            # Get the agent from the registry
            agent = self.agent_registry.instantiate_agent(agent_id)
            logger.info(f"Using agent: {agent.name} (ID: {agent.agent_id})")
            
            # Create the user message
            user_message = Message(
                role=MessageRole.USER,
                content=message_content
            )
            
            # Generate session ID
            session_id = f"session_{uuid.uuid4()}"
            
            # Send status update to client
            await self.send_message(client_id, {
                "type": "status",
                "status": "processing",
                "message": f"Processing with agent: {agent.name}",
                "timestamp": datetime.now().isoformat()
            })
            
            # Process the message
            response_message, next_agent = await agent.process(
                message=user_message,
                session_id=session_id,
                stream_callback=self.stream_callback
            )
            
            # Send the response to the client
            if response_message:
                await self.send_message(client_id, {
                    "type": "response",
                    "agent_id": agent_id,
                    "content": response_message.content,
                    "next_agent": next_agent,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"Sent response to client {client_id}")
                
                # Print to console for testing
                print("\n" + "=" * 60)
                print(f" RESPONSE FROM AGENT: {agent.name} ".center(60, "="))
                print("=" * 60)
                print(response_message.content)
                print("=" * 60 + "\n")
                
                return response_message.content
            else:
                await self.send_message(client_id, {
                    "type": "error",
                    "message": "No response received from agent",
                    "timestamp": datetime.now().isoformat()
                })
                logger.error(f"No response received from agent {agent_id}")
                return None
                
        except Exception as e:
            error_message = f"Error processing request with agent {agent_id}: {str(e)}"
            logger.error(error_message)
            
            # Send error to client
            await self.send_message(client_id, {
                "type": "error",
                "message": error_message,
                "timestamp": datetime.now().isoformat()
            })
            return None

# Create manager instance
manager = ConnectionManager()

# --- Global WorkflowManager instance (Consider Dependency Injection for production) ---
try:
    from src.agent_system.core.workflow_manager import WorkflowManager # Updated path
    # Define the path to the workflow registry directory relative to this file's location
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../.."))
    workflow_registry_dir = os.path.join(project_root, "backend/src/registries/workflows")
    
    # Verify the directory exists
    if not os.path.isdir(workflow_registry_dir):
        logger.critical(f"Workflow registry directory not found: {workflow_registry_dir}")
        workflow_manager_instance = None
    else:
        logger.info(f"Initializing WorkflowManager with registry_dir: {workflow_registry_dir}")
        workflow_manager_instance = WorkflowManager(registry_dir=workflow_registry_dir)
        # Validate that GRAPH_RAG_WORKFLOW is loaded
        try:
            workflow_manager_instance.get_steps("GRAPH_RAG_WORKFLOW")
            logger.info(f"Successfully loaded GRAPH_RAG_WORKFLOW")
        except ValueError as e:
            logger.warning(f"GRAPH_RAG_WORKFLOW not found in registry: {e}")
        logger.info(f"WorkflowManager initialized successfully with workflows: {list(workflow_manager_instance._workflows.keys())}")
except Exception as e:
    logger.critical(f"Failed to initialize WorkflowManager: {e}. Workflow endpoint will not function.")
    logger.critical(traceback.format_exc())
    workflow_manager_instance = None
# -----------------------------------------------------------------------------------

# --- NEW Workflow Endpoint --- 
@router.websocket("/workflow/{workflow_name}")
async def websocket_workflow_endpoint(
    websocket: WebSocket,
    workflow_name: str,
    client_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for executing a specific workflow.

    **Connection:**
    - URL: `/ws/workflow/{workflow_name}`
    - Parameters:
        - workflow_name: ID of the workflow to execute
        - client_id: Optional client identifier for reconnection (auto-generated if not provided)

    **Message Protocol:**
    - Client -> Server:
        ```json
        {
            "message": "string",      # User prompt/message content
            "metadata": {             # Optional metadata
                "key1": "value1",
                ...
            }
        }
        ```
        
    - Server -> Client (multiple message types):
        1. Connection established:
        ```json
        {
            "type": "connected",
            "client_id": "string",
            "workflow_name": "string",
            "message": "string",
            "timestamp": "ISO-8601 timestamp"
        }
        ```
        
        2. Stream updates during processing:
        ```json
        {
            "type": "stream_update",
            "agent_id": "string",
            "message_type": "string",  # e.g., "status", "thinking"
            "content": "string",
            "data": {},                # Optional additional data
            "timestamp": "ISO-8601 timestamp"
        }
        ```
        
        3. Final result:
        ```json
        {
            "type": "workflow_result",
            "content": {},
            "metadata": {},
            "trace_logs": [],
            "session_id": "string",
            "timestamp": "ISO-8601 timestamp"
        }
        ```
        
        4. Error result:
        ```json
        {
            "type": "workflow_error",
            "error": "string",
            "metadata": {},
            "trace_logs": [],
            "session_id": "string",
            "timestamp": "ISO-8601 timestamp"
        }
        ```
    """
    logger.info(f"Incoming WS connection request for workflow: {workflow_name}") # Log entry

    if not workflow_manager_instance:
        # Log and reject immediately if manager isn't ready
        logger.warning(f"Rejecting WS connection for workflow {workflow_name} - WorkflowManager not initialized.")
        return # Simply return, connection won't be established.

    client_id = client_id or f"client_{uuid.uuid4()}"
    logger.info(f"Attempting to accept connection for client {client_id}...")
    await manager.connect(websocket, client_id) # This internally calls await websocket.accept()
    logger.info(f"Connection accepted for client {client_id}, workflow {workflow_name}")

    session_id = None # Track session ID across messages if needed

    try:
        logger.info(f"Sending 'connected' message to client {client_id}")
        await manager.send_message(client_id, {
            "type": "connected",
            "client_id": client_id,
            "workflow_name": workflow_name,
            "message": f"Connected for workflow: {workflow_name}",
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"Starting message receive loop for client {client_id}")
        while True:
            # Add logging before receive
            logger.info(f"[Client {client_id}] Waiting to receive message...")
            data = await websocket.receive_json()
            # Add logging after receive, showing raw data
            logger.info(f"[Client {client_id}] Received raw data: {data}")

            if not isinstance(data, dict):
                logger.warning(f"[Client {client_id}] Received non-dict data: {type(data)}")
                await manager.send_message(client_id, {
                    "type": "error",
                    "message": "Invalid message format. Please send a JSON object.",
                    "timestamp": datetime.now().isoformat()
                })
                continue

            message_content = data.get("message", "")
            initial_metadata = data.get("metadata", {})

            if not message_content:
                 await manager.send_message(client_id, {
                    "type": "error",
                    "message": "Missing 'message' field in request.",
                    "timestamp": datetime.now().isoformat()
                })
                 continue

            logger.info(f"Received workflow request from client {client_id} for '{workflow_name}': {message_content[:50]}...")

            # Define the stream callback specific to this connection/request
            async def workflow_stream_callback(agent_id: str, message_type: str, content: str, data: Any = None):
                payload = {
                    "type": "stream_update",
                    "agent_id": agent_id,
                    "message_type": message_type, # e.g., "status", "thinking"
                    "content": content,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_message(client_id, payload)

            # Generate or reuse session ID for the workflow run
            current_session_id = session_id or f"wf_session_{uuid.uuid4()}"
            if not session_id: # Store if first message in session
                session_id = current_session_id

            # Call the WorkflowManager
            result = {}
            try:
                result = await workflow_manager_instance.process_message(
                    message_content=message_content,
                    user_id=client_id, 
                    session_id=current_session_id,
                    metadata=initial_metadata,
                    callbacks={"stream": workflow_stream_callback},
                    workflow_id=workflow_name 
                )
            except Exception as wf_exc:
                 # Catch errors during workflow processing itself
                 logger.error(f"Exception during WorkflowManager.process_message for session {current_session_id}: {wf_exc}", exc_info=True)
                 result = {
                     "error": f"Internal server error during workflow execution: {str(wf_exc)}",
                     "session_id": current_session_id,
                     "metadata": initial_metadata, # Metadata might not have been updated
                     "trace_logs": [{"event": "fatal_error", "error": str(wf_exc), "traceback": traceback.format_exc()}] # Add a basic error log
                 }


            # Prepare the final response payload
            response_payload = {
                "session_id": result.get("session_id", current_session_id), # Use generated ID if result missing one
                "timestamp": datetime.now().isoformat(),
                "trace_logs": result.get("trace_logs", []) 
            }

            if "error" in result:
                response_payload["type"] = "workflow_error"
                response_payload["error"] = result["error"]
                response_payload["metadata"] = result.get("metadata", {})
                logger.error(f"Workflow '{workflow_name}' error for client {client_id}, session {response_payload['session_id']}: {result['error']}")
            else:
                response_payload["type"] = "workflow_result"
                # Map the "response" field from backend to "content" for frontend
                response_payload["content"] = result.get("response")
                
                # Handle case where content is None but we have trace logs
                if response_payload["content"] is None and "trace_logs" in response_payload:
                    # Look for the last step output in the trace logs
                    for log in reversed(response_payload["trace_logs"]):
                        if log.get("event") == "step_end" and "output_content_summary" in log:
                            response_payload["content"] = log["output_content_summary"]
                            logger.info("Recovered content from trace logs")
                            break
                
                # If still None, provide a fallback message
                if response_payload["content"] is None:
                    response_payload["content"] = "No response generated. Please try again."
                
                # Ensure visualization_data doesn't get too large
                if "metadata" in result and result["metadata"]:
                    metadata = result.get("metadata", {})
                    # Trim visualization data if it's too large
                    if "visualization_data" in metadata and isinstance(metadata["visualization_data"], dict):
                        viz_data = metadata["visualization_data"]
                        # Truncate large arrays to reasonable sizes
                        for key in ["historical_data", "predicted_data", "data"]:
                            if key in viz_data and isinstance(viz_data[key], list) and len(viz_data[key]) > 20:
                                viz_data[key] = viz_data[key][:20]  # Keep only first 20 items
                                logger.info(f"Truncated {key} to prevent oversized response")
                
                response_payload["metadata"] = result.get("metadata", {})
                logger.info(f"Sent workflow '{workflow_name}' response to client {client_id}, session {response_payload['session_id']}")

            # Send the final result (including trace logs)
            try:
                await manager.send_message(client_id, response_payload)
            except Exception as send_error:
                logger.error(f"Error sending response: {str(send_error)}")
                # Create a simplified response if the full one fails
                simplified_payload = {
                    "type": response_payload["type"],
                    "content": response_payload.get("content", "Error: Response too large to transmit"),
                    "session_id": response_payload["session_id"],
                    "timestamp": response_payload["timestamp"]
                }
                await manager.send_message(client_id, simplified_payload)
                
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected from workflow {workflow_name}.")
        # manager.disconnect(client_id) # Disconnect is handled in finally
    except Exception as e:
        # Log any unexpected error during the websocket lifecycle
        logger.error(f"Unhandled exception in workflow websocket for client {client_id}, workflow {workflow_name}: {e}", exc_info=True)
        try:
            # Attempt to send an error message if possible
            await manager.send_message(client_id, {
                "type": "error",
                "message": f"Server error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as send_err:
            logger.error(f"Failed to send error message to client {client_id}: {send_err}")
    finally:
        # Ensure the connection is cleaned up
        logger.info(f"Cleaning up WS connection for client {client_id}")
        manager.disconnect(client_id)

# --- End NEW Workflow Endpoint --- 

@router.websocket("/agent/{agent_id}")
async def websocket_agent_endpoint(
    websocket: WebSocket, 
    agent_id: str,
    client_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for interacting with a specific agent.
    
    **Connection:**
    - URL: `/ws/agent/{agent_id}`
    - Parameters:
        - agent_id: ID of the agent to interact with
        - client_id: Optional client identifier for reconnection (auto-generated if not provided)
    
    **Message Protocol:**
    - Client -> Server:
        ```json
        {
            "message": "string"  # Message content to process
        }
        ```
        Or plain text message
        
    - Server -> Client (multiple message types):
        1. Connection established:
        ```json
        {
            "type": "connected",
            "client_id": "string",
            "agent_id": "string",
            "message": "string",
            "timestamp": "ISO-8601 timestamp"
        }
        ```
        
        2. Agent updates during processing (streamed):
        ```json
        {
            "type": "agent_stream",
            "agent_id": "string",
            "message_type": "string",
            "content": "string",
            "data": {},
            "timestamp": "ISO-8601 timestamp"
        }
        ```
        
        3. Status messages:
        ```json
        {
            "type": "status",
            "status": "string",
            "message": "string",
            "timestamp": "ISO-8601 timestamp"
        }
        ```
        
        4. Agent response:
        ```json
        {
            "type": "response",
            "agent_id": "string",
            "content": "string",
            "next_agent": "string or null",
            "session_id": "string",
            "timestamp": "ISO-8601 timestamp"
        }
        ```
        
        5. Error messages:
        ```json
        {
            "type": "error",
            "message": "string",
            "timestamp": "ISO-8601 timestamp"
        }
        ```
    """
    # Generate client ID if not provided
    if not client_id:
        client_id = f"client_{uuid.uuid4()}"
        
    # Connect the client
    await manager.connect(websocket, client_id)
    
    try:
        # Send welcome message
        await manager.send_message(client_id, {
            "type": "connected",
            "client_id": client_id,
            "agent_id": agent_id,
            "message": f"Connected to agent: {agent_id}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Process messages
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                # Parse the message
                message_data = json.loads(data)
                message_content = message_data.get("message", "")
                
                # Log the received message
                logger.info(f"Received message from client {client_id}: {message_content[:50]}...")
                
                # Process the message with the agent
                await manager.process_agent_request(client_id, agent_id, message_content)
                
            except json.JSONDecodeError:
                # Handle plain text messages for testing
                logger.info(f"Received plain text message from client {client_id}: {data[:50]}...")
                
                # Process the message with the agent
                await manager.process_agent_request(client_id, agent_id, data)
                
    except WebSocketDisconnect:
        # Handle disconnect
        manager.disconnect(client_id)
        
    except Exception as e:
        # Handle other exceptions
        logger.error(f"Error in WebSocket connection: {str(e)}")
        manager.disconnect(client_id)