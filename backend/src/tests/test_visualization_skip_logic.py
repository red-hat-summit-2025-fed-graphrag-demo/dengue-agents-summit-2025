"""
Test for the visualization skip logic in the output combiner agent.

This test verifies that the output combiner agent correctly determines
when visualization data is needed based on query content.
"""
import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Add the project root to the Python path
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from src.agent_system.rag_system.output_combiner_agent import OutputCombinerAgent
from src.agent_system.core.message import Message, MessageRole

# Set up output directory for saving test results
logs_dir = Path("/Users/wesjackson/Code/Summit2025/dengue-agents-summit-2025/backend/logs/workflow_tests")
os.makedirs(logs_dir, exist_ok=True)

# Configure logging with timestamp for unique filenames
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = logs_dir / f"visualization_skip_logic_test_{timestamp}.log"
results_file = logs_dir / f"visualization_skip_logic_results_{timestamp}.json"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("visualization_skip_test")

# Test queries with expected visualization needs
TEST_CASES = [
    # Format: (query, should_need_visualization, reason)
    (
        "What are the symptoms of dengue fever?", 
        False, 
        "Basic information query without time/data components"
    ),
    (
        "How is dengue fever treated?", 
        False, 
        "Treatment query without time/data components"
    ),
    (
        "What are the dengue fever trends in Brazil over the last 5 years?", 
        True, 
        "Contains data keywords and time period"
    ),
    (
        "I'm traveling to Thailand in July, what's the risk of dengue fever?", 
        True, 
        "Contains travel context and time period"
    ),
    (
        "Are there statistics on dengue cases in Singapore?", 
        True, 
        "Explicitly requests statistics"
    ),
    (
        "What is the forecast for dengue in Saudi Arabia this September?", 
        True, 
        "Contains forecast request and time period"
    ),
    (
        "Compare dengue prevalence in urban versus rural areas.", 
        True, 
        "Requests comparison of data"
    ),
    (
        "What precautions should I take against dengue?", 
        False, 
        "General precaution query without data components"
    ),
    (
        "I have a patient living in New York who plans travel to Saudi Arabia in September of this year. This patient has had dengue fever in the last 3 years. What advice should I give him regarding his trip?",
        True,
        "Travel query with time period and location"
    ),
    (
        "What causes dengue hemorrhagic fever?",
        False,
        "Medical causation query without data components"
    ),
]

