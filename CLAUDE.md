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

\#\# Architecture decisions already made. Do not revisit.
\- TWO model calls per turn: classify, then reason. Never merge them.
  The classification determines which tools are exposed. Merging
  destroys the structural guardrail.
\- No agent framework. No pytest. No pandas.
\- The log schema is frozen. Do not add fields.
\- `confirmed` flips to True only on an explicit user affirmation,
  never inferred from tone or context.
\- If you believe one of these is wrong, say so and stop. Do not
  implement your preferred alternative.