from pydantic import BaseModel, Field
import json
import asyncio
from typing import List, Dict, Any, Optional
import traceback
import re
import collections  # For defaultdict

from openai import OpenAI
import httpx  # httpx is now assumed to be installed


class Pipe:
    class Valves(BaseModel):
        OPENAI_API_KEY: str = Field(
            default="",
            description="API key for authenticating requests to OpenAI API.",
        )
        JINA_API_KEY: str = Field(
            default="",
            description="API key for Jina AI services (e.g., Jina Search for web research and Jina Reader for scraping). Get yours at https://jina.ai.",
        )
        JINA_REGION: str = Field(
            default="global",
            description="Region for Jina AI endpoints: 'global' (default) or 'eu' for EU infrastructure.",
        )
        COORDINATOR_MODEL: str = Field(
            default="gpt-4o-mini",
            description="Model used for coordinating between agents, relevancy checks, and synthesizing (should be fast and efficient).",
        )
        THINKING_MODEL: str = Field(
            default="o1-mini",
            description="Model used for deep thinking, complex reasoning, and defining agents, also used for summarizing complex research.",
        )
        EXECUTION_MODEL: str = Field(
            default="gpt-4o",
            description="Model used for executing specialized tasks, often involving code generation or structured output.",
        )
        BROWSING_ENABLED: bool = Field(
            default=False,
            description="Whether to allow internet browsing capability for agents that need to gather information. Requires Jina AI API Key.",
        )
        MODEL_TIMEOUT: int = Field(
            default=60,
            description="Timeout in seconds for individual model API calls and external API calls (e.g., Jina AI).",
        )
        ENABLE_CACHING: bool = Field(
            default=True,
            description="Enable caching of identical model responses to save tokens and speed up repeated calls.",
        )
        TEMPERATURE: float = Field(
            default=0.7,
            description="Creativity level for model outputs. Lower (e.g., 0.1) for more deterministic/factual, higher (e.g., 0.9) for more creative.",
        )
        VISUALIZE_AGENTS: bool = Field(
            default=True,
            description="If true, emits detailed messages about agent execution flow for OpenWebUI to display.",
        )
        MAX_SEARCH_RESULTS: int = Field(
            default=3,
            description="Maximum number of search results to process for full content extraction via Jina Reader per search query.",
        )
        MAX_SUMMARY_TOKENS: int = Field(
            default=3000,
            description="Maximum number of tokens for a summarized research result, to prevent context overflow.",
        )
        SUMMARIZER_MODEL: str = Field(
            default="gpt-4o-mini",
            description="Model used for summarizing research results.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.client = None
        self.cache = {}  # Simple cache for model responses

        # Initialize the client if API key is provided
        if self.valves.OPENAI_API_KEY:
            try:
                self.client = OpenAI(
                    api_key=self.valves.OPENAI_API_KEY,
                )
            except Exception as e:
                print(f"Warning: Could not initialize OpenAI client: {str(e)}")

        # Determine Jina AI endpoints based on region valve
        jina_base_search_url = (
            "https://s.jina.ai/"
            if self.valves.JINA_REGION == "global"
            else "https://eu.s.jina.ai/"
        )
        jina_base_reader_url = (
            "https://r.jina.ai/"
            if self.valves.JINA_REGION == "global"
            else "https://eu.r.jina.ai/"
        )
        self.jina_search_endpoint = jina_base_search_url
        self.jina_reader_endpoint = jina_base_reader_url

    def pipes(self):
        """Define a single agent system model for OpenWebUI."""
        # Check for OpenAI API Key
        if not self.valves.OPENAI_API_KEY:
            return [
                {
                    "id": "error",
                    "name": "Agent System (OpenAI API Key Missing)",
                    "description": "Please provide your OpenAI API key in the 'Valves' settings.",
                }
            ]

        # Check for Jina AI browsing dependencies
        if self.valves.BROWSING_ENABLED:
            if not self.valves.JINA_API_KEY:
                return [
                    {
                        "id": "error",
                        "name": "Agent System (Jina API Key Missing for Browsing)",
                        "description": "Browsing is enabled but Jina AI API Key is missing. Please provide it in 'Valves' or disable browsing.",
                    }
                ]

        return [
            {
                "id": "agent-system",
                "name": "🤖 Multi-Agent System (OpenAI)",
                "description": "A collaborative multi-agent system powered by OpenAI that intelligently breaks down and executes tasks sequentially or in parallel, with web research capabilities via Jina AI.",
            }
        ]

    async def call_model(
        self, model: str, messages: List[Dict[str, str]], temperature: float
    ) -> str:
        """Helper function to call a model via OpenAI API using OpenAI library."""
        if not self.client:
            try:
                self.client = OpenAI(
                    api_key=self.valves.OPENAI_API_KEY,
                )
            except Exception as e:
                return f"Error initializing OpenAI client: {str(e)}"
        try:
            async with asyncio.timeout(self.valves.MODEL_TIMEOUT):
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model=model, messages=messages, temperature=temperature
                    ),
                )
            return response.choices[0].message.content
        except asyncio.TimeoutError:
            error_msg = f"Error: Request to model {model} timed out after {self.valves.MODEL_TIMEOUT} seconds."
            print(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error calling model {model}: {str(e)}"
            print(error_msg)
            # Attempt a fallback if the primary model call fails
            try:
                fallback_model = "gpt-3.5-turbo"  # A generally reliable fallback
                print(f"Attempting fallback with model: {fallback_model}")
                async with asyncio.timeout(self.valves.MODEL_TIMEOUT):
                    fallback_response = await loop.run_in_executor(
                        None,
                        lambda: self.client.chat.completions.create(
                            model=fallback_model,
                            messages=messages,
                            temperature=temperature,
                        ),
                    )
                return fallback_response.choices[0].message.content
            except Exception as fallback_e:
                print(f"Fallback also failed: {str(fallback_e)}")
                return f"Error calling model {model}: {str(e)}\nFallback also failed: {str(fallback_e)}"

    async def call_model_with_cache(
        self, model: str, messages: List[Dict[str, str]], temperature: float
    ) -> str:
        """Call a model, utilizing caching if enabled, to avoid redundant API calls."""
        if not self.valves.ENABLE_CACHING:
            return await self.call_model(model, messages, temperature)
        # Create a cache key using model, messages (converted to string), and temperature
        cache_key = (
            f"{model}_{hash(json.dumps(messages, sort_keys=True))}_{temperature}"
        )
        if cache_key in self.cache:
            return self.cache[cache_key]
        response = await self.call_model(model, messages, temperature)
        self.cache[cache_key] = response
        return response

    async def browse_for_information(
        self, query: str, agent_name: str, __event_emitter__=None
    ) -> str:
        """Performs web research using Jina AI Search API and then scrapes content with Jina AI Reader."""
        if not self.valves.BROWSING_ENABLED:
            return (
                "Web browsing is disabled. Enable it in the Valves settings if needed."
            )
        if not self.valves.JINA_API_KEY:
            return "Jina AI API Key is not configured for web research. Please add it to Valves."

        headers = {
            "Authorization": f"Bearer {self.valves.JINA_API_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        combined_content = []
        urls_accessed_for_logging = []
        try:
            async with httpx.AsyncClient(timeout=self.valves.MODEL_TIMEOUT) as client:
                # Step 1: Perform Search using Jina Search API
                search_payload = {
                    "q": query,
                    "count": self.valves.MAX_SEARCH_RESULTS,
                }
                search_response = await client.post(
                    self.jina_search_endpoint, headers=headers, json=search_payload
                )
                search_response.raise_for_status()
                search_results = search_response.json()

                if (
                    not search_results
                    or not search_results.get("data")
                    or not search_results["data"]
                ):
                    return f"No useful search results found for the query: '{query}'."

                urls_to_read = []
                for item in search_results["data"]:
                    if item.get("url"):
                        urls_to_read.append(item["url"])

                if not urls_to_read:
                    return f"No valid URLs found in search results for: '{query}'."

                # Step 2: Read Content from URLs using Jina Reader API
                read_tasks = []
                for url in urls_to_read:
                    read_tasks.append(
                        client.post(
                            self.jina_reader_endpoint,
                            headers=headers,
                            json={"url": url},
                        )
                    )
                read_responses = await asyncio.gather(
                    *read_tasks, return_exceptions=True
                )

                for i, res in enumerate(read_responses):
                    url = urls_to_read[i]
                    if isinstance(res, httpx.Response):
                        try:
                            res.raise_for_status()
                            read_result = res.json()
                            content = read_result.get("data", {}).get("content")
                            if content:
                                combined_content.append(
                                    f"--- Source: {url} ---\n{content}\n"
                                )
                                urls_accessed_for_logging.append(url)
                        except httpx.HTTPStatusError as e:
                            combined_content.append(
                                f"--- Error reading {url}: HTTP {e.response.status_code} ---\n"
                            )
                        except json.JSONDecodeError:
                            combined_content.append(
                                f"--- Error decoding JSON from {url} ---\n"
                            )
                        except Exception as e:
                            combined_content.append(
                                f"--- Unexpected error reading {url}: {e} ---\n"
                            )
                    else:
                        combined_content.append(
                            f"--- Request to {url} failed: {res} ---\n"
                        )

                if not combined_content:
                    return f"No readable content extracted from any of the search results for: '{query}'."

                # Emit event for OpenWebUI to visualize accessed URLs
                if __event_emitter__ and urls_accessed_for_logging:
                    await __event_emitter__(
                        {
                            "type": "web_sources_accessed",
                            "agent": agent_name,
                            "query": query,
                            "urls": urls_accessed_for_logging,
                        }
                    )
                print(f"Accessed URLs: {urls_accessed_for_logging}")
                return "\n".join(combined_content)

        except httpx.RequestError as e:
            return f"Error connecting to Jina AI API (search or read) for query '{query}': {e}"
        except httpx.HTTPStatusError as e:
            return f"Jina AI Search API returned an error status ({e.response.status_code}) for query '{query}': {e.response.text}"
        except Exception as e:
            return f"An unexpected error occurred during Jina AI operations for query '{query}': {e}\nTraceback: {traceback.format_exc()}"

    async def _get_research_queries(self, task: str) -> List[str]:
        """
        Asks the Coordinator model to identify specific research queries needed for the task.
        """
        system_prompt = """You are a shrewd research planner. Given an overall task, determine if external web research is needed.
If so, identify specific, concise search queries (questions or keywords) that, if answered, would significantly help in completing the task.
Think step-by-step about what information is missing from a general LLM's knowledge base (e.g., current events, specific real-time data, very niche topics).
If no web research appears necessary, state 'NONE'.
If research is needed, provide a JSON array of strings, where each string is a search query.
Limit your responses to at most 3 search queries.
Example:
Task: 'What is the current status of the ITER fusion project and its expected completion date?'
Response: ["ITER fusion project current status", "ITER completion date", "recent news ITER fusion"]

Task: 'Explain the theory of relativity.'
Response: NONE
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Overall Task: {task}"},
        ]
        response = await self.call_model_with_cache(
            self.valves.COORDINATOR_MODEL,
            messages,
            temperature=0.1,
        )
        try:
            if response.strip().upper() == "NONE":
                return []
            queries = json.loads(response)
            if not isinstance(queries, list) or not all(
                isinstance(q, str) for q in queries
            ):
                raise ValueError("Response is not a valid JSON list of strings.")
            return queries
        except json.JSONDecodeError:
            print(
                f"Warning: _get_research_queries response not valid JSON: {response}. Attempting regex fallback."
            )
            matches = re.findall(r'"([^"]*)"', response)
            if matches:
                return matches
            return []
        except Exception as e:
            print(f"Error parsing research queries: {e}. Raw response: {response}")
            return []

    async def _summarize_research_results(
        self, raw_web_content: str, query: str, __event_emitter__=None
    ) -> str:
        """
        Summarizes raw web content using a thinking model to extract key information.
        """
        if not raw_web_content.strip():
            return f"No content available for query: '{query}'."

        system_prompt = f"""You are a highly skilled research summarizer. Your task is to extract and summarize the most critical and relevant information from the provided web content related to the query: "{query}".
Focus on answering the query directly with facts, figures, and key insights.
- Consolidate information from different sources.
- Eliminate redundancy.
- Note any conflicting information present.
- Be concise but retain all essential details.
- The output should provide a direct summary, not an analysis or opinion.
Maximum length for the summary is approximately {self.valves.MAX_SUMMARY_TOKENS} tokens. Be ruthless in eliminating fluff."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Raw Web Content:\n{raw_web_content}"},
        ]

        summarized_content = await self.call_model_with_cache(
            self.valves.SUMMARIZER_MODEL,
            messages,
            temperature=0.2,
        )

        return summarized_content

    async def define_agents(self, task: str) -> List[Dict[str, Any]]:
        """Uses the thinking model to define specialized agents and their execution order for a given task."""
        system_prompt = """You are an AI system architect. Given a task, create a team of 3-7 specialized agents to solve it effectively.
Each agent must have a clear, unique role, specialty, and purpose. Critically, you must assign an 'order' (integer starting from 0)
to each agent, defining their execution sequence. Agents with the same 'order' run in parallel. Agents with a higher 'order'
will only start after all agents with a lower 'order' have completed.

IMPORTANT: Web research will be conducted centrally based on queries determined by the coordinator. Therefore, subsequent agents will receive _summarized_ research context. Your "Researcher" or "Analyst" type agents should focus on _analyzing_ this provided information, not performing new searches. Their tasks should reflect this (e.g., "Analyze compiled research on X", "Extract key data from provided context").

Ensure the 'Coordinator' agent is always present, has an 'order' of 0, and is responsible for overall management and final synthesis.
Other agents should typically follow, with research-oriented agents often having a lower 'order' than analysis or implementation agents.
Avoid creating agents with overlapping responsibilities.

Return your response as a JSON array of agent objects with this structure:
[
  {
    "name": "Agent name (be creative and descriptive)",
    "role": "Brief role description focusing on their contribution",
    "specialty": "What this agent is exceptionally good at (e.g., 'Data Analysis', 'Code Generation', 'Strategic Planning', 'Information Synthesis')",
    "tasks": ["List of specific, actionable tasks for this agent to perform"],
    "order": 0
  }
]
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {task}"},
        ]
        try:
            response = await self.call_model_with_cache(
                self.valves.THINKING_MODEL,
                messages,
                temperature=self.valves.TEMPERATURE,
            )
            # Use regex to robustly extract JSON if it's embedded within text
            json_match = re.search(r"\[\s*\{.*\}\s*\]", response, re.DOTALL)
            if json_match:
                agents = json.loads(json_match.group(0))
                # Ensure coordinator is present and has order 0
                if not any(a.get("name") == "Coordinator" for a in agents):
                    print(
                        "Warning: Coordinator agent missing from AI-defined agents. Adding default."
                    )
                    agents.insert(
                        0,
                        {
                            "name": "Coordinator",
                            "role": "Manages workflow and synthesizes information",
                            "specialty": "Coordination and decision making",
                            "tasks": [
                                "Coordinate other agents",
                                "Synthesize final answer",
                            ],
                            "order": 0,
                        },
                    )
                # Ensure all agents have an 'order' and it's an integer
                for agent in agents:
                    if not isinstance(agent.get("order"), int):
                        agent["order"] = 0
                return agents
            else:
                print(
                    "Could not extract agent JSON from response, using fallback agents."
                )
                raise ValueError("Could not extract agent JSON from response")
        except Exception as e:
            print(f"Error defining agents: {str(e)}. Using fallback agents.")
            return [
                {
                    "name": "Coordinator",
                    "role": "Manages workflow and synthesizes information",
                    "specialty": "Coordination and decision making",
                    "tasks": ["Coordinate other agents", "Synthesize final answer"],
                    "order": 0,
                },
                {
                    "name": "Analyst",
                    "role": "Analyzes the provided information",
                    "specialty": "Data analysis and interpretation",
                    "tasks": [
                        "Analyze provided context",
                        "Formulate insights",
                    ],
                    "order": 1,
                },
                {
                    "name": "Implementer",
                    "role": "Translates findings into actionable steps",
                    "specialty": "Practical implementation",
                    "tasks": [
                        "Convert ideas to actions",
                        "Provide concrete solutions",
                    ],
                    "order": 2,
                },
            ]

    async def run_agent(
        self, agent: Dict[str, Any], context: str, task: str, __event_emitter__=None
    ) -> str:
        """Runs a single agent on its assigned task, incorporating context."""
        # Determine appropriate model based on agent role/task
        model_to_use = self.valves.EXECUTION_MODEL

        agent_name_lower = agent.get("name", "").lower()
        agent_role_lower = agent.get("role", "").lower()
        agent_specialty_lower = str(agent.get("specialty", "")).lower()
        agent_tasks_combined_lower = " ".join(agent.get("tasks", [])).lower()

        if agent_name_lower == "coordinator" or "coordinate" in agent_role_lower:
            model_to_use = self.valves.COORDINATOR_MODEL
        elif any(
            kw in agent_specialty_lower
            for kw in [
                "thinking",
                "analysis",
                "reasoning",
                "strategic",
                "synthesis",
                "analyst",
            ]
        ) or any(
            kw in agent_tasks_combined_lower
            for kw in ["analyze", "evaluate", "interpret", "synthesize"]
        ):
            model_to_use = self.valves.THINKING_MODEL

        base_system_prompt = f"""You are {agent.get('name', 'An AI agent')}, an AI agent with the role: {agent.get('role', 'undefined')}.
