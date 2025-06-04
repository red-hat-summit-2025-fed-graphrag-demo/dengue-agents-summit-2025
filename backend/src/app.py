"""
Main application entry point for the basic agent system.
"""
import logging
import os
import uuid
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any, Set

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import API key manager
from src.api_key_manager import api_key_manager

# Set API keys from environment or mounted secrets
granite_instruct_key = api_key_manager.get_api_key("GRANITE_INSTRUCT_API_KEY")
granite_guardian_key = api_key_manager.get_api_key("GRANITE_GUARDIAN_API_KEY")
granite_embedding_key = api_key_manager.get_api_key("GRANITE_EMBEDDING_API_KEY")

# Log available API keys (without showing the actual keys)
if granite_instruct_key:
    print("✅ Granite Instruct API key found")
else:
    print("❌ Granite Instruct API key not found")

if granite_guardian_key:
    print("✅ Granite Guardian API key found")
else:
    print("❌ Granite Guardian API key not found")

if granite_embedding_key:
    print("✅ Granite Embedding API key found")
else:
    print("❌ Granite Embedding API key not found")

# Import the WorkflowManager and its ChatSession
from src.agent_system.core.workflow_manager import WorkflowManager, ChatSession
from src.registries.agent_registry import AgentRegistry

# Create FastAPI app
app = FastAPI(
    title="Agent System API",
    description="API for the Agent System",
    version="1.0.0"
)

# Add CORS middleware to allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

# Define the path to workflow registry
workflow_registry_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "registries/workflows"
)

# Initialize the agent registry
agent_registry = AgentRegistry()

# Initialize workflow manager
workflow_manager = WorkflowManager(
    registry_dir=workflow_registry_dir,
    agent_registry=agent_registry
)

# Store active sessions
active_sessions: Dict[str, ChatSession] = {}

# Store agent activity logs
agent_logs: Dict[str, Dict[str, List[Dict]]] = {}

# Track currently active agents for polling
active_agents: Dict[str, str] = {}

# Enhanced WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        # Store active connections by session ID
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Connect a new WebSocket client."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"New WebSocket connection for session {session_id}")

    async def disconnect(self, websocket: WebSocket, session_id: str):
        """Disconnect a WebSocket client."""
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
                logger.info(f"All connections closed for session {session_id}")

    async def send_message(self, session_id: str, message: dict):
        """Send a message to all connected clients for a session."""
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to WebSocket: {e}")

    async def send_agent_status(self, session_id: str, agent_id: str, status: str):
        """Send an agent status update to all connected clients for a session."""
        await self.send_message(session_id, {
            "type": "agent_status", 
            "agent_id": agent_id,
            "status": status
        })

# Initialize connection manager
manager = ConnectionManager()

# Define models for API requests and responses
class MessageRequest(BaseModel):
    """Request model for sending a message."""
    session_id: str
    message: str
    debug: bool = False
    workflow_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SessionResponse(BaseModel):
    """Response model for session creation."""
    session_id: str
    user_id: str

class AgentOutput(BaseModel):
    """Model for detailed agent output."""
    agent_id: str
    model_id: Optional[str] = None
    input: str
    output: str
    processing_time_ms: int

class MessageResponse(BaseModel):
    """Response model for message processing."""
    response: str
    agent_flow: Optional[List[str]] = None
    models_used: Optional[Dict[str, str]] = None
    agent_outputs: Optional[List[AgentOutput]] = None

# Define API routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Agent System API"}

