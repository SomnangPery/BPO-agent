from langchain.agents import AgentExecutor, create_react_agent
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from ic_agent.config import AGENT_MODEL, ANTHROPIC_API_KEY
from ic_agent.tools import build_tools

def create_ic_agent():
    llm = ChatAnthropic(model=AGENT_MODEL, anthropic_api_key=ANTHROPIC_API_KEY, temperature=0)
    tools = build_tools()
    
    template = """You are the IC Agent, a project analysis assistant.
Your goal is to help IC staff analyze project progress based on files in Google Drive.

The model only deals with:
1. Projects (folder name = project name)
2. Files (OPPM, SRS, and Report files)
3. Submissions and Analysis

There are NO students or individual members. Everything belongs to the project.

TOOLS:
------
You have access to the following tools:
{tools}

To use a tool, please use the following format:
Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action

When you have a response for the user, or if you do not need to use a tool, you MUST use the format:
Thought: Do I need to use a tool? No
Final Answer: [your response here]

USER QUERY: {input}

{agent_scratchpad}"""

    prompt = PromptTemplate.from_template(template)
    agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