Your specialty is: {agent.get('specialty', 'general problem solving')}.
Your specific tasks for this session are: {', '.join(agent.get('tasks', ['to complete a specific task']))}.
Your goal is to contribute detailed and specific information to the overall task based on the provided context.
Avoid generic statements. Provide concrete examples, data points, and actionable insights relevant to your role.
The final response will incorporate and synthesize your detailed analysis. Be thorough."""

        messages = [
            {"role": "system", "content": base_system_prompt},
            {
                "role": "user",
                "content": f"Original Task: {task}\n\nContext and previously gathered information:\n{context}\n\nYour specific task to complete now:",
            },
        ]

        if __event_emitter__ and self.valves.VISUALIZE_AGENTS:
            await __event_emitter__(
                {
                    "type": "agent_status",
                    "agent": agent["name"],
                    "status": "Thinking...",
                    "detail": f"Using model: {model_to_use}",
                }
            )

        result = await self.call_model_with_cache(
            model_to_use, messages, temperature=self.valves.TEMPERATURE
        )

        if __event_emitter__ and self.valves.VISUALIZE_AGENTS:
            await __event_emitter__(
                {
                    "type": "agent_result",
                    "agent": agent["name"],
                    "result": result[:500] + "..." if len(result) > 500 else result,
                }
            )
            await __event_emitter__(
                {
                    "type": "agent_status",
                    "agent": agent["name"],
                    "status": "Completed.",
                }
            )
        return result

    async def synthesize_results(
        self, task: str, agent_results: Dict[str, str], __event_emitter__=None
    ) -> str:
        """Synthesizes results from all agents into a final, comprehensive response."""
        system_prompt = """You are a highly skilled synthesis engine. Your job is to combine the contributions of multiple AI agents into a single, cohesive, and comprehensive final response.
