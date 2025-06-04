"""
Test Registry Implementations

Unit tests for the BaseRegistry class and its concrete implementations.
"""
import os
import json
import unittest
import tempfile
import yaml
import shutil
from typing import Dict, Any, List

import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.registries.base_registry import BaseRegistry
from src.registries.tool_registry import ToolRegistry
from src.registries.agent_registry import AgentRegistry
from src.registries.prompt_registry import PromptRegistry
from src.registries.registry_validator import (
    ToolRegistryValidator,
    AgentRegistryValidator,
    PromptRegistryValidator
)

class MockRegistry(BaseRegistry):
    """Mock implementation of BaseRegistry for testing."""
    
    def __init__(self, registry_path: str = None, base_dir: str = None):
        """Initialize the mock registry."""
        self.mock_items = {}
        super().__init__(registry_path, base_dir)
    
    def _get_default_base_dir(self) -> str:
        """Get the default base directory."""
        return "mock"
    
    def _get_default_registry_path(self) -> str:
        """Get the default registry file path."""
        return os.path.join(self.base_dir, "registry.json")
    
    def _get_validator(self):
        """Get the validator for this registry type."""
        return ToolRegistryValidator()  # Using tool validator for mock tests
    
    def _load_registry(self) -> None:
        """Load the registry (mock implementation)."""
        self._registry_items = self.mock_items
    
    def set_mock_items(self, items: Dict[str, Dict[str, Any]]) -> None:
        """Set the mock items for testing."""
        self.mock_items = items
        self._registry_items = items

