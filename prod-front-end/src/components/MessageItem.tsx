"use client";

import React, { useState, useEffect } from 'react';
import { WebSocketMessage } from '../hooks/useWebSocket';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';

interface MessageItemProps {
  message: WebSocketMessage;
  messages: WebSocketMessage[]; // All messages for context
  index: number; // Message position in the array
}

// Custom Citation component for rendering citation tags
const Citation = ({ id, children }: { id: string; children: React.ReactNode }) => {
  const [tooltipVisible, setTooltipVisible] = useState(false);
  const [dataExpanded, setDataExpanded] = useState(false);
  
  // Get citation data based on the ID
  const getCitationData = (id: string) => {
    // Sample data mapping for different citation IDs
    const citationData: {[key: string]: {title: string, source?: string, data: string[], index?: number}} = {
      'kg-1': {
        title: 'Knowledge Graph: Dengue Transmission',
        source: 'CDC Travel Health Guidelines',
        data: [
          'Aedes aegypti mosquitoes are the primary vectors for dengue virus',
          'These mosquitoes typically bite during the day, especially early morning and late afternoon',
          'Female mosquitoes acquire the virus by feeding on infected humans',
          'The virus incubates in the mosquito for 8-12 days before it can be transmitted'
        ]
      },
      'data-1': {
        title: 'Historical Dengue Cases in Saudi Arabia', 
        source: 'WHO Surveillance Data 2020-2024',
        data: [
          '2020: 432 reported cases',
          '2021: 507 reported cases',
          '2022: 683 reported cases',
          '2023: 791 reported cases',
          '2024: 842 reported cases (January-October)'
        ]
      },
      'data-2': {
        title: 'Seasonal Distribution of Dengue Cases', 
        source: 'Saudi Ministry of Health, 2024 Report',
        data: [
          'Winter (Dec-Feb): 12% of annual cases',
          'Spring (Mar-May): 18% of annual cases',
          'Summer (Jun-Aug): 47% of annual cases',
          'Fall (Sep-Nov): 23% of annual cases'
        ]
      },
      'who-1': {
        title: 'WHO Dengue Guidelines Summary',
        source: 'World Health Organization, 2023',
        data: [
          'Dengue is a mosquito-borne viral infection',
          'About half of the world\'s population is now at risk',
          'There are an estimated 100-400 million infections yearly',
          'Early detection and access to proper medical care can reduce fatality rates to below 1%'
        ]
      },
      'cdc-1': {
        title: 'CDC Travel Advisory',
        source: 'Centers for Disease Control and Prevention, 2024',
        data: [
          'Use insect repellent, wear covering clothing',
          'Choose accommodations with screened windows/doors',
          'Symptoms appear 4-10 days after infection',
          'Seek medical care promptly if symptoms develop'
        ]
      },
      // Add document references from the actual document
      'doc-1': {
        title: 'Special Considerations for Dengue Management',
        source: 'National Guidelines for Clinical Management of Dengue Fever 2023',
        index: 1,
        data: [
          'Pregnant women may be at increased risk for complications and often warrant inpatient monitoring',
          'Vertical transmission from mother to baby can occur, especially near delivery time',
          'Most infected newborns are asymptomatic, but some may develop symptoms within two weeks',
          'Pediatric cases require weight-based fluid calculations and special monitoring',
          'Patients with co-morbidities are at higher risk for severe dengue'
        ]
      },
      'doc-2': {
        title: 'Key Pillars of Dengue Management',
        source: 'CDC and WHO/PAHO Clinical Practice Guidelines',
        index: 1,
        data: [
          'Standardized Classification: WHO 2009 severity classification guides risk stratification',
          'Emphasis on Warning Signs: Monitoring specific warning signs is crucial for care escalation',
          'Supportive Care Focus: Management relies on fluid balance and appropriate fever control',
          'Critical Fluid Management: Careful titration based on hemodynamic status',
          'Evidence-Based Contraindications: Avoidance of routine corticosteroids and prophylactic platelet transfusions'
        ]
      }
    };
    
    // Return data if available, or fallback text
    return citationData[id] || {
      title: `Source: ${id}`,
      source: 'Citation data not available',
      data: ['Details for this citation are not available']
    };
  };
  
  // Extract a relevant snippet from the document content
  const getDocumentSnippet = (index: number) => {
    // This would normally retrieve content from the actual document
    // For now, we're using sample content from the document provided
    if (index === 1) {
      return `Special Considerations (Brief Mention)
While the core principles apply broadly, specific patient populations require tailored considerations in dengue management:

Pregnancy: Dengue during pregnancy poses risks to both mother and fetus and requires careful multidisciplinary management. Pregnant women may be at increased risk for complications and often warrant inpatient monitoring (Group B) even without warning signs. Vertical transmission from mother to baby can occur, especially if the mother is symptomatic near the time of delivery.

Pediatrics: Clinical presentation and management in children, particularly infants, can differ from adults. Fluid management relies heavily on accurate weight-based calculations (e.g., using Holliday-Segar formula for maintenance needs). Recognizing shock can be more challenging, as hypotension is a late sign; subtle signs like lethargy, cool extremities, and prolonged capillary refill are critical.

Co-morbidities: Patients with pre-existing chronic conditions—such as diabetes mellitus, chronic renal failure, cardiovascular disease, chronic hemolytic diseases (e.g., sickle cell anemia), obesity, or underlying coagulopathies—are generally considered at higher risk for developing severe dengue or experiencing complications.`;
    }
    return "No document snippet available for this citation.";
  };
  
  const citationData = getCitationData(id);
  
  return (
    <span 
      className="inline-flex items-center rounded-md bg-[#0066cc] px-2 py-1 text-xs font-medium text-white ring-1 ring-inset ring-[#003366]/20 cursor-pointer relative"
      onClick={() => setDataExpanded(!dataExpanded)}
      onMouseEnter={() => setTooltipVisible(true)}
      onMouseLeave={() => setTooltipVisible(false)}
    >
      <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
      {children}
      
      {tooltipVisible && !dataExpanded && (
        <div className="absolute bottom-full left-0 mb-2 w-64 p-2 bg-[#0066cc] text-white text-xs rounded shadow-lg z-10">
          <div className="font-bold mb-1">Source Information</div>
          <div className="mb-1">ID: {id}</div>
          <div className="text-[#003366] text-xs">Click to view detailed data</div>
          <div className="absolute bottom-0 left-3 -mb-1 w-2 h-2 bg-[#0066cc] transform rotate-45"></div>
        </div>
      )}
      
      {dataExpanded && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={(e) => {
          // Close the modal when clicking the background but not when clicking inside the content
          if (e.target === e.currentTarget) setDataExpanded(false);
        }}>
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-[#003366]">{citationData.title}</h3>
              <button 
                className="text-gray-500 hover:text-gray-700" 
                onClick={() => setDataExpanded(false)}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="text-gray-900">
              {citationData.source && (
                <div className="mb-4">
                  <div className="font-medium text-[#003366] mb-1">Source</div>
                  <div className="text-sm bg-gray-50 p-3 rounded border border-gray-200">
                    {citationData.source}
                  </div>
                </div>
              )}
              
              <div className="mb-4">
                <div className="font-medium text-[#003366] mb-2">Key Information</div>
                <ul className="list-disc pl-5 space-y-2">
                  {citationData.data.map((item, index) => (
                    <li key={index} className="text-sm">{item}</li>
                  ))}
                </ul>
              </div>
              
              {citationData.index !== undefined && (
                <div className="mb-4">
                  <div className="font-medium text-[#003366] mb-1">Document Extract</div>
                  <div className="text-sm bg-gray-50 p-3 rounded border border-gray-200 whitespace-pre-line">
                    {getDocumentSnippet(citationData.index)}
                  </div>
                </div>
              )}
              
              <div className="text-xs text-gray-500 pt-4 border-t border-gray-200">
                Citation ID: {id}
              </div>
            </div>
          </div>
        </div>
      )}
    </span>
  );
};

