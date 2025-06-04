#!/usr/bin/env python
"""
Simplified test runner script.

This script runs the minimal set of tests to validate that the tools
can successfully connect to the Neo4j database and execute queries.

Usage:
    python run_all_tests.py
"""
import os
import sys
import time
import subprocess
from typing import Tuple, List

# Add color support if available
try:
    import colorama
    colorama.init()
    GREEN = colorama.Fore.GREEN
    RED = colorama.Fore.RED
    YELLOW = colorama.Fore.YELLOW
    BLUE = colorama.Fore.BLUE
    RESET = colorama.Style.RESET_ALL
except ImportError:
    GREEN = ""
    RED = ""
    YELLOW = ""
    BLUE = ""
    RESET = ""

def run_test_script(script_name: str, args: List[str] = None) -> Tuple[bool, str]:
    """
    Run a test script as a subprocess.
    
    Args:
        script_name: Name of the script to run
        args: Optional list of arguments to pass to the script
        
    Returns:
        Tuple of (success, output)
    """
    print(f"{BLUE}Running: {script_name} {' '.join(args or [])}{RESET}")
    
    try:
        # Get the absolute path to the script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(current_dir, script_name)
        
        # Set up the environment with the correct Python path
        env = os.environ.copy()
        src_dir = os.path.abspath(os.path.join(current_dir, ".."))
        backend_dir = os.path.abspath(os.path.join(src_dir, ".."))
        project_dir = os.path.abspath(os.path.join(backend_dir, ".."))
        
        python_path = os.pathsep.join([
            project_dir,
            backend_dir,
            src_dir,
            current_dir,
            env.get("PYTHONPATH", "")
        ])
        
        env["PYTHONPATH"] = python_path
        
        # Build the command
        cmd = [sys.executable, script_path] + (args or [])
        
        # Run the script and capture output
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,  # Don't raise exception on non-zero exit code
            env=env,
            cwd=current_dir  # Set the working directory to the test directory
        )
        
        # Check exit code
        success = result.returncode == 0
        return success, result.stdout
    
    except Exception as e:
        return False, str(e)

def run_test_suite():
    """Run the simplified test suite."""
    print("\n" + "=" * 70)
    print(" SIMPLIFIED TOOL TEST SUITE ".center(70, "="))
    print("=" * 70)
    
    start_time = time.time()
    test_results = {}
    
    try:
        # 1. Test Cypher tool
        print(f"\n{BLUE}🔧 Testing Cypher tool...{RESET}")
        cypher_tool_success, cypher_tool_output = run_test_script("test_cypher_tool_fix.py")
        test_results["cypher_tool"] = cypher_tool_success
        
        if not cypher_tool_success:
            print(f"{RED}❌ Cypher tool tests failed.{RESET}")
            print(f"{YELLOW}   Run 'python test_cypher_tool_fix.py' for detailed information.{RESET}")
            
        # 2. Test Schema tool
        print(f"\n{BLUE}🔧 Testing Schema tool...{RESET}")
        schema_tool_success, schema_tool_output = run_test_script("test_schema_tool.py")
        test_results["schema_tool"] = schema_tool_success
        
        if not schema_tool_success:
            print(f"{RED}❌ Schema tool tests failed.{RESET}")
            print(f"{YELLOW}   Run 'python test_schema_tool.py' for detailed information.{RESET}")
        
        # 3. Test Citation functionality
        print(f"\n{BLUE}📚 Testing Citation functionality...{RESET}")
        citation_success, citation_output = run_test_script("test_cypher_citations.py")
        test_results["citations"] = citation_success
        
        if not citation_success:
            print(f"{RED}❌ Citation functionality tests failed.{RESET}")
            print(f"{YELLOW}   Run 'python test_cypher_citations.py' for detailed information.{RESET}")
        
        # All tests completed
        return all(test_results.values())
        
    except Exception as e:
        print(f"{RED}❌ Error running tests: {e}{RESET}")
        return False
    finally:
        # Print summary
        end_time = time.time()
        total_time = end_time - start_time
        
        print("\n" + "=" * 70)
        print(" TEST SUMMARY ".center(70, "="))
        print("=" * 70)
        
        for test_name, result in test_results.items():
            status = f"{GREEN}✅ PASS{RESET}" if result else f"{RED}❌ FAIL{RESET}"
            print(f"{test_name.capitalize().ljust(20)} {status}")
        
        print("-" * 70)
        print(f"Total time: {total_time:.2f} seconds")
        print("=" * 70)


def main():
    """Entry point for the script."""
    success = run_test_suite()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()