class TestBaseRegistry(unittest.TestCase):
    """Test the BaseRegistry abstract class functionality."""
    
    def setUp(self):
        """Set up the test case."""
        self.temp_dir = tempfile.mkdtemp()
        self.registry_path = os.path.join(self.temp_dir, "registry.json")
        
        # Create a valid test item
        self.valid_item = {
            "id": "test_item",
            "name": "Test Item",
            "description": "Test description",
            "active": True,
            "module_path": "test.module",
            "class_name": "TestClass",
            "config_path": "test/config.yaml",
            "allowed_agents": ["*"]
        }
        
        # Initialize the mock registry
        self.registry = MockRegistry(registry_path=self.registry_path, base_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up after the test case."""
        shutil.rmtree(self.temp_dir)
    
    def test_get_item(self):
        """Test getting items from the registry."""
        # Set up mock items
        self.registry.set_mock_items({
            "item1": {"id": "item1", "name": "Item 1"},
            "item2": {"id": "item2", "name": "Item 2"}
        })
        
        # Test getting an existing item
        item = self.registry.get_item("item1")
        self.assertEqual(item["id"], "item1")
        self.assertEqual(item["name"], "Item 1")
        
        # Test getting a non-existent item
        with self.assertRaises(ValueError):
            self.registry.get_item("nonexistent")
    
    def test_list_items(self):
        """Test listing items from the registry."""
        # Set up mock items
        self.registry.set_mock_items({
            "item1": {"id": "item1", "name": "Item 1", "active": True},
            "item2": {"id": "item2", "name": "Item 2", "active": False}
        })
        
        # Test listing all items
        items = self.registry.list_items()
        self.assertEqual(len(items), 2)
        
        # Test listing with filter
        active_items = self.registry.list_items(
            filter_func=lambda item: item.get("active", False)
        )
        self.assertEqual(len(active_items), 1)
        self.assertEqual(active_items[0]["id"], "item1")
    
    def test_validate_item(self):
        """Test validating registry items."""
        # Test validating a valid item
        is_valid = self.registry.validate_item(self.valid_item)
        self.assertTrue(is_valid)
        
        # Test validating an invalid item
        invalid_item = {
            "id": "test_item",
            "name": "Test Item",
            "description": "Test description",
            "active": True,
            # Missing required fields
        }
        is_valid = self.registry.validate_item(invalid_item)
        self.assertFalse(is_valid)
    
    def test_register_item(self):
        """Test registering new items."""
        # Register a valid item
        item_id = self.registry.register_item(self.valid_item)
        self.assertEqual(item_id, "test_item")
        
        # Verify the item was added
        self.assertIn("test_item", self.registry._registry_items)
        
        # Try to register an invalid item
        invalid_item = {
            "id": "invalid_item",
            "name": "Invalid Item",
            "description": "Invalid description",
            "active": True,
            # Missing required fields
        }
        with self.assertRaises(ValueError):
            self.registry.register_item(invalid_item)
    
    def test_unregister_item(self):
        """Test unregistering items."""
        # Set up mock items
        self.registry.set_mock_items({
            "item1": {"id": "item1", "name": "Item 1"},
            "item2": {"id": "item2", "name": "Item 2"}
        })
        
        # Unregister an item
        self.registry.unregister_item("item1")
        
        # Verify the item was removed
        self.assertNotIn("item1", self.registry._registry_items)
        self.assertIn("item2", self.registry._registry_items)
        
        # Try to unregister a non-existent item
        with self.assertRaises(ValueError):
            self.registry.unregister_item("nonexistent")
    
    def test_reload(self):
        """Test reloading the registry."""
        # Set up mock items
        self.registry.set_mock_items({
            "item1": {"id": "item1", "name": "Item 1"},
            "item2": {"id": "item2", "name": "Item 2"}
        })
        
        # Modify the items
        self.registry._registry_items = {
            "item3": {"id": "item3", "name": "Item 3"}
        }
        
        # Reload the registry
        self.registry.reload()
        
        # Verify the items were reloaded from the mock source
        self.assertIn("item1", self.registry._registry_items)
        self.assertIn("item2", self.registry._registry_items)
        self.assertNotIn("item3", self.registry._registry_items)

class TestToolRegistry(unittest.TestCase):
    """Test the ToolRegistry implementation."""
    
    def setUp(self):
        """Set up the test case."""
        self.temp_dir = tempfile.mkdtemp()
        self.registry_path = os.path.join(self.temp_dir, "registry.json")
        
        # Create a registry file with test tools
        test_tools = {
            "tools": [
                {
                    "id": "test_tool",
                    "name": "Test Tool",
                    "description": "Test tool description",
                    "version": "1.0.0",
                    "tags": ["test", "tool"],
                    "created_at": "2025-05-14",
                    "updated_at": "2025-05-14",
                    "author": "Test Author",
                    "active": True,
                    "module_path": "src.tools.test_tool",
                    "class_name": "TestTool",
                    "config_path": "configs/test_tool.yaml",
                    "allowed_agents": ["*"]
                }
            ]
        }
        
        with open(self.registry_path, "w") as f:
            json.dump(test_tools, f)
        
        # Initialize the tool registry
        self.registry = ToolRegistry(registry_path=self.registry_path)
    
    def tearDown(self):
        """Clean up after the test case."""
        shutil.rmtree(self.temp_dir)
    
    def test_get_validator(self):
        """Test getting the validator for the tool registry."""
        validator = self.registry._get_validator()
        self.assertIsInstance(validator, ToolRegistryValidator)
    
    def test_load_tool_registry(self):
        """Test loading the tool registry from a file."""
        # The registry should have loaded the test tool
        tools = self.registry.list_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["id"], "test_tool")
    
    def test_get_tool_config(self):
        """Test getting a tool configuration."""
        # Get the test tool
        tool_config = self.registry.get_tool_config("test_tool")
        self.assertEqual(tool_config["name"], "Test Tool")
        self.assertEqual(tool_config["module_path"], "src.tools.test_tool")
        
        # Try to get a non-existent tool
        with self.assertRaises(ValueError):
            self.registry.get_tool_config("nonexistent_tool")
    
    def test_register_tool(self):
        """Test registering a new tool."""
        # Create a new tool
        new_tool = {
            "id": "new_tool",
            "name": "New Tool",
            "description": "New tool description",
            "version": "1.0.0",
            "tags": ["new", "tool"],
            "created_at": "2025-05-14",
            "updated_at": "2025-05-14",
            "author": "Test Author",
            "active": True,
            "module_path": "src.tools.new_tool",
            "class_name": "NewTool",
            "config_path": "configs/new_tool.yaml",
            "allowed_agents": ["test_agent"]
        }
        
        # Register the tool
        self.registry.register_tool(new_tool)
        
        # Verify the tool was added
        tools = self.registry.list_tools()
        self.assertEqual(len(tools), 2)
        self.assertIn("new_tool", [tool["id"] for tool in tools])

class TestAgentRegistry(unittest.TestCase):
    """Test the AgentRegistry implementation."""
    
    def setUp(self):
        """Set up the test case."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.temp_dir, "agents")
        os.makedirs(self.base_dir, exist_ok=True)
        
        self.registry_path = os.path.join(self.base_dir, "registry.json")
        
        # Create a registry file with test agents
        test_agents = {
            "agents": [
                {
                    "id": "test_agent",
                    "name": "Test Agent",
                    "description": "Test agent description",
                    "version": "1.0.0",
                    "tags": ["test", "agent"],
                    "created_at": "2025-05-14",
                    "updated_at": "2025-05-14",
                    "author": "Test Author",
                    "active": True,
                    "module_path": "src.agent_system.test_agent",
                    "class_name": "TestAgent",
                    "config_path": "configs/test_agent.yaml",
                    "prompt_id": "test.prompt",
                    "model_config": {
                        "model_type": "instruct",
                        "max_tokens": 1024,
                        "temperature": 0.7
                    }
                }
            ]
        }
        
        with open(self.registry_path, "w") as f:
            json.dump(test_agents, f)
        
        # Initialize the agent registry
        self.registry = AgentRegistry(registry_path=self.registry_path, base_dir=self.base_dir)
    
    def tearDown(self):
        """Clean up after the test case."""
        shutil.rmtree(self.temp_dir)
    
    def test_get_validator(self):
        """Test getting the validator for the agent registry."""
        validator = self.registry._get_validator()
        self.assertIsInstance(validator, AgentRegistryValidator)
    
    def test_load_agent_registry(self):
        """Test loading the agent registry from a file."""
        # The registry should have loaded the test agent
        agents = self.registry.list_agents()
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0]["id"], "test_agent")
    
    def test_get_agent_config(self):
        """Test getting an agent configuration."""
        # Get the test agent
        agent_config = self.registry.get_agent_config("test_agent")
        self.assertEqual(agent_config["name"], "Test Agent")
        self.assertEqual(agent_config["module_path"], "src.agent_system.test_agent")
        
        # Try to get a non-existent agent
        with self.assertRaises(ValueError):
            self.registry.get_agent_config("nonexistent_agent")
    
    def test_register_agent(self):
        """Test registering a new agent."""
        # Create a new agent
        new_agent = {
            "id": "new_agent",
            "name": "New Agent",
            "description": "New agent description",
            "version": "1.0.0",
            "tags": ["new", "agent"],
            "created_at": "2025-05-14",
            "updated_at": "2025-05-14",
            "author": "Test Author",
            "active": True,
            "module_path": "src.agent_system.new_agent",
            "class_name": "NewAgent",
            "config_path": "configs/new_agent.yaml",
            "prompt_id": "test.prompt",
            "model_config": {
                "model_type": "instruct",
                "max_tokens": 1024,
                "temperature": 0.7
            }
        }
        
        # Register the agent
        self.registry.register_agent(new_agent)
        
        # Verify the agent was added
        agents = self.registry.list_agents()
        self.assertEqual(len(agents), 2)
        self.assertIn("new_agent", [agent["id"] for agent in agents])

