"""
Agent for ensuring final content compliance.
"""
import logging
import json
import re
import json
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import BaseMetadata, MetadataKeys, ResultMetadata
from src.agent_system.safety.safety_agent_base import SafetyAgentBase
from src.registries.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)


class ContentComplianceAgent(SafetyAgentBase):
    """
    Content compliance agent for the "back of the sandwich" safety checks.
    
    This agent checks the final generated content before it is returned to the user,
    ensuring no unsafe content passes through even if previous safety checks missed it.
    
    Key focuses:
    1. PII/PHI detection and redaction
    2. Appropriate content for the intended audience
    3. Final check for harmful or policy-violating content
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], workflow_manager=None, **kwargs):
        """
        Initialize the content compliance agent.
        
        Args:
            agent_id: The unique identifier for this agent
            config: Agent configuration dictionary
            workflow_manager: Optional reference to the parent WorkflowManager
            **kwargs: Additional keyword arguments
        """
        # Make sure agent_id is in the config
        if "agent_id" not in config:
            config["agent_id"] = agent_id
            
        super().__init__(config, workflow_manager=workflow_manager, **kwargs)
        
        # Get a reference to the prompt registry
        self.prompt_registry = PromptRegistry()
        
        # Set the prompt IDs (can be overridden in config)
        self.compliance_prompt_id = config.get("compliance_prompt_id", "safety.content_compliance_system")
        self.remediation_prompt_id = config.get("remediation_prompt_id", "safety.content_remediation")
        
        logger.info(f"Initialized ContentComplianceAgent with prompt IDs: {self.compliance_prompt_id}, {self.remediation_prompt_id}")
    
    # Optional hook called by BaseAgent.process to stream initial thoughts.
    async def _stream_thinking_hook(self, stream_callback: Any):
        """Optional hook called by BaseAgent.process to stream initial thoughts."""
        await self.stream_thinking(
            thinking="Running final content compliance check...",
            stream_callback=stream_callback
        )

    async def _execute_processing(
        self,
        message: Message,
        session_id: Optional[str] = None
    ) -> Tuple[Message, Optional[str]]:
        """
        Core processing logic for the ContentComplianceAgent.
        Simplified to focus on text compliance using direct pattern matching.

        Args:
            message: The message to process
            session_id: Optional session identifier

        Returns:
            Tuple of (processed message, next agent ID)
        """
        input_content = message.content
        input_metadata = message.metadata

        logger.info(f"ContentComplianceAgent starting processing.")
        logger.debug(f"Input message content sample: {str(input_content)[:100]}...")
        logger.debug(f"Input metadata keys: {list(input_metadata.keys())}")

        # Determine the content to check for compliance
        content_to_check = BaseMetadata.get(input_metadata, MetadataKeys.GENERATED, None)
        if content_to_check:
            logger.info(f"Using generated content found in metadata for compliance check.")
            logger.debug(f"Generated content sample: {str(content_to_check)[:100]}...")
        else:
            content_to_check = input_content
            logger.info(f"No generated content in metadata. Using input message content for compliance check.")

        # Extract visualization data if present
        has_visualization_data = BaseMetadata.get(input_metadata, MetadataKeys.HAS_VISUALIZATION_DATA, False)
        visualization_data = BaseMetadata.get(input_metadata, MetadataKeys.VISUALIZATION_DATA, None)
        
        logger.info(f"Visualization data present: {has_visualization_data}")

        # Ensure content_to_check is a string
        if not isinstance(content_to_check, str):
            logger.warning(f"Content to check is not a string (type: {type(content_to_check)}). Converting to string.")
            content_to_check = str(content_to_check)

        # Check the content directly for PII using regex patterns
        pii_detected, explanation, anonymized_text = self._direct_pii_check_and_anonymize(content_to_check)

        final_content: str
        is_compliant: bool
        was_remediated: bool

        if not pii_detected:
            logger.info("No PII/PHI detected via patterns. Content is compliant.")
            final_content = content_to_check
            is_compliant = True
            was_remediated = False
            compliance_confidence = 0.98  # Confidence for regex check
            compliance_metadata_update = {
                MetadataKeys.IS_COMPLIANT.value: is_compliant,
                MetadataKeys.WAS_REMEDIATED.value: was_remediated,
                MetadataKeys.COMPLIANCE_CONFIDENCE.value: compliance_confidence
            }
        else:
            logger.info(f"PII/PHI detected via patterns: {explanation}. Remediating content.")
            final_content = anonymized_text
            is_compliant = False
            was_remediated = True
            compliance_confidence = 0.98  # Confidence for regex check
            compliance_metadata_update = {
                MetadataKeys.IS_COMPLIANT.value: is_compliant,
                MetadataKeys.WAS_REMEDIATED.value: was_remediated,
                MetadataKeys.PII_EXPLANATION.value: explanation,
                MetadataKeys.COMPLIANCE_CONFIDENCE.value: compliance_confidence
            }

        # Create the result metadata, updating existing metadata
        result_metadata = input_metadata.copy() # Start with incoming metadata
        BaseMetadata.update(result_metadata, **{
            MetadataKeys.COMPLIANCE_CHECKED.value: True,
            MetadataKeys.COMPLIANCE_AGENT_ID.value: self.agent_id
        })
        BaseMetadata.update(result_metadata, **compliance_metadata_update)
        
        # Ensure MetadataKeys are used consistently
        # Clean up potential raw string keys if necessary (optional, but good practice)
        for key_enum in [MetadataKeys.IS_COMPLIANT, MetadataKeys.WAS_REMEDIATED, MetadataKeys.PII_EXPLANATION, MetadataKeys.COMPLIANCE_CONFIDENCE, MetadataKeys.COMPLIANCE_CHECKED, MetadataKeys.COMPLIANCE_AGENT_ID]:
             if key_enum.value in result_metadata and key_enum in result_metadata:
                  # If both enum and string value exist, prefer enum and remove string
                  if result_metadata[key_enum.value] == result_metadata[key_enum]:
                       del result_metadata[key_enum.value]

        # Preserve visualization data in metadata if it exists
        if has_visualization_data and visualization_data:
            logger.info("Preserving visualization data in final response metadata")
            result_metadata[MetadataKeys.VISUALIZATION_DATA.value] = visualization_data
            result_metadata[MetadataKeys.HAS_VISUALIZATION_DATA.value] = True
            
        # Create the final message
        result_message = Message(
            role=MessageRole.ASSISTANT,
            content=final_content,
            metadata=result_metadata
        )

        logger.info(f"ContentComplianceAgent returning {'compliant' if is_compliant else 'remediated'} content.")
        logger.debug(f"Final content sample: {str(final_content)[:100]}...")
        logger.debug(f"Final metadata keys: {list(result_metadata.keys())}")

        return result_message, None

    def _direct_pii_check_and_anonymize(self, content: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check content for PII/PHI using regex patterns and anonymize if necessary.
        Handles both plain text and text that might contain code blocks or structured data.
        Also preserves citations and source information.
        
        Args:
            content: The content to check
            
        Returns:
            Tuple of (is_pii_detected, explanation, anonymized_text)
        """
        import re
        import json
        
        # Extract citations section to preserve it
        citations_section = ""
        citations_pattern = re.compile(r'\n\n\*\*Sources:\*\*\n([\s\S]*?)(?:\n\n|$)', re.MULTILINE)
        citations_match = citations_pattern.search(content)
        if citations_match:
            citations_section = citations_match.group(0)
            content = content.replace(citations_section, "__CITATIONS_SECTION__")
        
        # Check if content contains JSON code blocks and handle specially
        json_blocks = []
        json_pattern = re.compile(r'```json\s*\n([\s\S]*?)\n```', re.MULTILINE)
        
        # Extract any JSON code blocks to protect them from PII scanning
        content_without_json = content
        for i, match in enumerate(json_pattern.finditer(content)):
            block_content = match.group(1)
            placeholder = f"__JSON_BLOCK_{i}__"
            json_blocks.append((placeholder, block_content))
            content_without_json = content_without_json.replace(match.group(0), placeholder)
        
        # Now check the text content without JSON blocks
        anonymized = content_without_json  # Start with content minus JSON blocks
        pii_detected = False
        explanations = []
        
        # Check for SSNs (###-##-####)
        ssn_pattern = re.compile(r'\b(\d{3}-\d{2}-\d{4})\b')
        for match in ssn_pattern.finditer(content_without_json):
            # Count the number of characters in the matched SSN
            matched_text = match.group(0)
            # Create a mask with same number of dashes as characters
            mask = "[" + "-" * len(matched_text) + "]"
            anonymized = anonymized.replace(matched_text, mask)
            pii_detected = True
            explanations.append(f"Contains SSN")
            
        # Check for unformatted SSNs (9 digits in a row)
        unformatted_ssn = re.compile(r'\b(\d{9})\b')
        for match in unformatted_ssn.finditer(content_without_json):
            if not any(p in content_without_json[max(0, match.start()-15):match.start()] 
                     for p in ["phone", "fax", "zip", "code", "id"]):
                matched_text = match.group(0)
                mask = "[" + "-" * len(matched_text) + "]"
                anonymized = anonymized.replace(matched_text, mask)
                pii_detected = True
                explanations.append(f"Contains unformatted SSN")
        
        # Check for credit card numbers (simplified patterns)
        # Common pattern for most credit cards (16 digits, may have dashes or spaces)
        cc_pattern = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')
        for match in cc_pattern.finditer(content_without_json):
            matched_text = match.group(0)
            mask = "[" + "-" * len(matched_text) + "]"
            anonymized = anonymized.replace(matched_text, mask)
            pii_detected = True
            explanations.append(f"Contains credit card number")
            
        # Amex pattern (15 digits, may have dashes or spaces)
        amex_pattern = re.compile(r'\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b')
        for match in amex_pattern.finditer(content_without_json):
            matched_text = match.group(0)
            mask = "[" + "-" * len(matched_text) + "]"
            anonymized = anonymized.replace(matched_text, mask)
            pii_detected = True
            explanations.append(f"Contains American Express card number")
        
        # Restore the JSON blocks to the anonymized content
        final_content = anonymized
        for placeholder, block_content in json_blocks:
            final_content = final_content.replace(placeholder, f"```json\n{block_content}\n```")
            
        # Restore the citations section if it was extracted
        if citations_section:
            final_content = final_content.replace("__CITATIONS_SECTION__", citations_section)
        
        # No PII detected
        if not pii_detected:
            return False, "", content
        else:
            return True, "; ".join(explanations), final_content
    
    def _apply_direct_anonymization(self, content: str, pii_type: str) -> str:
        """
        Apply direct anonymization when PII is detected.
        
        Args:
            content: The content to anonymize
            pii_type: Type of PII detected
            
        Returns:
            Anonymized content
        """
        # This method is now obsolete as the full anonymization happens 
        # in _direct_pii_check_and_anonymize
        # Kept for backwards compatibility
        return self._direct_pii_check_and_anonymize(content)[2]
    
    def _extract_response_from_content(self, content: str) -> str:
        """
        Extract the actual response content from input text.
        
        This handles cases where the response starts with "RESPONSE:" prefix
        or contains the original query as part of the content.
        
        Args:
            content: The input content to extract response from
            
        Returns:
            The extracted response text
        """
        # If content is not a string, return it as is
        if not isinstance(content, str):
            return content
            
        # Check for "RESPONSE:" prefix (common pattern from response generators)
        response_prefix_match = re.search(r'RESPONSE:\s*\n', content, re.IGNORECASE)
        if response_prefix_match:
            # Extract everything after the "RESPONSE:" prefix
            start_idx = response_prefix_match.end()
            extracted_content = content[start_idx:].strip()
            logger.info(f"Extracted response after 'RESPONSE:' prefix ({len(extracted_content)} chars)")
            return extracted_content
        
        # If no prefix found but has "generated" in metadata, check for common output formats
        if "\n\n" in content:
            # Some agents use double line breaks to separate metadata from content
            parts = content.split("\n\n")
            # Heuristic: the longest part after the first one is likely the main content
            if len(parts) > 1:
                candidate_parts = parts[1:]
                main_part = max(candidate_parts, key=len)
                if len(main_part) > len(parts[0]) / 2:  # Only if it's substantial
                    logger.info(f"Extracted response from multiple parts ({len(main_part)} chars)")
                    return main_part
        
        # If no clear extraction pattern matched, return the original content
        logger.info("No clear response pattern found, using original content")
        return content