@app.get("/health")
async def get_system_health():
    """Get system health information."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(active_sessions),
        "agents": workflow_manager.get_agent_status(),
        "providers": {
            "ollama": False,
            "vllm": False,
            "granite": True
        }
    }

@app.post("/session", response_model=SessionResponse)
async def create_session():
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Create a new chat session - using WorkflowManager's ChatSession
    session = ChatSession(session_id=session_id, user_id=user_id)
    active_sessions[session_id] = session
    agent_logs[session_id] = {}
    
    return {"session_id": session_id, "user_id": user_id}

@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    """Process a chat message through the agent system."""
    session_id = request.session_id
    message = request.message
    
    # Check if session exists
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Initialize logs for this session if not exists
    if session_id not in agent_logs:
        agent_logs[session_id] = {}
    
    try:
        # If a direct agent ID is specified, update the SINGLE_AGENT_WORKFLOW
        if request.workflow_id == "SINGLE_AGENT_WORKFLOW":
            agent_id = request.metadata.get("agent_id")
            if agent_id:
                update_single_agent_workflow(agent_id)
        
        # Process the message through the workflow manager
        result_dict = await workflow_manager.process_message(
            message_content=message,
            session_id=session_id,
            metadata=request.metadata or {},
            callbacks={
                "visualization": lambda agent_id: manager.send_agent_status(
                    session_id, agent_id, "processing"
                ),
                "log": lambda agent_id, input_text, output_text, processing_time: log_agent_activity(
                    session_id, agent_id, input_text, output_text, processing_time
                ),
                "stream": lambda agent_id, message_type, content, data: stream_agent_update(
                    session_id, agent_id, message_type, content, data
                )
            },
            workflow_id=request.workflow_id
        )
        
        # Extract response text from result
        response_text = result_dict.get("response", "An error occurred while processing your request.")
        
        # Update session with user message
        active_sessions[session_id].add_message("user", message)
        
        # Update session with assistant response
        active_sessions[session_id].add_message("assistant", response_text)
        
        return MessageResponse(
            response=response_text
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Define helper functions
async def log_agent_activity(session_id: str, agent_id: str, input_text: str, output_text: str, processing_time: int):
    """Log agent activity."""
    if agent_id not in agent_logs[session_id]:
        agent_logs[session_id][agent_id] = []
    
    agent_logs[session_id][agent_id].append({
        "timestamp": datetime.now().isoformat(),
        "input": input_text,
        "output": output_text,
        "processing_time_ms": processing_time
    })

async def stream_agent_update(session_id: str, agent_id: str, message_type: str, content: str, data: Any):
    """Stream agent updates to clients."""
    await manager.send_message(session_id, {
        "type": "agent_update",
        "agent_id": agent_id,
        "message_type": message_type,
        "content": content,
        "data": data
    })

def update_single_agent_workflow(agent_id: str):
    """Update the SINGLE_AGENT_WORKFLOW with a specific agent ID."""
    workflow_path = os.path.join(workflow_registry_dir, "SINGLE_AGENT_WORKFLOW.json")
    
    try:
        # Read the current workflow
        with open(workflow_path, 'r') as f:
            workflow_data = json.load(f)
        
        # Update the agent ID
        workflow_data["agents"][0]["agent_id"] = agent_id
        workflow_data["default_agent"] = agent_id
        
        # Write back the updated workflow
        with open(workflow_path, 'w') as f:
            json.dump(workflow_data, f, indent=2)
            
        # Reload the workflow in the workflow manager
        workflow_manager.reload_workflow("SINGLE_AGENT_WORKFLOW")
        
        return True
    except Exception as e:
        logger.error(f"Error updating single agent workflow: {e}")
        return False

@app.websocket("/ws/agent/{agent_id}")
async def websocket_agent_endpoint(websocket: WebSocket, agent_id: str):
    """WebSocket endpoint for direct agent communication."""
    session_id = str(uuid.uuid4())
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message from client
            message_text = await websocket.receive_text()
            
            # Process message through agent
            response = await workflow_manager.process_direct_agent_message(
                agent_id=agent_id, 
                message=message_text,
                session_id=session_id
            )
            
            # Send response back to client
            await manager.send_message(session_id, {
                "type": "response",
                "content": response,
                "agent_id": agent_id
            })
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"Error in agent WebSocket: {str(e)}")
        await manager.disconnect(websocket, session_id)

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time agent status and streaming updates."""
    # Accept connection
    await manager.connect(websocket, session_id)
    
    try:
        # Main WebSocket message loop
        while True:
            data = await websocket.receive_text()
            
            try:
                # Parse the message
                json_data = json.loads(data)
                message_type = json_data.get("type")
                
                if message_type == "command":
                    # Handle a command message
                    command = json_data.get("command")
                    message_text = json_data.get("message", "")
                    debug_mode = json_data.get("debug", False)
                    workflow_id = json_data.get("workflow_id")
                    
                    if command == "chat":
                        if not message_text.strip():
                            continue
                        
                        # Send acknowledgement
                        await manager.send_message(session_id, {
                            "type": "system",
                            "content": "processing",
                            "output": "Processing your message..."
                        })
                        
                        # Create a message request
                        request = MessageRequest(
                            session_id=session_id,
                            message=message_text,
                            debug=debug_mode,
                            workflow_id=workflow_id
                        )
                        
                        # Process the message using the chat endpoint logic
                        # We create a background task so we don't block the WebSocket
                        async def process_message_background():
                            try:
                                response = await chat(request)
                                # Final response will be sent by callbacks
                            except Exception as e:
                                logger.error(f"Error processing message via WebSocket: {e}")
                                await manager.send_message(session_id, {
                                    "type": "error",
                                    "content": "processing_error",
                                    "output": f"Error processing message: {str(e)}"
                                })
                        
                        # Start processing in the background
                        asyncio.create_task(process_message_background())
                    else:
                        # Unknown command
                        await manager.send_message(session_id, {
                            "type": "error",
                            "content": "unknown_command",
                            "output": f"Unknown command: {command}"
                        })
                else:
                    # Unknown message type
                    await manager.send_message(session_id, {
                        "type": "error",
                        "content": "unknown_message_type",
                        "output": "Unknown message type"
                    })
                    
            except json.JSONDecodeError:
                # Not a valid JSON message
                await manager.send_message(session_id, {
                    "type": "error",
                    "content": "invalid_json",
                    "output": "Invalid JSON message"
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Make sure to clean up connection
        await manager.disconnect(websocket, session_id)

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8000))  # Using consistent port 8000
    
    # Start the server
    uvicorn.run("src.app:app", host="0.0.0.0", port=port, reload=True)