"use client";

import React, { useState, FormEvent, KeyboardEvent } from 'react';

interface MessageInputProps {
  onSendMessage: (message: string) => void;
  isConnected: boolean;
  workflowSelected?: boolean;
}

const MessageInput: React.FC<MessageInputProps> = ({ 
  onSendMessage, 
  isConnected,
  workflowSelected = true
}) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (message.trim() && isConnected && workflowSelected) {
      onSendMessage(message);
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Determine the placeholder text based on connection and workflow status
  const getPlaceholder = () => {
    if (!workflowSelected) return "Please select a workflow first...";
    if (!isConnected) return "Connecting...";
    return "Type your question about dengue fever...";
  };

  const isDisabled = !isConnected || !workflowSelected;

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2">
      <div className="flex-grow relative">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={getPlaceholder()}
          className={`w-full p-3 border rounded-md focus:outline-none ${isConnected ? 'focus:border-[#0066cc]' : 'bg-gray-100 text-gray-500'} text-gray-800 font-medium border-[#0066cc]`}
          rows={3}
          style={{ 
            minHeight: '44px', 
            maxHeight: '200px', 
            resize: 'none'
          }}
          disabled={isDisabled}
        />
      </div>
      <button
        type="submit"
        className={`px-4 py-2 rounded-md text-white font-medium flex items-center justify-center ${
          isConnected && message.trim() && workflowSelected
            ? 'bg-[#0066cc] hover:bg-[#003366]'
            : 'bg-gray-300 cursor-not-allowed'
        }`}
        disabled={isDisabled || !message.trim()}
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
        </svg>
      </button>
    </form>
  );
};

export default MessageInput;
