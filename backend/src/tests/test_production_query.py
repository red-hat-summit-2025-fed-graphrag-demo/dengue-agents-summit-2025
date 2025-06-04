"""
Test script for the conversational feedback approach in production mode.

This script tests the actual production HybridQueryWriterAgent implementation
with real validation to see how it behaves with real queries.
"""
import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Tuple, Set, Optional

# Add the project root to the Python path
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from src.agent_system.rag_system.query.hybrid_query_writer_agent import HybridQueryWriterAgent
from src.agent_system.core.message import Message, MessageRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("production_query_test")

# Test queries designed to potentially trigger validation issues
TEST_QUERIES = [
    # This query deliberately uses node labels and relationship types that might not exist
    "What is the connection between rainfall patterns and mosquito breeding cycles in dengue transmission?",
    
    # This query deliberately lacks specific entities which might trigger refinement
    "What are the serotypes of dengue and how do they affect treatment?",
    
    # This query targets invalid relationships potentially
    "What organizations fund dengue research and what treatments have they developed?"
]

class ConversationTrackingAgent(HybridQueryWriterAgent):
    """Extension of HybridQueryWriterAgent that tracks conversation for output"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_conversation = []  # Store the conversation history
    
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Override to capture conversation history while using production validation
        """
        # Store initial user message
        self._last_conversation = [message]
        
        # Get schema for validation
        schema = await self._retrieve_schema()
        
        # Extract valid node labels, relationship types from schema
        valid_node_labels = set(schema.get("node_labels", schema.get("nodeLabels", [])))
        valid_rel_types = set(schema.get("relationship_types", schema.get("relationshipTypes", [])))
        
        logger.info(f"Valid node labels: {valid_node_labels}")
        logger.info(f"Valid relationship types: {valid_rel_types}")
        
        # Initialize conversation with the user's original message
        conversation = [message]
        
        # Try ICL approach first with limited attempts in a conversational manner
        icl_attempts = 0
        cypher_query = None
        is_valid = False
        final_response = None
        
        while icl_attempts < self.max_icl_attempts:
            # Log attempt information before processing
            logger.info(f"Trying ICL approach (attempt {icl_attempts + 1}/{self.max_icl_attempts})")
            
            # Process with ICL agent using conversation
            response, cypher_query, is_valid, attempt_count = await self.icl_agent.process_with_feedback(
                conversation, valid_node_labels, valid_rel_types, session_id
            )
            
            # Update the actual attempt count (important for tracking)
            icl_attempts = attempt_count
            
            # Update conversation with the agent's response
            conversation.append(response)
            
            # Store the response in our conversation history
            self._last_conversation.append(response)
            
            # Validate the query - using the real production validation
            is_valid, validation_error = self._validate_query(
                cypher_query, valid_node_labels, valid_rel_types
            )
            
            if is_valid:
                logger.info("Valid query generated using ICL approach")
                final_response = response
                break
            else:
                logger.warning(f"Invalid query from ICL (attempt {icl_attempts}): {validation_error}")
                
                # Add to failed queries collection
                self._failed_queries.append({
                    "query": cypher_query,
                    "error": validation_error
                })
                
                # If we have attempts left, add feedback to the conversation
                if icl_attempts < self.max_icl_attempts:
                    # Create a message with feedback about the validation error
                    rel_sample = ", ".join(list(valid_rel_types)[:5]) + "..."
                    node_sample = ", ".join(list(valid_node_labels)[:5]) + "..."
                    
                    feedback_content = (
                        f"The Cypher query you provided has an error: {validation_error}\n\n"
                        f"Invalid query:\n```cypher\n{cypher_query}\n```\n\n"
                        f"Please correct the query. Remember:\n"
                        f"1. Use only valid node labels like: {node_sample}\n"
                        f"2. Use only valid relationship types like: {rel_sample}\n"
                        f"3. Pay attention to relationship directions\n"
                        f"4. Include Citation nodes with HAS_SOURCE relationships\n\n"
                        f"Generate a new, corrected query."
                    )
                    
                    feedback_message = Message(
                        role=MessageRole.USER,
                        content=feedback_content
                    )
                    
                    # Add feedback to conversations
                    conversation.append(feedback_message)
                    self._last_conversation.append(feedback_message)
        
        # If ICL approach failed after max attempts, try two-step
        if not is_valid:
            logger.info(f"ICL approach failed after {icl_attempts} attempts, falling back to two-step approach")
            
            # Process with two-step agent
            two_step_response, _ = await self.two_step_agent.process(message)
            
            # Extract query from response
            cypher_query = two_step_response.metadata.get("query", "")
            final_response = two_step_response
            
            # Store the two-step response in our conversation history
            self._last_conversation.append(two_step_response)
            
            # Validate the two-step query
            is_valid, validation_error = self._validate_query(
                cypher_query, valid_node_labels, valid_rel_types
            )
            
            if not is_valid:
                logger.warning(f"Invalid query from two-step approach: {validation_error}")
                # Use a safe fallback query if both approaches fail
                cypher_query = 'MATCH (d:Disease {name: "Dengue Fever"}) RETURN d.name, d.description LIMIT 5'
        
        # Create response with the final query if not already created
        if not final_response:
            # Create a fallback response
            response_message = Message(
                role=MessageRole.ASSISTANT,
                content=json.dumps({
                    "query": cypher_query,
                    "approach": "fallback",
                    "attempts": icl_attempts
                }, indent=2),
                metadata={
                    "query": cypher_query,
                    "query_type": "cypher",
                    "approach": "fallback",
                    "attempts": icl_attempts,
                    "timestamp": self._get_timestamp()
                }
            )
            
            # Add to conversation history
            self._last_conversation.append(response_message)
        else:
            # Use the generated response but ensure metadata is updated
            approach = "icl" if is_valid and icl_attempts < self.max_icl_attempts else "two_step"
            
            response_message = Message(
                role=final_response.role,
                content=final_response.content,
                metadata={
                    **final_response.metadata,
                    "query": cypher_query,
                    "query_type": "cypher",
                    "approach": approach,
                    "attempts": icl_attempts,
                    "timestamp": self._get_timestamp()
                }
            )
        
        return response_message, "next"

