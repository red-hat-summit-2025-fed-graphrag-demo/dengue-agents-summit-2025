#!/usr/bin/env python
"""
Simple verification script to check that the CypherTool can be imported properly.

This script tries to import the CypherTool class and instantiate it,
which helps identify any import issues.

Usage:
    python verify_cypher_import.py
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    """Verify that the CypherTool can be imported properly."""
    # Show the current working directory
    logger.info(f"Current directory: {os.getcwd()}")
    
    # Show the Python path
    logger.info(f"Python path: {sys.path}")
    
    try:
        # Attempt relative import (from the 'src' directory)
        logger.info("Attempting to import CypherTool with relative import...")
        from tools import CypherTool
        logger.info("✅ Relative import successful!")
        
        # Try to create an instance
        cypher_tool = CypherTool(api_url="http://example.com/api")
        logger.info(f"✅ Successfully created CypherTool instance with endpoint: {cypher_tool.query_endpoint}")
        
    except ImportError as e:
        logger.error(f"❌ Relative import failed: {str(e)}")
        
        try:
            # Attempt absolute import (with 'src' prefix)
            logger.info("Attempting to import CypherTool with absolute import...")
            from src.tools import CypherTool
            logger.info("✅ Absolute import successful!")
            
            # Try to create an instance
            cypher_tool = CypherTool(api_url="http://example.com/api")
            logger.info(f"✅ Successfully created CypherTool instance with endpoint: {cypher_tool.query_endpoint}")
            
        except ImportError as e:
            logger.error(f"❌ Absolute import failed: {str(e)}")
            sys.exit(1)
    
    logger.info("\nSUMMARY:")
    logger.info("✅ CypherTool import verification completed successfully!")

if __name__ == "__main__":
    main()
