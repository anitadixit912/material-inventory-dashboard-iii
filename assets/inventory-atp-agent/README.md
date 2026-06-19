# Inventory ATP Agent

An AI agent that analyzes inventory availability, explains stock drops, checks order feasibility via ATP, simulates corrective options, and executes approved supply chain actions.

## Overview

Uses A2A Protocol, LangGraph, LiteLLM, and SAP Cloud SDK.

## Structure

- `app/main.py` - A2A server entry
- `app/agent_executor.py` - Request handling
- `app/agent.py` - Agent logic