async def run_visualization_need_test() -> List[Dict[str, Any]]:
    """
    Test the visualization need detection function.
    
    Returns:
        List of test results
    """
    logger.info("Initializing OutputCombinerAgent for visualization need testing")
    
    # Initialize with minimal configuration
    agent_id = "rag_output_combiner_agent"
    config = {
        "model_config": {
            "temperature": 0.1,
            "model_type": "instruct"
        }
    }
    
    # Initialize the agent
    output_combiner = OutputCombinerAgent(agent_id, config)
    
    # Test results
    results = []
    
    for query, expected_need, reason in TEST_CASES:
        # Test the visualization need detection
        needs_visualization, analysis_reason = await output_combiner._analyze_visualization_need(query)
        
        # Check if the result matches expectations
        matches_expectation = needs_visualization == expected_need
        
        # Log the result
        logger.info(f"Query: '{query[:50]}...'")
        logger.info(f"Expected visualization need: {expected_need} ({reason})")
        logger.info(f"Actual visualization need: {needs_visualization} ({analysis_reason})")
        logger.info(f"Test result: {'PASS' if matches_expectation else 'FAIL'}")
        logger.info("---")
        
        # Store the result
        results.append({
            "query": query,
            "expected_need": expected_need,
            "expected_reason": reason,
            "actual_need": needs_visualization,
            "actual_reason": analysis_reason,
            "passed": matches_expectation
        })
    
    # Calculate overall success rate
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    success_rate = (passed_count / total_count) * 100 if total_count > 0 else 0
    
    logger.info(f"Overall success rate: {success_rate:.1f}% ({passed_count}/{total_count} tests passed)")
    
    # Save detailed results to file
    with open(logs_dir / f"visualization_need_results_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)
        
    logger.info(f"Detailed visualization need results saved to {logs_dir / f'visualization_need_results_{timestamp}.json'}")
    
    return results

async def test_with_dummy_message() -> Dict[str, Any]:
    """
    Test the entire _execute_processing method with visualization skip logic.
    
    Returns:
        Test result dictionary
    """
    logger.info("Testing _execute_processing with visualization skip logic")
    
    # Initialize with minimal configuration
    agent_id = "rag_output_combiner_agent"
    config = {
        "model_config": {
            "temperature": 0.1,
            "model_type": "instruct"
        }
    }
    
    # Initialize the agent
    output_combiner = OutputCombinerAgent(agent_id, config)
    
    # Create test cases with different query types and visualization data
    test_cases = [
        {
            "name": "Query needs visualization - with visualization data",
            "query": "What are the dengue fever trends in Brazil over the last 5 years?",
            "visualization_data": {
                "countries": ["Brazil"],
                "analysis": {
                    "summaries": [
                        {
                            "country": "Brazil",
                            "summary_text": "Brazil has seen a 20% increase in dengue cases over the last 5 years."
                        }
                    ]
                }
            },
            "response_content": "Dengue fever in Brazil has been a significant public health concern.",
            "should_include_visualization": True
        },
        {
            "name": "Query doesn't need visualization - with visualization data",
            "query": "What are the symptoms of dengue fever?",
            "visualization_data": {
                "countries": ["Global"],
                "analysis": {
                    "summaries": [
                        {
                            "country": "Global",
                            "summary_text": "Global dengue cases have remained stable in recent years."
                        }
                    ]
                }
            },
            "response_content": "The symptoms of dengue fever include high fever, severe headache, and joint pain.",
            "should_include_visualization": False
        }
    ]
    
    results = []
    
    for case in test_cases:
        # Create a test message
        metadata = {
            "original_query": case["query"],
            "visualization_data": case["visualization_data"],
            "response_generator_output": case["response_content"]
        }
        
        message = Message(
            role=MessageRole.USER,
            content=case["response_content"],
            metadata=metadata
        )
        
        # Process the message
        response_message, _ = await output_combiner._execute_processing(message)
        
        # Check if visualization was included based on content
        visualization_included = "Dengue Data Visualization" in response_message.content
        matches_expectation = visualization_included == case["should_include_visualization"]
        
        logger.info(f"Test case: {case['name']}")
        logger.info(f"Query: '{case['query'][:50]}...'")
        logger.info(f"Should include visualization: {case['should_include_visualization']}")
        logger.info(f"Actually included visualization: {visualization_included}")
        logger.info(f"Test result: {'PASS' if matches_expectation else 'FAIL'}")
        logger.info("---")
        
        # Store the result
        results.append({
            "name": case["name"],
            "query": case["query"],
            "should_include_visualization": case["should_include_visualization"],
            "visualization_included": visualization_included,
            "passed": matches_expectation,
            "response_length": len(response_message.content),
            "response_preview": response_message.content[:100] + "..."
        })
    
    # Calculate overall success rate
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    success_rate = (passed_count / total_count) * 100 if total_count > 0 else 0
    
    logger.info(f"Overall success rate: {success_rate:.1f}% ({passed_count}/{total_count} tests passed)")
    
    # Save detailed processing results to file
    with open(logs_dir / f"processing_results_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)
        
    logger.info(f"Detailed processing results saved to {logs_dir / f'processing_results_{timestamp}.json'}")
    
    return {
        "results": results,
        "success_rate": success_rate
    }

async def main():
    """Run the visualization skip logic tests."""
    print("Starting visualization skip logic tests...")
    print(f"Log file: {log_file}")
    print(f"Results will be saved to: {logs_dir}")
    
    all_results = {}
    
    # Test the visualization need detection function
    need_test_results = await run_visualization_need_test()
    all_results["visualization_need_tests"] = need_test_results
    
    # Test with dummy messages
    process_test_results = await test_with_dummy_message()
    all_results["processing_tests"] = process_test_results
    
    # Save combined results
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)
    
    print("\nTests completed!")
    print(f"Full results saved to: {results_file}")
    
    # Print summary
    need_passed = sum(1 for r in need_test_results if r["passed"])
    need_total = len(need_test_results)
    
    process_passed = sum(1 for r in process_test_results["results"] if r["passed"])
    process_total = len(process_test_results["results"])
    
    total_passed = need_passed + process_passed
    total_tests = need_total + process_total
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": total_tests,
        "total_passed": total_passed,
        "success_rate": (total_passed/total_tests)*100 if total_tests > 0 else 0,
        "visualization_need_tests": {
            "total": need_total,
            "passed": need_passed,
            "success_rate": (need_passed/need_total)*100 if need_total > 0 else 0
        },
        "processing_tests": {
            "total": process_total,
            "passed": process_passed,
            "success_rate": (process_passed/process_total)*100 if process_total > 0 else 0
        }
    }
    
    # Save summary to a separate file
    with open(logs_dir / f"visualization_skip_summary_{timestamp}.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nOverall test results: {total_passed}/{total_tests} tests passed ({(total_passed/total_tests)*100:.1f}%)")
    print("- Visualization need detection: " +
          f"{need_passed}/{need_total} passed ({(need_passed/need_total)*100:.1f}%)")
    print("- Processing with skip logic: " +
          f"{process_passed}/{process_total} passed ({(process_passed/process_total)*100:.1f}%)")
    print(f"\nSummary saved to: {logs_dir / f'visualization_skip_summary_{timestamp}.json'}")

if __name__ == "__main__":
    asyncio.run(main())