class TestPromptRegistry(unittest.TestCase):
    """Test the PromptRegistry implementation."""
    
    def setUp(self):
        """Set up the test case."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.temp_dir, "prompts")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create test prompt files
        test_prompt = {
            "id": "test.prompt",
            "name": "Test Prompt",
            "description": "Test prompt description",
            "version": "1.0.0",
            "tags": ["test", "prompt"],
            "created_at": "2025-05-14",
            "updated_at": "2025-05-14",
            "author": "Test Author",
            "active": True,
            "models": ["test-model"],
            "prompt": "This is a test prompt template with {{variable}}."
        }
        
        with open(os.path.join(self.base_dir, "test_prompt.yaml"), "w") as f:
            yaml.dump(test_prompt, f)
        
        # Initialize the prompt registry
        self.registry = PromptRegistry(base_dir=self.base_dir)
    
    def tearDown(self):
        """Clean up after the test case."""
        shutil.rmtree(self.temp_dir)
    
    def test_get_validator(self):
        """Test getting the validator for the prompt registry."""
        validator = self.registry._get_validator()
        self.assertIsInstance(validator, PromptRegistryValidator)
    
    def test_load_prompt_registry(self):
        """Test loading the prompt registry from files."""
        # The registry should have loaded the test prompt
        prompts = self.registry.list_prompts()
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0]["id"], "test.prompt")
    
    def test_get_prompt(self):
        """Test getting a prompt with variable substitution."""
        # Get the test prompt with variable
        prompt = self.registry.get_prompt("test.prompt", variable="value")
        self.assertEqual(prompt, "This is a test prompt template with value.")
        
        # Try to get a non-existent prompt
        with self.assertRaises(ValueError):
            self.registry.get_prompt("nonexistent.prompt")
    
    def test_get_prompt_metadata(self):
        """Test getting prompt metadata."""
        # Get the test prompt metadata
        metadata = self.registry.get_prompt_metadata("test.prompt")
        self.assertEqual(metadata["name"], "Test Prompt")
        self.assertNotIn("prompt", metadata)
    
    def test_register_prompt(self):
        """Test registering a new prompt."""
        # Create a new prompt
        new_prompt_id = "new.prompt"
        new_prompt_text = "This is a new prompt template."
        new_prompt_metadata = {
            "name": "New Prompt",
            "description": "New prompt description",
            "version": "1.0.0",
            "tags": ["new", "prompt"],
            "created_at": "2025-05-14",
            "updated_at": "2025-05-14",
            "author": "Test Author",
            "active": True,
            "models": ["test-model"]
        }
        
        # Register the prompt
        self.registry.register_prompt(new_prompt_id, new_prompt_text, new_prompt_metadata)
        
        # Verify the prompt was added
        prompts = self.registry.list_prompts()
        self.assertEqual(len(prompts), 2)
        self.assertIn(new_prompt_id, [prompt["id"] for prompt in prompts])
        
        # Verify the prompt text was saved
        prompt = self.registry.get_prompt(new_prompt_id)
        self.assertEqual(prompt, new_prompt_text)

if __name__ == '__main__':
    unittest.main()
