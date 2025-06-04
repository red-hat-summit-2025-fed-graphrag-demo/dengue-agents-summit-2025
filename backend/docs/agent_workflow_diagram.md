# Agent System Workflow Diagram

This document provides a comprehensive visualization of the entire agent system workflow, from initial user input to final response.

## Complete Agent Workflow

```mermaid
flowchart TD
    %% Main entities
    User([User]) --> UserPrompt[User Prompt]
    UserPrompt --> InjectionCheck{Injection Check Agent}
    
    %% Initial Safety Checks (Front of the Sandwich)
    InjectionCheck -->|Injection Detected| BlockResponse[Block Response]
    InjectionCheck -->|Safe| PolicyCheck{Policy Check Agent}
    PolicyCheck -->|Policy Violation| BlockResponse
    BlockResponse --> SafetyMessage[Safety Message to User]
    SafetyMessage --> User
    
    %% Router
    PolicyCheck -->|Safe| TaskRouter{Task Router Agent}
    
    %% Main agent pathways
    TaskRouter -->|Code Question| CodeAssistant[Code Assistant Agent]
    TaskRouter -->|General Question| GeneralAssistant[General Assistant Agent]
    TaskRouter -->|Dengue Knowledge Question| GraphRAG[GraphRAG Workflow]
    
    %% Response Routing
    CodeAssistant --> ContentComplianceCheck
    GeneralAssistant --> ContentComplianceCheck
    
    %% GraphRAG detailed workflow
    subgraph GraphRAG Workflow
        QueryGenerator[Graph Query Generator Agent]
        QueryExecutor[Graph Query Executor Agent]
        ResultAssessor[Graph Result Assessor Agent]
        TemplateSelector[Template Criteria Selector]
        ResponseGenerator[Response Generator Agent]
        
        QueryGenerator --> QueryExecutor
        QueryExecutor --> ResultAssessor
        ResultAssessor --> TemplateSelector
        TemplateSelector -->|Template Selected| ResponseGenerator
        TemplateSelector -->|No Template| FreeForm[Free-form Generation]
        FreeForm --> ResponseGenerator
    end
    
    GraphRAG --> ContentComplianceCheck
    
    %% Final Compliance Check (Back of the Sandwich)
    ContentComplianceCheck{Content Compliance Agent} -->|Compliant| Response[Response to User]
    ContentComplianceCheck -->|Non-Compliant| RemediationResponse[Remediate Response]
    RemediationResponse --> Response
    Response --> User
    
    %% Templates
    subgraph Templates
        SymptomsTemplate[Symptom Overview Template]
        TreatmentTemplate[Treatment Options Template]
        TransmissionTemplate[Disease Transmission Template]
        OverviewTemplate[General Overview Template]
        CodeTemplate[Code Example Template]
        
        TemplateSelector -.->|Match Symptoms| SymptomsTemplate
        TemplateSelector -.->|Match Treatment| TreatmentTemplate
        TemplateSelector -.->|Match Transmission| TransmissionTemplate
        TemplateSelector -.->|Match Overview| OverviewTemplate
        TemplateSelector -.->|Match Code| CodeTemplate
        
        SymptomsTemplate -.-> ResponseGenerator
        TreatmentTemplate -.-> ResponseGenerator
        TransmissionTemplate -.-> ResponseGenerator
        OverviewTemplate -.-> ResponseGenerator
        CodeTemplate -.-> ResponseGenerator
    end
    
    %% Data Flow (metadata)
    UserPrompt -.->|Metadata| InjectionCheck
    InjectionCheck -.->|Metadata| PolicyCheck
    PolicyCheck -.->|Metadata| TaskRouter
    TaskRouter -.->|Metadata| CodeAssistant
    TaskRouter -.->|Metadata| GeneralAssistant
    TaskRouter -.->|Metadata| QueryGenerator
    QueryGenerator -.->|Graph Query + Metadata| QueryExecutor
    QueryExecutor -.->|Query Results + Metadata| ResultAssessor
    ResultAssessor -.->|Assessment + Visualization Data + Metadata| TemplateSelector
    TemplateSelector -.->|Template + Metadata| ResponseGenerator
    
    %% Styling
    classDef agent fill:#f9f,stroke:#333,stroke-width:2px
    classDef safety fill:#fcc,stroke:#f66,stroke-width:2px
    classDef template fill:#cfc,stroke:#6f6,stroke-width:1px
    classDef response fill:#ccf,stroke:#66f,stroke-width:2px
    classDef user fill:#cff,stroke:#6ff,stroke-width:2px
    classDef compliance fill:#fcf,stroke:#c6c,stroke-width:2px
    
    class InjectionCheck,PolicyCheck safety
    class ContentComplianceCheck compliance
    class TaskRouter,CodeAssistant,GeneralAssistant agent
    class QueryGenerator,QueryExecutor,ResultAssessor,TemplateSelector,ResponseGenerator agent
    class SymptomsTemplate,TreatmentTemplate,TransmissionTemplate,OverviewTemplate,CodeTemplate template
    class Response,SafetyMessage,RemediationResponse response
    class User,UserPrompt user
```

