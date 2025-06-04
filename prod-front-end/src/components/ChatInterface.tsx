"use client";

import React, { useEffect, useRef, useState } from 'react';
import useWebSocket from '../hooks/useWebSocket';
import MessageItem from './MessageItem';
import MessageInput from './MessageInput';
import Image from 'next/image';
import publicHealthLogo from '../assets/logos/public_health_assistant.png';

// Update the interface to match the expected API response
interface Workflow {
  id: string;
  name: string;
  description?: string;
  version?: string;
  enabled?: boolean;
}

// Define canned queries
const CANNED_QUERIES = [
  "I have a patient in New York with prior dengue fever, who will be traveling to Saudi Arabia in September 2025. What should I tell him about dengue prevention and treatment?",
  "If a patient has recently returned from a trip to Australia, what should I tell them about post-travel precautions for dengue, given the time of year that it is (April 30, 2025)?",
  "How can a person living in Florida protect themselves from Dengue fever?"
];

const ChatInterface: React.FC = () => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [workflowName, setWorkflowName] = useState('');
  // Rename to make it clear these are fallbacks
  const [availableWorkflows, setAvailableWorkflows] = useState<Workflow[]>([
    { id: '', name: 'Loading workflows...' }
  ]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCannedQueries, setShowCannedQueries] = useState(true);
  
  // Only create a WebSocket URL when we have a valid workflow
  const wsUrl = workflowName ? `ws://localhost:8000/ws/workflow/${workflowName}` : null;
  
  const { 
    isConnected, 
    messages, 
    sendMessage, 
    clearMessages: clearWebSocketMessages, 
    reconnect, 
    error 
  } = useWebSocket(wsUrl);

  // Fetch available workflows from API
  useEffect(() => {
    const fetchWorkflows = async () => {
      try {
        setIsLoading(true);
        console.log('Fetching workflows from API...');
        
        // Always start with GRAPH_RAG_WORKFLOW as default
        console.log('PRE-SETTING GRAPH_RAG_WORKFLOW before API call');
        setWorkflowName('GRAPH_RAG_WORKFLOW');
        
        // Define fallback workflows in case API fails
        const fallbackWorkflows: Workflow[] = [
          { id: 'GRAPH_RAG_WORKFLOW', name: 'Graph RAG Workflow' },
          { id: 'BASIC_TEST_WORKFLOW', name: 'Basic Test Workflow' },
          { id: 'TEST_ACTIVE_WORKFLOW', name: 'Test Active Workflow' }
        ];

        // Check if there's a stored workflow selection
        let storedWorkflow = '';
        try {
          storedWorkflow = localStorage.getItem('selectedWorkflow') || '';
          console.log('Found stored workflow in localStorage:', storedWorkflow);
        } catch (error) {
          console.error('Error reading from localStorage:', error);
        }
        
        try {
          const response = await fetch('http://localhost:8000/api/v1/workflows/', {
            method: 'GET',
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json',
              'Origin': 'http://localhost:3000'
            },
            mode: 'cors'
          });
          
          console.log('API Response Status:', response.status);
          
          if (response.ok) {
            const data = await response.json();
            console.log('API Response Data:', data);
            
            // Check if data has a workflows property that is an array
            if (data && data.workflows && Array.isArray(data.workflows) && data.workflows.length > 0) {
              console.log('Found workflows array with', data.workflows.length, 'items');
              
              // Map the workflow names to our interface
              const workflows = data.workflows.map((name: string) => ({
                id: name,
                name: name.replace(/_/g, ' ').toLowerCase()
                  .split(' ')
                  .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                  .join(' ')
              }));
              
              console.log('Mapped workflows:', workflows);
              setAvailableWorkflows(workflows);
              
              // FORCEFULLY use GRAPH_RAG_WORKFLOW regardless of what's available
              console.log('FORCE SETTING GRAPH_RAG_WORKFLOW as selected workflow');
              setWorkflowName('GRAPH_RAG_WORKFLOW');
            } 
            // Check if data itself is an array (fallback check)
            else if (Array.isArray(data) && data.length > 0) {
              console.log('Data is a direct array with', data.length, 'items');
              const workflows = data.map(item => {
                if (typeof item === 'string') {
                  return {
                    id: item,
                    name: item.replace(/_/g, ' ').toLowerCase()
                      .split(' ')
                      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                      .join(' ')
                  };
                } else {
                  return {
                    id: item.id || item.name || String(item),
                    name: item.display_name || item.name || String(item)
                  };
                }
              });
              console.log('Mapped workflows:', workflows);
              setAvailableWorkflows(workflows);
              
              // FORCEFULLY use GRAPH_RAG_WORKFLOW regardless of what's available
              console.log('FORCE SETTING GRAPH_RAG_WORKFLOW as selected workflow');
              setWorkflowName('GRAPH_RAG_WORKFLOW');
            } else {
              console.log('No valid workflows found in the API response, using fallbacks');
              setAvailableWorkflows(fallbackWorkflows);
              console.log('FORCE SETTING GRAPH_RAG_WORKFLOW as fallback workflow');
              setWorkflowName('GRAPH_RAG_WORKFLOW');
            }
          } else {
            console.error('API response not OK:', response.statusText);
            setAvailableWorkflows(fallbackWorkflows);
            console.log('FORCE SETTING GRAPH_RAG_WORKFLOW as fallback workflow after API error');
            setWorkflowName('GRAPH_RAG_WORKFLOW');
          }
        } catch (error) {
          console.error('Failed to fetch workflows:', error);
          setAvailableWorkflows(fallbackWorkflows);
          console.log('FORCE SETTING GRAPH_RAG_WORKFLOW as fallback workflow after exception');
          setWorkflowName('GRAPH_RAG_WORKFLOW');
        }
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchWorkflows();
  }, []);

  // Format message before sending to match the API specification
  const handleSendMessage = (message: string) => {
    if (!workflowName) {
      console.error('No workflow selected');
      return;
    }
    
    const formattedMessage = {
      message: message,
      metadata: {}
    };
    
    sendMessage(formattedMessage);
  };

  // Auto-scroll to the latest message
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Handle canned query selection
  const handleCannedQuery = (query: string) => {
    if (!isConnected) return;
    
    // Hide canned queries after selection
    setShowCannedQueries(false);
    
    handleSendMessage(query);
  };

  // Group messages into different categories
  const groupSystemMessages = () => {
    const userMessages = messages.filter(msg => msg.sender === 'user');
    const connectionMessages = messages.filter(msg => msg.type === 'connected');
    const streamMessages = messages.filter(msg => msg.type === 'stream_update');
    const resultMessages = messages.filter(msg => msg.type === 'workflow_result' || msg.type === 'workflow_error');
    const errorMessages = messages.filter(msg => msg.type === 'error');
    const otherMessages = messages.filter(msg => 
      msg.sender !== 'user' && 
      msg.type !== 'connected' && 
      msg.type !== 'stream_update' && 
      msg.type !== 'workflow_result' &&
      msg.type !== 'workflow_error' &&
      msg.type !== 'error'
    );
    
    // Combine the messages in the desired order for display
    return [
      ...connectionMessages,
      ...userMessages,
      ...streamMessages,
      ...resultMessages,
      ...errorMessages,
      ...otherMessages
    ];
  };

  // Function to clear messages and show canned queries again
  const clearMessages = () => {
    clearWebSocketMessages();
    setShowCannedQueries(true); // Show canned queries again after clearing
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] max-w-4xl mx-auto border border-gray-300 rounded-lg shadow-md">
      <div className="flex justify-between items-center p-4 border-b bg-[#003366] text-white">
        <div className="flex items-center">
          <div className="flex-shrink-0 mr-3">
            <Image 
              src={publicHealthLogo} 
              alt="Public Health Assistant Logo" 
              width={50} 
              height={50} 
              className="rounded-md"
            />
          </div>
          <h1 className="text-2xl font-semibold">Public Health Assistant</h1>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={clearMessages}
            className="px-3 py-1 bg-[#0066cc] text-white rounded hover:bg-[#f5921b] transition-colors text-sm"
          >
            Clear Chat
          </button>
          {!isConnected && (
            <button
              onClick={reconnect}
              className="px-3 py-1 bg-[#ee0000] text-white rounded hover:bg-[#5f0000] transition-colors text-sm"
            >
              Reconnect
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 bg-white">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-[#003366]">
            <h2 className="text-xl font-medium mb-4">Welcome to Public Health Assistant</h2>
            <p className="text-center max-w-md mb-4">
              Your trusted source for dengue fever information and patient care guidance.
            </p>
            <p className="text-center text-[#0066cc]">
              Ask a question below or use one of the suggested queries to get started.
            </p>
          </div>
        ) : (
          groupSystemMessages().map((msg, index) => (
            <MessageItem key={index} message={msg} messages={groupSystemMessages()} index={index} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="p-2 bg-white text-[#ee0000] text-sm font-medium border border-[#ee0000]">
          Connection error. Please try reconnecting.
        </div>
      )}

      <div className="p-4 border-t bg-white">
        {showCannedQueries && messages.length > 0 ? (
          <div className="space-y-3 mb-4">
            <p className="text-sm font-medium text-[#003366]">Suggested Questions:</p>
            <div className="flex flex-wrap gap-2">
              {CANNED_QUERIES.map((query, index) => (
                <button
                  key={index}
                  onClick={() => handleCannedQuery(query)}
                  className="px-3 py-2 bg-[#fccb8f] text-[#003366] rounded-lg hover:bg-[#f5921b] hover:text-white text-sm text-left transition-colors flex-1 min-w-[250px]"
                  disabled={!isConnected}
                >
                  {query.length > 100 ? query.substring(0, 100) + '...' : query}
                </button>
              ))}
            </div>
          </div>
        ) : showCannedQueries && messages.length === 0 ? (
          <div className="space-y-3 mb-4">
            <p className="text-sm font-medium text-[#003366]">Suggested Questions:</p>
            <div className="flex flex-wrap gap-2">
              {CANNED_QUERIES.map((query, index) => (
                <button
                  key={index}
                  onClick={() => handleCannedQuery(query)}
                  className="px-3 py-2 bg-[#fccb8f] text-[#003366] rounded-lg hover:bg-[#f5921b] hover:text-white text-sm text-left transition-colors flex-1 min-w-[250px]"
                  disabled={!isConnected}
                >
                  {query.length > 100 ? query.substring(0, 100) + '...' : query}
                </button>
              ))}
            </div>
          </div>
        ) : null}
        <div className="text-sm text-[#003366] mb-1">
          <span className={`inline-block w-2 h-2 rounded-full mr-1 ${isConnected ? 'bg-[#0066cc]' : 'bg-[#ee0000]'}`}></span>
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>
        <MessageInput 
          onSendMessage={handleSendMessage} 
          isConnected={isConnected}
          workflowSelected={!!workflowName} 
        />
      </div>
    </div>
  );
};

export default ChatInterface;