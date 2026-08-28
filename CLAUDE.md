\# Bookly Support Agent

\#\# Thesis  
The unit of a support agent is not the prompt, it's the procedure.  
Behaviour lives in declarative YAML, not in the system prompt.

\#\# Hard constraints  
\- No agent frameworks. No LangChain, CrewAI, LlamaIndex.  
\- Anthropic SDK \+ Python stdlib only. requests allowed.  
\- No vector database. Keyword search over policy files.  
\- Every function must be explainable in one sentence.  
\- Every network call wrapped in try/except.  
\- Every loop bounded.  
\- Secrets in env vars only.

\#\# Architecture invariants  
\- One agent loop, max 5 tool turns  
\- Tools exposed \= tools\_allowed from the loaded procedure  
\- customer\_id comes from session, never from user input  
\- Every turn writes a structured JSON log line

\#\# Style  
\- Explicit over clever. This code will be read aloud in an interview.  
