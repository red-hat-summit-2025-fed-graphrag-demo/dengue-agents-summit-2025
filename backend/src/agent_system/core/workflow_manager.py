"""
Workflow manager that coordinates the workflow between different agents.
"""

import os
import json
import logging
import time
import uuid
import asyncio
import traceback
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, Callable

from src.agent_system.core.message import Message, MessageRole
from src.registries.agent_registry import AgentRegistry


logger = logging.getLogger(__name__)

class ChatSession:
    """Chat session model for tracking conversation state."""
    def __init__(self, session_id: str, user_id: str = "anonymous"):
        """
        Initialize a new chat session.
        
        Args:
            session_id: Unique identifier for the session
            user_id: Identifier for the user
        """
        self.session_id = session_id
        self.user_id = user_id
        self.messages: List[Message] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.metadata: Dict[str, Any] = {}


class WorkflowManager:
    """
    Loads and manages agent workflows defined as JSON files in a registry directory.
    Also executes workflows by instantiating and coordinating agents.

    Schema:
      - Each workflow file is named <WORKFLOW_ID>.json and contains:
        {
          "steps": [ <step1>, <step2>, ... ]
        }
      - Step can be:
        - str: agent ID
        - {"sub_workflow": "<WORKFLOW_ID>"}
        - {"loop": { "condition_key": "<key>", "steps": [ ... ], "max_iterations": int (optional) }}
    """

    def __init__(self, registry_dir: str, agent_registry: Optional[AgentRegistry] = None):
        """
        Initialize the workflow manager.
        
        Args:
            registry_dir: Directory containing workflow JSON files
            agent_registry: Optional agent registry for instantiating agents
        """
        self.registry_dir = registry_dir
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._load_all()
        
        # Agent registry for instantiating agents
        self.agent_registry = agent_registry or AgentRegistry()
        
        # Cache of agent instances
        self.agent_instances: Dict[str, Any] = {}
        
        # Active sessions
        self.sessions: Dict[str, ChatSession] = {}
        
        # Default workflow ID to use when none is specified
        self.default_workflow_id = "COMPLIANCE_SANDWICH_WORKFLOW"
        
        logger.info(f"WorkflowManager initialized with {len(self._workflows)} workflows")

    def _load_all(self) -> None:
        """Load all workflow JSON files from the registry directory."""
        if not os.path.isdir(self.registry_dir):
            raise FileNotFoundError(f"Workflow registry directory not found: {self.registry_dir}")
        for fname in os.listdir(self.registry_dir):
            if not fname.endswith(".json"):
                continue
            wf_id = fname[:-5]
            path = os.path.join(self.registry_dir, fname)
            with open(path, "r") as f:
                self._workflows[wf_id] = json.load(f)

    def get_steps(self, workflow_id: str) -> List[Any]:
        """
        Return raw steps for the given workflow ID.
        """
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        return deepcopy(self._workflows[workflow_id].get("steps", []))

    def flatten_steps(self, workflow_id: str) -> List[Any]:
        """
        Recursively expand sub_workflow entries into a flat list.
        Loop directives remain as dicts for the executor to interpret.
        """
        flat: List[Any] = []
        for step in self.get_steps(workflow_id):
            if isinstance(step, str):
                flat.append(step)
            elif isinstance(step, dict) and "sub_workflow" in step:
                flat.extend(self.flatten_steps(step["sub_workflow"]))
            else:
                # loop or other directive
                flat.append(step)
        return flat
        
    def _get_or_create_session(self, session_id: Optional[str] = None, user_id: str = "anonymous") -> str:
        """
        Get an existing session or create a new one.
        
        Args:
            session_id: Optional session ID to use
            user_id: Optional user ID to use
            
        Returns:
            Session ID
        """
        if not session_id:
            session_id = str(uuid.uuid4())
            
        if session_id not in self.sessions:
            self.sessions[session_id] = ChatSession(session_id, user_id)
            
        return session_id
        
    def _get_agent(self, agent_id: str) -> Any:
        """
        Get an agent instance by ID, creating it if it doesn't exist.
        
        Args:
            agent_id: The ID of the agent to get
            
        Returns:
            Agent instance
            
        Raises:
            ValueError: If the agent can't be instantiated
        """
        if agent_id in self.agent_instances:
            return self.agent_instances[agent_id]
        
        try:
            # Instantiate the agent using the registry
            agent = self.agent_registry.instantiate_agent(agent_id)
            
            # Cache the agent instance
            self.agent_instances[agent_id] = agent
            
            logger.info(f"Instantiated agent: {agent_id}")
            return agent
        except Exception as e:
            error_msg = f"Failed to instantiate agent {agent_id}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def reload_workflow(self, workflow_id: str) -> None:
        """
        Reload a specific workflow from disk.
        
        Args:
            workflow_id: ID of the workflow to reload
        """
        path = os.path.join(self.registry_dir, f"{workflow_id}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Workflow not found: {path}")
            
        with open(path, "r") as f:
            self._workflows[workflow_id] = json.load(f)
            
        logger.info(f"Reloaded workflow: {workflow_id}")
    
    async def process_message(
        self, 
        message_content: str, 
        user_id: str = "anonymous",
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        callbacks: Optional[Dict[str, Callable]] = None,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user message through a workflow.
        
        Args:
            message_content: The user message to process
            user_id: User identifier
            session_id: Optional session identifier
            metadata: Optional additional metadata
            callbacks: Optional callback functions for visualization, logging, and streaming
            workflow_id: Optional workflow identifier (uses default if not specified)
            
        Returns:
            Dictionary with response content, session ID, and metadata
        """
        # Initialize metadata
        if not metadata:
            metadata = {}
            
        # Initialize callbacks
        if not callbacks:
            callbacks = {}
            
        # Setup helper functions for callbacks
        async def call_visualization(agent_id: str) -> None:
            """Call visualization callback if provided."""
            visualization_cb = callbacks.get('visualization')
            if not visualization_cb:
                return
                
            if asyncio.iscoroutinefunction(visualization_cb):
                await visualization_cb(agent_id=agent_id)
            else:
                visualization_cb(agent_id=agent_id)
                
        async def call_log(agent_id: str, input_text: str, output_text: str, processing_time: int) -> None:
            """Call log callback if provided."""
            log_cb = callbacks.get('log')
            if not log_cb:
                return
                
            if asyncio.iscoroutinefunction(log_cb):
                await log_cb(
                    agent_id=agent_id,
                    input_text=input_text,
                    output_text=output_text,
                    processing_time=processing_time
                )
            else:
                log_cb(
                    agent_id=agent_id,
                    input_text=input_text,
                    output_text=output_text,
                    processing_time=processing_time
                )
                
        async def handle_stream(agent_id: str, message_type: str, content: str, data: Any) -> None:
            """Handle streaming callback."""
            stream_cb = callbacks.get('stream')
            if not stream_cb:
                return
                
            if asyncio.iscoroutinefunction(stream_cb):
                await stream_cb(
                    agent_id=agent_id, 
                    message_type=message_type, 
                    content=content, 
                    data=data
                )
            else:
                stream_cb(
                    agent_id=agent_id, 
                    message_type=message_type, 
                    content=content, 
                    data=data
                )
        
        # Get or create session
        session_id = self._get_or_create_session(session_id, user_id)
        session = self.sessions[session_id]
        
        # Create user message
        user_message = Message(
            role=MessageRole.USER, 
            content=message_content, 
            metadata=metadata
        )
        
        # Add user message to session history
        session.messages.append(user_message)
        session.updated_at = datetime.now().isoformat()
        
        # Determine workflow to use
        workflow_id = workflow_id or metadata.pop("workflow_id", self.default_workflow_id)
        
        try:
            # Record start time
            start_time = time.time()
            
            # Get flattened workflow steps
            workflow_steps = self.flatten_steps(workflow_id)
            logger.info(f"Executing workflow '{workflow_id}' with {len(workflow_steps)} steps")

            # Initialize trace logs list
            trace_logs = []

            # Initial workflow state log
            initial_log_data = {
                "event": "workflow_start",
                "session_id": session_id,
                "workflow_id": workflow_id,
                "initial_message_content_summary": message_content[:200] + ("..." if len(message_content) > 200 else ""),
                "initial_metadata": metadata
            }
            trace_logs.append(initial_log_data)
            
            # Stream workflow start event
            await handle_stream(
                agent_id="workflow_manager",
                message_type="workflow_update",
                content="starting",
                data={
                    "status": "starting",
                    "message": f"Starting workflow {workflow_id}",
                    "workflow_id": workflow_id,
                    "step_count": len(workflow_steps)
                }
            )

            # Variables to track during workflow execution
            final_response_content: Optional[str] = None
            accumulated_metadata: Dict[str, Any] = user_message.metadata.copy()
            current_step_index = 0
            
            # Process through the workflow
            while current_step_index < len(workflow_steps):
                current_agent_id = workflow_steps[current_step_index]
                
                # Handle complex workflow step directives
                if not isinstance(current_agent_id, str):
                    # Handle loop or other directives
                    logger.info(f"Handling complex workflow directive: {current_agent_id}")
                    
                    # Check if this is a loop directive
                    if "loop" in current_agent_id:
                        loop_config = current_agent_id["loop"]
                        condition_key = loop_config.get("condition_key")
                        condition_value = loop_config.get("condition_value")
                        steps = loop_config.get("steps", [])
                        max_iterations = loop_config.get("max_iterations", 3)
                        fallback_agent = loop_config.get("fallback_agent")
                        fallback_message = loop_config.get("fallback_message", "Previous step returned no results.")
                        
                        # Stream loop start event
                        await handle_stream(
                            agent_id="workflow_manager",
                            message_type="loop_update",
                            content="starting",
                            data={
                                "status": "starting",
                                "message": f"Starting loop with condition key: {condition_key}",
                                "condition_key": condition_key,
                                "condition_value": condition_value,
                                "max_iterations": max_iterations,
                                "steps": steps
                            }
                        )
                    
                        # Execute loop steps
                        current_iteration = 0
                        rewrite_needed = False
                        while current_iteration < max_iterations:
                            # Execute each step in the loop
                            loop_result = None
                            for step_agent_id in steps:
                                try:
                                    # Get the agent instance
                                    agent = self._get_agent(step_agent_id)
                                    
                                    # Call visualization callback
                                    await call_visualization(step_agent_id)
                                    
                                    # Create input message with metadata
                                    input_message = Message(
                                        role=MessageRole.USER,
                                        content=user_message.content,
                                        metadata=accumulated_metadata.copy()
                                    )
                                    
                                    # Process with current agent
                                    start_time = time.time()
                                    agent_response, next_step = await agent.process(
                                        input_message if loop_result is None else loop_result,
                                        session_id, 
                                        handle_stream
                                    )
                                    processing_time = int((time.time() - start_time) * 1000)
                                    
                                    # Call log callback
                                    input_content = input_message.content if loop_result is None else loop_result.content
                                    await call_log(
                                        step_agent_id,
                                        input_content,
                                        agent_response.content if agent_response else "",
                                        processing_time
                                    )
                                    
                                    # Update loop result for next step
                                    loop_result = agent_response
                                    
                                    # Update accumulated metadata
                                    if agent_response and agent_response.metadata:
                                        accumulated_metadata.update(agent_response.metadata)
                                    
                                    # Store the response content
                                    if agent_response:
                                        final_response_content = agent_response.content
                                        
                                except Exception as e:
                                    logger.error(f"Error in loop step {step_agent_id}: {e}", exc_info=True)
                                    break
                            
                            # Check if we need to do another iteration based on condition
                            if condition_key in accumulated_metadata:
                                if accumulated_metadata[condition_key] == condition_value:
                                    # Condition matched, continue looping with fallback
                                    current_iteration += 1
                                    rewrite_needed = True
                                    
                                    # Stream loop iteration event
                                    await handle_stream(
                                        agent_id="workflow_manager",
                                        message_type="loop_update",
                                        content="iterating",
                                        data={
                                            "status": "iterating",
                                            "message": f"Loop condition matched, starting iteration {current_iteration}",
                                            "current_iteration": current_iteration,
                                            "max_iterations": max_iterations,
                                            "condition_matched": True
                                        }
                                    )
                                    
                                    if current_iteration < max_iterations and fallback_agent:
                                        # Call the fallback agent to rewrite the query
                                        fallback_agent_instance = self._get_agent(fallback_agent)
                                        
                                        # Create a fallback message
                                        fallback_input = Message(
                                            role=MessageRole.USER,
                                            content=fallback_message,
                                            metadata={
                                                **accumulated_metadata,
                                                "original_query": user_message.content,
                                                "query_rewrite_attempted": True,
                                                "rewrite_count": current_iteration
                                            }
                                        )
                                        
                                        # Stream fallback agent start event
                                        await handle_stream(
                                            agent_id="workflow_manager",
                                            message_type="fallback_update",
                                            content="starting",
                                            data={
                                                "status": "starting",
                                                "message": f"Using fallback agent {fallback_agent} to rewrite query",
                                                "fallback_agent": fallback_agent,
                                                "iteration": current_iteration,
                                                "fallback_message": fallback_message
                                            }
                                        )
                                        
                                        # Process with fallback agent
                                        start_time = time.time()
                                        fallback_response, _ = await fallback_agent_instance.process(
                                            fallback_input,
                                            session_id,
                                            handle_stream
                                        )
                                        processing_time = int((time.time() - start_time) * 1000)
                                        
                                        # Call log callback
                                        await call_log(
                                            fallback_agent,
                                            fallback_message,
                                            fallback_response.content if fallback_response else "",
                                            processing_time
                                        )
                                        
                                        # Update for next iteration
                                        loop_result = fallback_response
                                        
                                        # Update accumulated metadata
                                        if fallback_response and fallback_response.metadata:
                                            accumulated_metadata.update(fallback_response.metadata)
                                        
                                        continue
                                    else:
                                        # Max iterations reached or no fallback agent
                                        logger.info(f"Loop condition still matched after {current_iteration} iterations, moving on")
                                        break
                                else:
                                    # Condition not matched, exit loop
                                    logger.info(f"Loop condition not matched, exiting loop")
                                    break
                            else:
                                # Condition key not found in metadata
                                logger.warning(f"Loop condition key '{condition_key}' not found in metadata")
                                break
                        
                        # Move to the next step after loop
                        current_step_index += 1
                        continue
                    else:
                        # Not a recognized directive, skip
                        logger.warning(f"Complex workflow directive not recognized: {current_agent_id}")
                        current_step_index += 1
                        continue
                
                try:
                    # Get the agent instance
                    agent = self._get_agent(current_agent_id)
                    
                    # Call visualization callback
                    await call_visualization(current_agent_id)
                    
                    # Create a new message with accumulated metadata for this agent 
                    agent_input_message = Message(
                        role=MessageRole.USER,
                        content=user_message.content,
                        metadata=accumulated_metadata.copy()
                    )
                    
                    # --- Log Step Start ---
                    log_data_before = {
                        "event": "step_start",
                        "session_id": session_id,
                        "workflow_id": workflow_id,
                        "step_index": current_step_index,
                        "step_id": current_agent_id,
                        "agent_id": current_agent_id,
                        "input_content_summary": agent_input_message.content[:200] + ("..." if len(agent_input_message.content) > 200 else ""),
                        "input_metadata": agent_input_message.metadata,
                        "accumulated_metadata_before": accumulated_metadata
                    }
                    trace_logs.append(log_data_before)
                    
                    # Stream step start event
                    await handle_stream(
                        agent_id="workflow_manager",
                        message_type="step_update",
                        content="starting",
                        data={
                            "status": "starting",
                            "message": f"Starting agent: {current_agent_id}",
                            "step_index": current_step_index,
                            "step_id": current_agent_id,
                            "step_type": "agent",
                            "total_steps": len(workflow_steps)
                        }
                    )
                    # ----------------------

                    # Process with current agent
                    start_time = time.time()
                    
                    agent_response, next_step = await agent.process(
                        agent_input_message,
                        session_id, 
                        handle_stream
                    )
                    processing_time = int((time.time() - start_time) * 1000)
                    
                    # Call log callback
                    await call_log(
                        current_agent_id,
                        agent_input_message.content,
                        agent_response.content if agent_response else "",
                        processing_time
                    )
                    
                    # Update accumulated metadata
                    if agent_response and agent_response.metadata:
                        accumulated_metadata.update(agent_response.metadata)
                    
                    # Store the response content
                    if agent_response:
                        final_response_content = agent_response.content
                    
                    # --- Log Step End ---
                    output_content_summary = ""
                    output_metadata = {}
                    if agent_response:
                        output_content_summary = agent_response.content[:200] + ("..." if len(agent_response.content) > 200 else "")
                        output_metadata = agent_response.metadata

                    log_data_after = {
                        "event": "step_end",
                        "session_id": session_id,
                        "workflow_id": workflow_id,
                        "step_index": current_step_index,
                        "step_id": current_agent_id,
                        "agent_id": current_agent_id,
                        "processing_time_ms": processing_time,
                        "output_content_summary": output_content_summary,
                        "output_metadata": output_metadata,
                        "accumulated_metadata_after": accumulated_metadata,
                        "next_step_override": next_step # Log if agent suggested a next step
                    }
                    trace_logs.append(log_data_after)
                    
                    # Stream step completion event
                    result_summary = ""
                    
                    # Add specific result summaries based on agent type
                    if current_agent_id == "injection_check_agent":
                        safety_result = accumulated_metadata.get("safety_check_passed", True)
                        result_summary = f"Safety check {'passed' if safety_result else 'failed'}"
                    elif current_agent_id == "policy_check_agent":
                        safety_result = accumulated_metadata.get("safety_check_passed", True)
                        result_summary = f"Policy check {'passed' if safety_result else 'failed'}"
                    elif current_agent_id == "simple_query_writer_agent":
                        query = accumulated_metadata.get("cypher_query", "")
                        pattern_name = accumulated_metadata.get("pattern_name", "unknown")
                        extracted_countries = accumulated_metadata.get("extracted_countries", [])
                        result_summary = f"Generated query using pattern: {pattern_name}"
                        if extracted_countries:
                            countries_str = ", ".join(extracted_countries)
                            result_summary += f"\nCountries mentioned: {countries_str}"
                    elif current_agent_id == "graph_query_executor_agent":
                        result_count = accumulated_metadata.get("result_count", 0)
                        result_summary = f"Query executed, found {result_count} results"
                    elif current_agent_id == "graph_result_assessor_agent":
                        assessment = accumulated_metadata.get("assessment", "unknown")
                        result_summary = f"Results assessment: {assessment}"
                        
                    await handle_stream(
                        agent_id="workflow_manager",
                        message_type="step_update",
                        content="completed",
                        data={
                            "status": "completed",
                            "message": f"Completed agent: {current_agent_id}",
                            "step_index": current_step_index,
                            "step_id": current_agent_id,
                            "processing_time_ms": processing_time,
                            "result_summary": result_summary
                        }
                    )
                    # --------------------

                    # Special handling for safety agent blocks
                    if current_agent_id in ["injection_check_agent", "policy_check_agent"]:
                        # If safety check failed, skip to final response
                        if next_step is None or accumulated_metadata.get("blocked", False):
                            logger.info(f"Safety check failed at {current_agent_id}. Skipping to final response.")
                            break
                    
                    # Special handling for router-like agents
                    if next_step and next_step != "next":
                        # Find the index of the target agent in the workflow
                        target_index = -1
                        for i, step in enumerate(workflow_steps):
                            if isinstance(step, str) and step == next_step:
                                target_index = i
                                break
                        
                        if target_index >= 0:
                            # We found the target agent, jump to it
                            logger.info(f"Agent {current_agent_id} routed to {next_step} (step {target_index})")
                            current_step_index = target_index
                            continue
                        else:
                            # Target agent not found in workflow, assume next step
                            logger.warning(f"Agent {current_agent_id} routed to {next_step} but not found in workflow")
                            current_step_index += 1
                    else:
                        # Move to the next step in the workflow
                        current_step_index += 1
                    
                except Exception as e:
                    logger.error(f"Error processing with agent {current_agent_id}: {e}", exc_info=True)
                    final_response_content = f"An error occurred while processing your request. Please try again later."
                    break
            
            # Workflow completed successfully
            final_log_data = {
                "event": "workflow_end",
                "session_id": session_id,
                "workflow_id": workflow_id,
                "status": "success",
                "final_content_summary": final_response_content[:200] + ("..." if len(final_response_content) > 200 else ""),
                "final_metadata": accumulated_metadata
            }
            trace_logs.append(final_log_data)
            
            # Stream workflow completion event
            await handle_stream(
                agent_id="workflow_manager",
                message_type="workflow_update",
                content="completed",
                data={
                    "status": "completed",
                    "message": f"Workflow {workflow_id} completed successfully",
                    "workflow_id": workflow_id,
                    "processing_time_ms": int((time.time() - start_time) * 1000) if 'start_time' in locals() else 0
                }
            )

            # Create final response
            final_message = Message(
                role=MessageRole.ASSISTANT,
                content=final_response_content or "I apologize, but I couldn't generate a response.",
                metadata=accumulated_metadata
            )
            
            # Add to session history
            session.messages.append(final_message)
            session.updated_at = datetime.now().isoformat()
            
            # Return the response
            return {
                "response": final_message.content if final_message.content else "I apologize, but I couldn't generate a response.",
                "session_id": session_id,
                "metadata": accumulated_metadata,
                "trace_logs": trace_logs
            }
            
        except Exception as e:
            # Workflow ended due to an error (could be agent error or other manager error)
            logger.exception(f"Workflow '{workflow_id}' terminated with error for session '{session_id}': {e}")
            
            # Define accumulated_metadata if it doesn't exist yet (for early errors)
            if 'accumulated_metadata' not in locals():
                accumulated_metadata = metadata.copy() if metadata else {}
                
            final_log_data = {
                "event": "workflow_end",
                "session_id": session_id,
                "workflow_id": workflow_id,
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "final_metadata": accumulated_metadata
            }
            trace_logs.append(final_log_data)
            
            # Stream workflow error event
            await handle_stream(
                agent_id="workflow_manager",
                message_type="workflow_update",
                content="error",
                data={
                    "status": "error",
                    "message": f"Workflow {workflow_id} encountered an error: {str(e)}",
                    "workflow_id": workflow_id,
                    "error": str(e),
                    "processing_time_ms": int((time.time() - start_time) * 1000) if 'start_time' in locals() else 0
                }
            )

            # Return an error structure including trace logs
            return {
                "error": f"Workflow execution failed: {str(e)}",
                "session_id": session_id,
                "metadata": accumulated_metadata,
                "trace_logs": trace_logs
            }

    async def process_direct_agent_message(self, agent_id: str, message: str, session_id: Optional[str] = None) -> str:
        """
        Process a message directly for a specific agent via WebSocket.
        
        Args:
            agent_id: The ID of the agent to process the message
            message: The message content to process
            session_id: Optional session ID
            
        Returns:
            The agent's response as a string
        """
        # Get or create session
        session_id = self._get_or_create_session(session_id)
        
        # Create message object with user role
        message_obj = Message(content=message, role=MessageRole.USER)
        
        try:
            # Get the agent instance
            agent = self._get_agent(agent_id)
            if not agent:
                return f"Error: Agent '{agent_id}' not found"
            
            # Process the message with the agent
            response_msg, _ = await agent.process(message_obj, session_id)
            
            if response_msg:
                return response_msg.content
            else:
                return f"Error: Agent '{agent_id}' did not produce a response"
        
        except Exception as e:
            logger.error(f"Error processing direct agent message: {e}")
            return f"Error processing message with agent '{agent_id}': {str(e)}"

    def get_agent_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the status of all instantiated agents.
        
        Returns:
            Dictionary mapping agent IDs to status information
        """
        return {
            agent_id: {
                "id": agent_id,
                "name": getattr(agent, "name", agent_id),
                "description": getattr(agent, "description", ""),
                "type": getattr(agent, "agent_type", "unknown")
            }
            for agent_id, agent in self.agent_instances.items()
        }