Carefully analyze all provided agent outputs. Your process must include:
1. Consolidation: Merge related information from different agents.
2. Redundancy Elimination: Identify and remove duplicate content.
3. Contradiction Resolution: Harmonize conflicting information or clearly state discrepancies.
4. Logical Structuring: Organize the information into a well-structured format.
5. Direct Answer: Directly and thoroughly answer the original user task.
6. Completeness: Ensure all aspects of the original task are addressed.
7. Specificity: Include concrete details, data points, and actionable insights.
Remember: The user needs the ACTUAL, COMPLETE, and DETAILED CONTENT."""

        agent_outputs_formatted = "\n\n".join(
            [
                f"=== Output from {name} ===\n{result}"
                for name, result in agent_results.items()
            ]
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Original task: {task}\n\nAgent contributions to synthesize:\n{agent_outputs_formatted}\n\nProvide a comprehensive final response:",
            },
        ]

        if __event_emitter__ and self.valves.VISUALIZE_AGENTS:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Synthesizing final response...",
                        "done": False,
                    },
                }
            )

        final_response = await self.call_model_with_cache(
            self.valves.COORDINATOR_MODEL, messages, temperature=0.5
        )

        if __event_emitter__ and self.valves.VISUALIZE_AGENTS:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Final synthesis complete.", "done": True},
                }
            )
        return final_response

    async def is_relevant(
        self, information: str, agent: Dict[str, Any], task: str
    ) -> bool:
        """Determines if a piece of information is relevant to a specific agent's task."""
        system_prompt = f"""You are a relevance evaluator. Given a piece of information and an agent's definition, determine if the information is directly relevant.
Agent Name: {agent.get('name', 'Unknown Agent')}
Agent Role: {agent.get('role', 'No Role')}
Agent Specialty: {agent.get('specialty', 'No Specialty')}
Agent Tasks: {', '.join(agent.get('tasks', []))}
Overall Task: {task}
Respond with 'YES' if relevant, otherwise 'NO'. Be strict."""

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Information:\n{information}\n\nIs this relevant? (YES/NO)",
            },
        ]
        response = await self.call_model_with_cache(
            self.valves.COORDINATOR_MODEL, messages, temperature=0.1
        )
        return "YES" in response.upper()

    async def pipe(self, body: dict, __event_emitter__=None) -> str:
        """Main function orchestrating the multi-agent system workflow with sequential phases."""
        active_tasks = set()
        progress_messages = []

        try:
            messages = body.get("messages", [])
            user_messages = [msg for msg in messages if msg.get("role") == "user"]
            if not user_messages:
                return "Please provide a task for the agents to work on."
            task = user_messages[-1]["content"]

            if __event_emitter__ and self.valves.VISUALIZE_AGENTS:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "🧠 Multi-agent system initializing...",
                            "done": False,
                        },
                    }
                )

            # Step 1: Define agents
            progress_messages.append("🔍 Analyzing task and defining agent team...\n")
            define_agents_task = asyncio.create_task(self.define_agents(task))
            active_tasks.add(define_agents_task)
            agents = await define_agents_task
            active_tasks.remove(define_agents_task)

            # Sort agents by order
            agents.sort(key=lambda a: a.get("order", 0))
            agents_by_order = collections.defaultdict(list)
            for agent in agents:
                agents_by_order[agent["order"]].append(agent)
            sorted_orders = sorted(agents_by_order.keys())

            progress_messages.append(
                f"✅ Agent team defined with {len(agents)} agents across {len(sorted_orders)} phases:\n"
            )
            for order_idx in sorted_orders:
                progress_messages.append(
                    f"  Phase {order_idx}: {[a['name'] for a in agents_by_order[order_idx]]}\n"
                )

            if __event_emitter__ and self.valves.VISUALIZE_AGENTS:
                await __event_emitter__({"type": "agents_defined", "agents": agents})

            overall_research_context = ""
            # Centralized Research Phase
            if self.valves.BROWSING_ENABLED:
                progress_messages.append("\n🌍 Initiating centralized web research...\n")
                research_queries = await self._get_research_queries(task)
                if research_queries:
                    progress_messages.append(
                        f"  🧠 Coordinator identified {len(research_queries)} research queries.\n"
                    )
                    all_summarized_research = []
                    for i, query in enumerate(research_queries):
                        raw_results = await self.browse_for_information(
                            query, "Centralized_Researcher", __event_emitter__
                        )
                        if "Error" not in raw_results and raw_results.strip():
                            summarized_piece = await self._summarize_research_results(
                                raw_results, query, __event_emitter__
                            )
                            all_summarized_research.append(
                                f"--- Research Summary for '{query}' ---\n{summarized_piece}\n"
                            )
                            progress_messages.append(
                                f"    ✅ Summarized results for '{query}'.\n"
                            )

                    if all_summarized_research:
                        overall_research_context = "\n".join(all_summarized_research)
                        progress_messages.append(
                            "  ✅ Centralized web research complete.\n"
                        )

            # Initialize agent contexts
            agent_contexts = {}
            for agent in agents:
                initial_context = f"The original task is: {task}\n"
                if overall_research_context:
                    initial_context += f"\n\n--- Research Context ---\n{overall_research_context}\n"
                agent_contexts[agent["name"]] = initial_context

            all_completed_agent_results = {}

            # Run agents in phases
            for current_order in sorted_orders:
                phase_agents = agents_by_order[current_order]
                phase_message = (
                    f"\nPhase {current_order}: {', '.join([a['name'] for a in phase_agents])}\n"
                )
                progress_messages.append(phase_message)

                current_phase_tasks = []
                for agent in phase_agents:
                    task_obj = asyncio.create_task(
                        self.run_agent(
                            agent,
                            agent_contexts[agent["name"]],
                            task,
                            __event_emitter__,
                        )
                    )
                    active_tasks.add(task_obj)
                    current_phase_tasks.append((agent["name"], task_obj))

                # Wait for phase completion
                for agent_name, task_obj in current_phase_tasks:
                    try:
                        result = await task_obj
                        active_tasks.remove(task_obj)
                        all_completed_agent_results[agent_name] = result
                        progress_messages.append(
                            f"  ✅ {agent_name} completed.\n"
                        )

                        # Propagate results to future agents
                        for future_agent in agents:
                            if future_agent["name"] != agent_name:
                                if future_agent["order"] > current_order:
                                    if await self.is_relevant(result, future_agent, task):
                                        agent_contexts[future_agent["name"]] += (
                                            f"\n\nOutput from {agent_name}:\n{result}\n"
                                        )
                                elif future_agent["name"] == "Coordinator":
                                    agent_contexts[future_agent["name"]] += (
                                        f"\n\nOutput from {agent_name}:\n{result}\n"
                                    )
                    except Exception as e:
                        progress_messages.append(f"  ❌ {agent_name} failed: {str(e)}\n")
                        print(f"Error running {agent_name}: {traceback.format_exc()}")

            # Synthesize final results
            progress_messages.append("\n🔄 Synthesizing final response...\n")
            synthesis_task = asyncio.create_task(
                self.synthesize_results(task, all_completed_agent_results, __event_emitter__)
            )
            active_tasks.add(synthesis_task)
            final_result = await synthesis_task
            active_tasks.remove(synthesis_task)
            progress_messages.append("✅ Final synthesis complete.\n")

            output = (
                "".join(progress_messages)
                + "\n\n--- FINAL RESPONSE ---\n\n"
                + final_result
            )

            # Cancel any remaining tasks
            for task_obj in list(active_tasks):
                if not task_obj.done():
                    task_obj.cancel()

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "Multi-agent process finished.",
                            "done": True,
                        },
                    }
                )
            return output

        except Exception as e:
            # Emergency cancellation
            for task_obj in list(active_tasks):
                if not task_obj.done():
                    task_obj.cancel()

            trace = traceback.format_exc()
            error_message = f"An error occurred: {str(e)}\n\nTraceback:\n{trace}"
            print(error_message)

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "Multi-agent process failed.",
                            "done": True,
                            "error": True,
                        },
                    }
                )
            return "".join(progress_messages) + "\n\n--- ERROR ---\n\n" + error_message