## GraphRAG Workflow with Compliance Check

```mermaid
sequenceDiagram
    participant User
    participant Router as Task Router
    participant QGen as Graph Query Generator
    participant QExec as Graph Query Executor
    participant KG as Knowledge Graph
    participant Assessor as Result Assessor
    participant TSelect as Template Selector
    participant RGen as Response Generator
    participant CompCheck as Content Compliance Agent
    
    User->>Router: Dengue-related question
    Router->>QGen: Route to GraphRAG
    
    %% Query Generation
    QGen->>QGen: Generate Cypher query
    QGen->>QExec: Pass query and metadata
    
    %% Query Execution
    QExec->>KG: Execute query against graph
    KG->>QExec: Return graph results
    QExec->>Assessor: Pass results and metadata
    
    %% Result Assessment
    Assessor->>Assessor: Assess quality & relevance
    Assessor->>Assessor: Extract visualization data
    Assessor->>TSelect: Pass assessment and metadata
    
    %% Template Selection
    TSelect->>TSelect: Match query to template criteria
    alt Template Found
        TSelect->>RGen: Pass selected template
    else No Template
        TSelect->>RGen: Use free-form generation
    end
    
    %% Response Generation
    RGen->>RGen: Generate response with template
    RGen->>CompCheck: Pass generated response
    
    %% Compliance Check
    CompCheck->>CompCheck: Check for PII/PHI, SSN, and abusive language
    alt Compliant
        CompCheck->>User: Return original response
    else Non-Compliant
        CompCheck->>CompCheck: Remediate non-compliant content
        CompCheck->>User: Return remediated response
    end
```

## Compliance Sandwich Pattern

```mermaid
flowchart LR
    Input[User Input] --> FrontCheck[Initial Safety Checks]
    FrontCheck -->|Safe| Processing[Agent Processing]
    Processing --> BackCheck[Content Compliance Check]
    BackCheck -->|Compliant| Output[Response to User]
    BackCheck -->|Non-Compliant| Remediation[Remediate Response]
    Remediation --> Output
    
    classDef safety fill:#fcc,stroke:#f66,stroke-width:2px
    classDef process fill:#cfc,stroke:#6f6,stroke-width:1px
    classDef compliance fill:#fcf,stroke:#c6c,stroke-width:2px
    classDef io fill:#cff,stroke:#6ff,stroke-width:2px
    
    class FrontCheck safety
    class Processing process
    class BackCheck compliance
    class Input,Output,Remediation io
```

## Template Selection Criteria

```mermaid
flowchart TD
    Query[User Query] --> TSelector[Template Criteria Selector]
    
    TSelector --> SymptomCheck{Contains symptom terms?}
    SymptomCheck -->|Yes| SymptomTemplate[Symptom Overview Template]
    
    SymptomCheck -->|No| TreatmentCheck{Contains treatment terms?}
    TreatmentCheck -->|Yes| TreatmentTemplate[Treatment Options Template]
    
    TreatmentCheck -->|No| TransmissionCheck{Contains transmission terms?}
    TransmissionCheck -->|Yes| TransmissionTemplate[Disease Transmission Template]
    
    TransmissionCheck -->|No| CodeCheck{Contains code terms?}
    CodeCheck -->|Yes| CodeTemplate[Code Example Template]
    
    CodeCheck -->|No| MortalityCheck{Contains mortality terms?}
    MortalityCheck -->|Yes| FreeForm[Free-form Generation]
    
    MortalityCheck -->|No| GeneralCheck{Contains general terms?}
    GeneralCheck -->|Yes| OverviewTemplate[General Overview Template]
    GeneralCheck -->|No| FreeForm
    
    classDef template fill:#cfc,stroke:#6f6,stroke-width:1px
    classDef check fill:#ccf,stroke:#66f,stroke-width:1px
    
    class SymptomCheck,TreatmentCheck,TransmissionCheck,CodeCheck,MortalityCheck,GeneralCheck check
    class SymptomTemplate,TreatmentTemplate,TransmissionTemplate,CodeTemplate,OverviewTemplate,FreeForm template
```

## Safety Agent Workflow

```mermaid
flowchart LR
    UserInput[User Input] --> InjectionCheck{Injection Check Agent}
    
    InjectionCheck -->|Prompt Injection Detected| Block1[Block & Explain]
    InjectionCheck -->|Safe| PolicyCheck{Policy Check Agent}
    
    PolicyCheck -->|Policy Violation Detected| Block2[Block & Explain]
    PolicyCheck -->|Safe| Router[Task Router]
    
    Block1 --> SafetyResponse[Safety Response to User]
    Block2 --> SafetyResponse
    
    classDef safety fill:#fcc,stroke:#f66,stroke-width:2px
    classDef normal fill:#cfc,stroke:#6f6,stroke-width:1px
    
    class InjectionCheck,PolicyCheck safety
    class Router,UserInput normal
```