// Process content to handle citation tags and apply markdown formatting
const formatContent = (content: string) => {
  if (!content) return "No content available";
  
  // Pre-process the content to handle citation tags before markdown parsing
  // Convert citation tags to a special format that won't be affected by markdown processing
  let processedContent = content;
  
  // Replace citation tags with a special format
  processedContent = processedContent.replace(/<citation id=['"]([^'"]+)['"]>([^<]+)<\/citation>/g, 
    (match, id, text) => {
      // Use a format that won't be affected by markdown
      return `%%%CITATION_START:${id}%%%${text}%%%CITATION_END%%%`;
    }
  );

  // Function to process the final output after markdown rendering
  const processCitations = (text: string) => {
    if (!text.includes('%%%CITATION_START:')) return text;
    
    // Replace our special citation format with actual Citation components
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let textPartIndex = 0;
    
    // Regex to find our special citation format
    const regex = /%%%CITATION_START:([^%]+)%%%([^%]+)%%%CITATION_END%%%/g;
    let match;
    
    while ((match = regex.exec(text)) !== null) {
      // Add text before the citation
      if (match.index > lastIndex) {
        // Add key to text fragment
        parts.push(
          <React.Fragment key={`text-part-${textPartIndex++}`}>
            {text.substring(lastIndex, match.index)}
          </React.Fragment>
        );
      }
      
      // Add the Citation component
      const [fullMatch, id, citationText] = match;
      parts.push(
        <Citation key={`citation-${id}`} id={id}>
          {citationText}
        </Citation>
      );
      
      lastIndex = match.index + fullMatch.length;
    }
    
    // Add remaining text after the last citation
    if (lastIndex < text.length) {
      parts.push(
        <React.Fragment key={`text-part-${textPartIndex++}`}>
          {text.substring(lastIndex)}
        </React.Fragment>
      );
    }
    
    return parts.length > 0 ? <>{parts}</> : text;
  };

  return (
    <div className="markdown-content prose prose-sm max-w-none prose-table:overflow-hidden prose-table:border prose-table:border-[#0066cc]">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          // Custom renderers for markdown elements
          p: ({ node, children, ...props }) => {
            // Process any citations in the paragraph
            if (typeof children === 'string' && children.includes('%%%CITATION_START:')) {
              return <p className="mb-3" {...props}>{processCitations(children)}</p>;
            }
            // Handle arrays of children (which could contain our citation placeholders)
            if (Array.isArray(children)) {
              const processedChildren = children.map((child, index) => {
                if (typeof child === 'string' && child.includes('%%%CITATION_START:')) {
                  return processCitations(child);
                }
                return child;
              });
              return <p className="mb-3" {...props}>{processedChildren}</p>;
            }
            return <p className="mb-3" {...props}>{children}</p>;
          },
          li: ({ node, children, ...props }) => {
            // Process citations in list items
            if (typeof children === 'string' && children.includes('%%%CITATION_START:')) {
              return <li className="mb-1" {...props}>{processCitations(children)}</li>;
            }
            // Handle arrays of children
            if (Array.isArray(children)) {
              const processedChildren = children.map((child, index) => {
                if (typeof child === 'string' && child.includes('%%%CITATION_START:')) {
                  return processCitations(child);
                }
                return child;
              });
              return <li className="mb-1" {...props}>{processedChildren}</li>;
            }
            return <li className="mb-1" {...props}>{children}</li>;
          },
          strong: ({ node, children, ...props }) => {
            // Process citations in strong text
            if (typeof children === 'string' && children.includes('%%%CITATION_START:')) {
              return <strong className="font-bold text-gray-900" {...props}>{processCitations(children)}</strong>;
            }
            // Handle arrays of children
            if (Array.isArray(children)) {
              const processedChildren = children.map((child, index) => {
                if (typeof child === 'string' && child.includes('%%%CITATION_START:')) {
                  return processCitations(child);
                }
                return child;
              });
              return <strong className="font-bold text-gray-900" {...props}>{processedChildren}</strong>;
            }
            return <strong className="font-bold text-gray-900" {...props}>{children}</strong>;
          },
          em: ({ node, children, ...props }) => {
            // Process citations in emphasized text
            if (typeof children === 'string' && children.includes('%%%CITATION_START:')) {
              return <em {...props}>{processCitations(children)}</em>;
            }
            // Handle arrays of children
            if (Array.isArray(children)) {
              const processedChildren = children.map((child, index) => {
                if (typeof child === 'string' && child.includes('%%%CITATION_START:')) {
                  return processCitations(child);
                }
                return child;
              });
              return <em {...props}>{processedChildren}</em>;
            }
            return <em {...props}>{children}</em>;
          },
          // Table rendering components without div wrapper (causes nesting issues)
          table: ({ node, ...props }) => <table className="min-w-full overflow-x-auto border-collapse border border-[#0066cc] my-4 rounded-lg shadow-sm" {...props} />,
          thead: ({ node, ...props }) => <thead className="bg-gray-100" {...props} />,
          tbody: ({ node, ...props }) => <tbody className="bg-white divide-y divide-gray-200" {...props} />,
          tr: ({ node, ...props }) => <tr className="hover:bg-gray-50" {...props} />,
          th: ({ node, ...props }) => <th className="py-2 px-4 border-b border-[#0066cc] text-left text-xs font-medium text-gray-600 uppercase tracking-wider" {...props} />,
          td: ({ node, ...props }) => <td className="py-2 px-4 border border-gray-200 text-sm" {...props} />,
          // Apply container styles to the main parent elements to wrap tables properly
          div: ({ node, ...props }) => <div className="overflow-x-auto" {...props} />,
          ul: ({ node, ...props }) => <ul className="list-disc pl-6 mb-4" {...props} />,
          ol: ({ node, ...props }) => <ol className="list-decimal pl-6 mb-4" {...props} />,
          h1: ({ node, ...props }) => <h1 className="text-2xl font-bold mb-4" {...props} />,
          h2: ({ node, ...props }) => <h2 className="text-xl font-bold mb-3" {...props} />,
          h3: ({ node, ...props }) => <h3 className="text-lg font-bold mb-2" {...props} />,
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
};

const MessageItem: React.FC<MessageItemProps> = ({ message, messages, index }) => {
  const isUser = message.sender === 'user';
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Format the timestamp if it exists
  const formattedTime = message.timestamp 
    ? new Date(message.timestamp).toLocaleTimeString() 
    : '';

  // Group all processing messages for this query
  const [processingMessages, setProcessingMessages] = useState<WebSocketMessage[]>([]);
  const [hasFollowingResult, setHasFollowingResult] = useState(false);
  
  // Identify if this is a user message followed by processing updates
  useEffect(() => {
    if (isUser) {
      // Check if this user message is followed by processing messages
      let followingMessages: WebSocketMessage[] = [];
      let foundResult = false;
      let i = index + 1;
      
      // Collect all processing messages until the next user message or result
      while (i < messages.length) {
        const nextMsg = messages[i];
        
        // If we find a user message, stop collecting
        if (nextMsg.sender === 'user') {
          break;
        }
        
        // If we find a connection message, skip it
        if (nextMsg.type === 'connected') {
          i++;
          continue;
        }
        
        // If we find a result message, mark that we found one and stop collecting
        if (nextMsg.type === 'workflow_result' || nextMsg.type === 'workflow_error') {
          foundResult = true;
          break;
        }
        
        // Add this processing message to our collection
        if (nextMsg.type === 'stream_update') {
          followingMessages.push(nextMsg);
        }
        
        i++;
      }
      
      setProcessingMessages(followingMessages);
      setHasFollowingResult(foundResult);
      // Auto-expand if we have messages and settings indicate we should
      setIsExpanded(followingMessages.length > 0 && false); // Change to true to auto-expand
    }
  }, [isUser, index, messages]);

  // Handle connection messages
  if (message.type === 'connected') {
    return (
      <div className="flex justify-center mb-3">
        <div className="bg-[#0066cc] text-white px-4 py-2 rounded-full text-sm font-medium shadow-sm">
          {message.message || `Connected to ${message.workflow_name || 'workflow'}`}
          {formattedTime && (
            <span className="text-xs text-white opacity-70 ml-2">
              {formattedTime}
            </span>
          )}
        </div>
      </div>
    );
  }

  // Handle individual system processing updates
  if (message.type === 'stream_update' && !isUser) {
    // Skip individual stream updates as they will be grouped with the user message
    return null;
  }

  // Handle final results
  if (message.type === 'workflow_result') {
    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-[80%] rounded-lg px-4 py-3 shadow-sm bg-white text-gray-800 border border-[#0066cc]">
          <div className="text-xs text-[#003366] font-medium mb-1 flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1 text-[#0066cc]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Public Health Assistant Response
          </div>
          
          <div className="text-sm prose prose-sm max-w-none prose-table:overflow-hidden prose-table:border prose-table:border-[#0066cc]">
            {formatContent(message.content)}
          </div>
          
          {formattedTime && (
            <div className="text-xs mt-1 text-gray-600">
              {formattedTime}
            </div>
          )}
        </div>
      </div>
    );
  }
  
  // Handle error messages
  if (message.type === 'error' || message.type === 'workflow_error') {
    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-[80%] rounded-lg px-4 py-3 shadow-sm bg-[#ee0000] text-white border border-[#ee0000]">
          <div className="text-xs text-white font-medium mb-1 flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Error
          </div>
          
          <div className="text-sm">
            {message.content || message.error || "An error occurred"}
          </div>
          
          {formattedTime && (
            <div className="text-xs mt-1 text-white opacity-70">
              {formattedTime}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Handle user messages (with possible grouped processing steps)
  if (isUser) {
    return (
      <div className="mb-4">
        {/* User message bubble */}
        <div className="flex justify-end mb-2">
          <div className="max-w-[80%] rounded-lg px-4 py-3 shadow-sm bg-[#0066cc] text-white font-medium">
            <div className="text-sm">{message.content}</div>
            {formattedTime && (
              <div className="text-xs mt-1 text-white opacity-70">
                {formattedTime}
              </div>
            )}
          </div>
        </div>
        
        {/* Processing steps collapsible section */}
        {processingMessages.length > 0 && (
          <div className="mb-4">
            <div className="bg-gray-50 rounded-lg border border-gray-200 shadow-sm overflow-hidden">
              {/* Collapsible header */}
              <div 
                className="flex items-center p-3 cursor-pointer hover:bg-gray-50 border-b border-gray-200"
                onClick={() => setIsExpanded(!isExpanded)}
              >
                <div className="font-medium text-gray-700 flex items-center flex-grow">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-[#0066cc]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span>Processing Steps</span>
                  <span className="text-xs bg-[#fccb8f] text-[#003366] px-2 py-1 rounded ml-2 font-bold">
                    {processingMessages.length} {processingMessages.length === 1 ? 'step' : 'steps'}
                  </span>
                </div>
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  className={`h-5 w-5 ml-2 transition-transform duration-200 text-[#0066cc] ${isExpanded ? 'rotate-180' : ''}`} 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
              
              {/* Collapsible content */}
              {isExpanded && (
                <div className="border-t border-gray-200 p-3 bg-gray-50">
                  <div className="text-sm space-y-2">
                    {formatProcessingSteps(processingMessages)}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Default case for any other message type
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[80%] rounded-lg px-4 py-3 shadow-sm bg-white text-gray-800 border border-gray-200 font-medium">
        <div className="text-xs text-gray-500 font-medium mb-1">
          {message.type || 'Message'}
        </div>
        <div className="text-sm">{message.content}</div>
        {formattedTime && (
          <div className="text-xs mt-1 text-gray-600">
            {formattedTime}
          </div>
        )}
      </div>
    </div>
  );
};

// Formats the processing steps into a readable timeline
function formatProcessingSteps(messages: WebSocketMessage[]) {
  // Group messages by agent to maintain a timeline but show agent context
  type AgentGroup = {
    agentId: string;
    steps: {
      type: string;
      content: string;
      timestamp: string;
      isCompleted: boolean;
      data?: any;
    }[];
  };
  
  const agentGroups: Record<string, AgentGroup> = {};
  
  // First, collect and group all messages by agent
  messages.forEach(msg => {
    const agentId = msg.agent_id || 'System';
    if (!agentGroups[agentId]) {
      agentGroups[agentId] = {
        agentId,
        steps: []
      };
    }
    
    // Extract the detailed content
    let content = '';
    let isCompleted = false;
    
    // Handle special message types from workflow manager
    if (agentId === 'workflow_manager') {
      // Handle workflow manager updates
      if (msg.message_type === 'workflow_update' || msg.message_type === 'step_update' || 
          msg.message_type === 'loop_update' || msg.message_type === 'fallback_update') {
        // Use the data message field if available
        if (msg.data && msg.data.message) {
          content = msg.data.message;
          
          // Add result summary if available
          if (msg.data.result_summary) {
            content += '\n' + msg.data.result_summary;
          }
          
          // Handle completion status
          isCompleted = msg.content === 'completed';
        } else {
          content = msg.content || msg.message_type || 'Processing';
        }
      }
    } else {
      // Check if this is a completion message
      if (msg.content === 'completed' || (msg.message_type === 'agent_update' && msg.data?.status === 'completed')) {
        isCompleted = true;
        content = 'Processing completed';
      } 
      // Check data field for detailed info
      else if (msg.data) {
        if (typeof msg.data === 'string') {
          content = msg.data;
        } else if (typeof msg.data === 'object') {
          if (msg.data.message) {
            content = msg.data.message;
          } else {
            content = JSON.stringify(msg.data, null, 2);
          }
        }
      } 
      // Use content field if available
      else if (msg.content && msg.content !== 'thinking' && msg.content !== 'processing') {
        content = msg.content;
      }
      // Use message_type as fallback
      else {
        content = msg.message_type || 'Processing';
      }
    }
    
    agentGroups[agentId].steps.push({
      type: msg.message_type || '',
      content,
      timestamp: msg.timestamp || '',
      isCompleted,
      data: msg.data
    });
  });
  
  // Now format each agent group as a timeline
  return Object.values(agentGroups).map((group, groupIndex) => (
    <div key={groupIndex} className="mb-4 last:mb-0">
      <div className="font-medium mb-2 text-[#003366]">
        {formatAgentName(group.agentId)}
      </div>
      <div className="space-y-2 pl-4 border-l-2 border-[#0066cc]">
        {group.steps.map((step, stepIndex) => {
          // Format based on step type
          let icon = '⚙️';
          let textColor = 'text-gray-700';
          
          if (step.type === 'logs' || step.type === 'thinking') {
            icon = '🧠';
            textColor = 'text-purple-600';
          } else if (step.type === 'workflow_update') {
            icon = '🔄';
            textColor = 'text-indigo-600';
          } else if (step.type === 'step_update') {
            icon = '🔍';
            textColor = 'text-[#0066cc]';
          } else if (step.type === 'loop_update') {
            icon = '🔁';
            textColor = 'text-cyan-600';
          } else if (step.type === 'fallback_update') {
            icon = '🔀';
            textColor = 'text-amber-600';
          } else if (step.isCompleted) {
            icon = '✅';
            textColor = 'text-green-600';
          }
          
          // If there's a status in the data, show status-appropriate icon
          if (step.data && step.data.status) {
            if (step.data.status === 'error') {
              icon = '❌';
              textColor = 'text-red-600';
            } else if (step.data.status === 'completed') {
              icon = '✅';
              textColor = 'text-green-600';
            } else if (step.data.status === 'starting') {
              icon = '🚀';
              textColor = 'text-blue-600';
            } else if (step.data.status === 'iterating') {
              icon = '🔄';
              textColor = 'text-amber-600';
            }
          }
          
          return (
            <div key={stepIndex} className="flex items-start">
              <div className="flex-shrink-0 mr-2">
                <span>{icon}</span>
              </div>
              <div className={`flex-grow ${textColor}`}>
                <div className="text-sm whitespace-pre-line">{step.content}</div>
                {step.timestamp && (
                  <div className="text-xs text-gray-500">
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  ));
}

// Helper function to format agent names nicely
function formatAgentName(agentId: string) {
  // Convert agent_id to a nicer display format
  return agentId
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export default MessageItem;