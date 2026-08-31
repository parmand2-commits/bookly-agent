# Bookly support agent

A customer support agent for a fictional online bookstore. Chat, multi-turn, with tools,
retrieval, guardrails and an eval suite.

Built for Decagon's Solutions Engineering take-home.

---

## The thesis

**The unit of a support agent is not the prompt. It's the procedure.**

A prompt describes how an agent should behave. A procedure declares it, as data the system
enforces rather than language the model interprets.

Which tools are reachable, what the agent may never promise, when it has to stop and hand
over: all of that lives in a YAML file a CX manager can edit. No code change, no deploy.

The corollary is the part people skip. Refusing to answer is a designed outcome here, not a
failure mode.

---

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then put your Anthropic key in it
```

Chat with the agent:

```bash
python3 cli.py CUST-1002
```

It prints a reasoning panel after every reply: intent, procedure loaded, tools called,
retrieval scores, escalation status. That panel is the point. The conversation is just the
surface.

Try these:

| Customer | Message | What you should see |
|---|---|---|
| `CUST-1004` | `where is my order 4501` | one tool, no escalation |
| `CUST-1001` | `where is my stuff` | **zero tools**, the agent asks which order |
| `CUST-1002` | `I want to return one of the items from my order 4402` | four turns before anything is created |
| `CUST-1002` | `I want to return the book from order 4310` | escalation, no RMA, a reason you can act on |

Run the evals:

```bash
python3 evals/run_evals.py
```

Twenty-five instances, five categories, roughly thirty seconds and about 35 cents.

---

## How a turn works

Two model calls. They are never merged, and that is the whole design.

**The first classifies.** A fast model, forced to call a single tool whose only parameter is
an enum. The answer is structured because it cannot be anything else. No free text to parse.

**That classification picks a procedure**, and the procedure decides which tools the second
call is even shown.

**The second reasons.** Bounded at five tool turns. Conversation history persists across
turns, capped at twenty entries.

**Then three output checks** run before anything reaches the customer. No policy claim
without a confident retrieval behind it. No order or customer id that doesn't belong to this
session. No action claimed that the system didn't actually take.

The reason for two calls instead of one: in an order-status flow, `create_return` isn't
discouraged in a prompt. It is absent from the list the model receives. You cannot argue a
model out of a tool it was never handed.

### Four knowledge layers

| Layer | Format | Answers | Reached by |
|---|---|---|---|
| Data | JSON | what happened | tools |
| Policies | Markdown | what is true | retrieval |
| Procedures | YAML | what we do, in what order | detected intent |
| Session | loaded once | who is speaking | startup |

Each one has a different owner in a real company. That was the point.

---

## Three decisions worth defending

### Behaviour lives in files

Per-intent YAML loaded at runtime instead of one large system prompt.

Cost: more plumbing, and an intent nobody wrote a procedure for escalates rather than
improvising.

Worth it because a CX manager edits `never:` or `escalate_if:` in a text file and the agent's
behaviour changes on the next message.

### Retrieval is lexical, and I know where that breaks

Keyword matching over twelve short policy files, weighted by term rarity, with hand-written
aliases for the phrasings customers actually use. No vector store.

At this corpus size embeddings buy nothing and cost you an explainable score. My threshold is
1.5 because covered questions score between 2.5 and 4.3 and the two deliberate coverage gaps
top out at 0.78. I put the line in the gap.

The limit is measured, not assumed. The query `return window` scores 1.078 and no alias can
lift it: both its tokens are already in the document and one of them is common enough across
the corpus that rarity weighting flattens it. That is the point where this approach stops
paying.

### A claimed action has to be a performed action

During testing the agent wrote *your escalation has already been submitted* on a turn where
nothing had escalated. No log line. No human notified.

The escalation marker is a convention, so prose and structure can drift apart. There is now a
check for it: if a reply says it escalated and nothing did, the system escalates for real and
writes the log line. The sentence the customer read becomes true.

An identifier leak is handled differently, because it can't be undone. That reply gets
replaced.

---

## What the numbers say

I ran the suite three times without changing anything.

```
overall        48% – 56%
clarification  50% – 100%
edge           67% – 100%
guardrail      67%
nominal        43%
refusal        29% – 57%
```

Across the two runs I kept full data for, 44% of instances passed both, 32% failed both, and
24% flipped. The ones that flip depend on how the model happens to phrase a search query, or
whether it volunteers a tool call nobody required. Chasing them means aiming at a moving
target.

Structural defects: **zero**, in every run. Not once did a case reach a tool its procedure had
blocked. That is the difference between a guarantee written in code and a behaviour you hope
the model reproduces.

Median latency is 7.3 seconds per turn. Cost is about 1.2 cents.

A single pass rate is one sample. Report the band, and report it by category, because
`clarification` and `guardrail` fail for completely different reasons and get fixed by
completely different people.

---

## What I'd change first

Hybrid retrieval, once the alias list becomes the bottleneck. It already has, for one query,
and I can point at the number.

After that, a regression gate on procedure edits. Procedures are meant to be edited by people
who aren't engineers, and right now nothing checks an edit until someone tries it in a real
conversation. But a quarter of cases flip between identical runs, so that gate needs several
runs per change. Operator ownership isn't safe until it exists.

Third, the escalation reasons are model-written free text. The same trigger shows up under
three different phrasings across runs, which makes the escalation log hard to aggregate. It
should count the procedure's own `escalate_if` sentence, which is normalised, not the model's
explanation.

---

## Repo map

```
data/
  raw/*.csv          two CRM-style exports, deliberately messy
  policies/*.md      twelve policy files, aliases in the frontmatter
  *.json             seeded once, offline, committed
  seed_report.txt    the rows the loader refused, and why
procedures/*.yaml    two procedures: order status, returns
src/
  config.py          every tunable constant
  procedures.py      loads and validates YAML
  retrieval.py       keyword search, rarity-weighted
  tools.py           three tools, ownership checks in Python
  session.py         customer context, loaded once
  guardrails.py      delimiters and output checks
  logging.py         one JSON line per turn, seventeen fields
  agent.py           the loop
evals/
  cases.yaml         seventeen cases, written before the agent existed
  run_evals.py       replays them, reports by category
scripts/             seeding, threshold tuning, layer checks
cli.py               chat with the reasoning panel
```

### A note on the data

The CSVs are messy on purpose. Mixed date formats, inconsistent status casing, semicolon
delimiters and a UTF-8 BOM because that's what Excel produces in France. Two of the
thirty-three rows are unusable and the loader rejects them, writes down why, and never tries
to repair them.

`seed_report.txt` is the artefact. In a real deployment that file is the first conversation
you have with the customer's data team, and it's usually the one that sets the timeline.

### A note on the tests

The seventeen cases were written before any agent code existed. That wasn't discipline, it was
useful: writing them surfaced two architectural gaps I hadn't seen on paper, and a third much
later. Four of the seventeen are happy paths. The other thirteen check that the agent refuses,
asks, or stops.

A suite that only checks what a system does well has never tested a guardrail.