async def test_production_query(query_index: int = 0):
    """Test the production HybridQueryWriterAgent with a specific query"""
    query = TEST_QUERIES[query_index]
    logger.info(f"Testing production query: {query}")
    
    # Initialize the HybridQueryWriterAgent
    agent_config = {
        "agent_id": "test_hybrid_query_writer_agent",
        "class_name": "HybridQueryWriterAgent",
        "model_config": {
            "model_type": "instruct",
            "temperature": 0.1,
            "max_tokens": 1024
        },
        "max_icl_attempts": 3  # Allow up to 3 attempts before fallback
    }
    
    agent = ConversationTrackingAgent(
        agent_id="test_hybrid_query_writer_agent", 
        config=agent_config
    )
    
    # Create a message from the query
    message = Message(
        role=MessageRole.USER,
        content=query
    )
    
    # Process the message
    response_message, next_agent = await agent.process(message)
    
    # Extract the query information
    query_data = {}
    try:
        query_data = json.loads(response_message.content)
    except json.JSONDecodeError:
        logger.warning(f"Could not parse response content as JSON: {response_message.content}")
    
    # Get key information from response
    generated_query = response_message.metadata.get("query", "No query generated")
    approach = response_message.metadata.get("approach", "unknown")
    attempts = response_message.metadata.get("attempts", 0)
    
    logger.info(f"Generated query using {approach} approach after {attempts} attempts:")
    logger.info(f"{generated_query}")
    
    # Create the result dictionary
    result = {
        "query": query,
        "generated_query": generated_query,
        "approach": approach,
        "attempts": attempts
    }
    
    # Save results to a file
    output_file = os.path.join(project_root, f"production_query_results_{query_index}.md")
    with open(output_file, "w") as f:
        f.write("# Production Query Generation Test Results\n\n")
        
        f.write(f"## Query: {result['query']}\n\n")
        f.write(f"**Approach Used:** {result['approach']}\n\n")
        f.write(f"**Attempts Required:** {result['attempts']}\n\n")
        f.write("**Generated Cypher Query:**\n\n")
        f.write("```cypher\n")
        
        # Clean up the query by replacing escaped quotes and newlines
        clean_query = result.get('generated_query', 'No query generated')
        clean_query = clean_query.replace('\\"', '"').replace('\\n', '\n')
        
        # If RETURN clause is incomplete, try to extract a more complete query from metadata
        if clean_query.strip().endswith('RETURN'):
            # Check if we can get more complete query from agent's last response
            if agent._last_conversation and len(agent._last_conversation) >= 2:
                last_response = agent._last_conversation[-1]
                if "query" in last_response.metadata:
                    complete_query = last_response.metadata["query"]
                    complete_query = complete_query.replace('\\"', '"').replace('\\n', '\n')
                    clean_query = complete_query
        
        f.write(clean_query)
        f.write("\n```\n\n")
        
        # Add the full conversation exchange
        f.write("## Conversation Exchange\n\n")
        
        # Get the messages from the agent's conversation
        conversation = getattr(agent, '_last_conversation', [])
        if not conversation:
            f.write("*No conversation recorded*\n\n")
        else:
            for i, msg in enumerate(conversation):
                if msg.role == MessageRole.USER:
                    if i == 0:
                        f.write("### 👤 User Query\n\n")
                    else:
                        f.write(f"### 👤 System Feedback (Attempt {i//2})\n\n")
                    f.write(f"{msg.content}\n\n")
                else:  # ASSISTANT
                    f.write(f"### 🤖 Assistant Response (Attempt {i//2 + 1})\n\n")
                    
                    # Try to extract and format JSON content
                    try:
                        content_json = json.loads(msg.content)
                        f.write("**Response JSON:**\n\n")
                        f.write("```json\n")
                        f.write(json.dumps(content_json, indent=2))
                        f.write("\n```\n\n")
                    except:
                        f.write(f"{msg.content}\n\n")
                    
                    # Show the query if available in metadata
                    if "query" in msg.metadata:
                        f.write("**Generated Query:**\n\n")
                        f.write("```cypher\n")
                        # Clean up the query by replacing escaped quotes and newlines
                        query = msg.metadata["query"].replace('\\"', '"').replace('\\n', '\n')
                        f.write(query)
                        f.write("\n```\n\n")
                    
                    f.write("---\n\n")
        
    logger.info(f"Results saved to {output_file}")
    
    return result

async def run_tests():
    """Run tests for all queries in sequence"""
    results = []
    
    for i, query in enumerate(TEST_QUERIES):
        try:
            result = await test_production_query(i)
            results.append(result)
            logger.info(f"Test for query {i+1} completed successfully")
            logger.info("-" * 80)
        except Exception as e:
            logger.error(f"Error testing query {i+1}: {str(e)}")
    
    logger.info("All tests completed")
    
    return results

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run a specific test by index
        try:
            index = int(sys.argv[1])
            if 0 <= index < len(TEST_QUERIES):
                asyncio.run(test_production_query(index))
            else:
                logger.error(f"Invalid query index. Must be between 0 and {len(TEST_QUERIES)-1}")
        except ValueError:
            logger.error("Please provide a valid integer index")
    else:
        # Run all tests in sequence
        asyncio.run(run_tests())
