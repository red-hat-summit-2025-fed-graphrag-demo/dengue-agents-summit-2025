"""
Simple API Workflow Test

This script tests the GraphRAG workflow through the standard API endpoint,
just like a real application would use it. It sends a request through curl
to test the entire workflow in a production-like environment.
"""
import os
import sys
import json
import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

# Set up output directory for saving test results
output_dir = project_root / "logs" / "api_workflow_tests"
os.makedirs(output_dir, exist_ok=True)

# Configure logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = output_dir / f"api_workflow_test_{timestamp}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("api_workflow_test")

# Test cases with different queries to test visualization skip logic
TEST_CASES = [
    {
        "name": "travel_with_visualization",
        "query": "I have a patient living in New York who plans travel to Saudi Arabia in September of this year. This patient has had dengue fever in the last 3 years. What advice should I give him regarding his trip?",
        "should_visualize": True
    },
    {
        "name": "basic_query_no_visualization",
        "query": "What are the symptoms of dengue fever?",
        "should_visualize": False
    }
]

def make_curl_request(query, workflow_id="GRAPH_RAG_WORKFLOW"):
    """Make a curl request to the API endpoint."""
    logger.info(f"Making request with query: {query[:50]}...")
    
    # API endpoint
    api_host = os.environ.get("API_HOST", "localhost")
    api_port = os.environ.get("API_PORT", "8000")
    api_endpoint = f"http://{api_host}:{api_port}/api/chat"
    
    # Build request body
    request_body = {
        "query": query,
        "workflow_id": workflow_id
    }
    
    # Build curl command
    cmd = [
        "curl", "-X", "POST", api_endpoint,
        "-H", "Content-Type: application/json",
        "-d", json.dumps(request_body)
    ]
    
    # Execute curl command
    try:
        logger.info(f"Executing curl command")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Curl request failed: {stderr.decode()}")
            return None
        
        # Parse and return response
        response = json.loads(stdout.decode())
        logger.info(f"Received response with session ID: {response.get('session_id')}")
        
        # Save response to file
        result_file = output_dir / f"api_result_{timestamp}.json"
        with open(result_file, "w") as f:
            json.dump(response, f, indent=2)
        logger.info(f"Saved API response to {result_file}")
        
        return response
    
    except Exception as e:
        logger.error(f"Error making API request: {str(e)}")
        return None

def monitor_server_logs(timeout=60):
    """Monitor the server logs for output combiner agent information."""
    logger.info(f"Monitoring server logs for output combiner agent...")
    
    # Use grep to find output combiner agent logs
    cmd = [
        "grep", "-i", "output_combiner", 
        "/Users/wesjackson/Code/Summit2025/dengue-agents-summit-2025/backend/logs/api.log"
    ]
    
    start_time = time.time()
    combiner_logs = []
    
    while time.time() - start_time < timeout:
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if stdout:
                new_logs = stdout.decode().splitlines()
                for log in new_logs:
                    if log not in combiner_logs:
                        combiner_logs.append(log)
                        logger.info(f"Found new output combiner log: {log}")
            
            # Check if we have found logs indicating visualization analysis
            visualization_logs = [log for log in combiner_logs if "visualization_need" in log or "Visualization need analysis" in log]
            if visualization_logs:
                logger.info(f"Found visualization analysis logs: {len(visualization_logs)}")
                
                # Save all logs to file
                logs_file = output_dir / f"output_combiner_logs_{timestamp}.txt"
                with open(logs_file, "w") as f:
                    f.write("\n".join(combiner_logs))
                logger.info(f"Saved {len(combiner_logs)} logs to {logs_file}")
                
                return True
                
            # Wait a bit before checking again
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error monitoring logs: {str(e)}")
            break
    
    logger.warning(f"Timed out waiting for output combiner logs")
    return False

def run_test():
    """Run the API workflow test."""
    print(f"Starting API workflow test...")
    print(f"Log file: {log_file}")
    
    # Loop through test cases
    for test_case in TEST_CASES:
        test_name = test_case["name"]
        query = test_case["query"]
        expected_viz = test_case["should_visualize"]
        
        logger.info(f"Running test case: {test_name}")
        print(f"\nRunning test case: {test_name}")
        print(f"Query: {query[:50]}...")
        print(f"Expected visualization: {expected_viz}")
        
        # Make API request
        response = make_curl_request(query)
        if not response:
            logger.error(f"Test case {test_name} failed - no response")
            print(f"Test failed - no response from API")
            continue
        
        # Monitor logs for output combiner activity
        logger.info(f"Monitoring logs for output combiner activity")
        print(f"Monitoring logs for output combiner activity...")
        
        found_logs = monitor_server_logs(timeout=60)
        if found_logs:
            print(f"Successfully found output combiner logs")
        else:
            print(f"Warning: Could not find output combiner logs within timeout")
            
        # Add a delay between test cases
        print(f"Test case {test_name} completed")
        time.sleep(5)
    
    print("\nAll test cases completed!")
    print(f"Results saved to: {output_dir}")

if __name__ == "__main__":
    run_test()
