import asyncio
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.core.agent.workflow import (
    FunctionAgent,
    ToolCallResult,
    ToolCall
)
from llama_index.core.workflow import Context

llm = Ollama(model="llama3.2:1b",request_timeout=120.0)
Settings.llm = llm

SYSTEM_PROMPT = """\

You are an AI assistant for Tool calling.
Before helping, work with our tools to interact with our database.
"""

async def get_agent(tools: McpToolSpec):
    tools = await tools.to_tool_list_async()

    agent = FunctionAgent(
        name="Agent",
        description="agent that interacts with our database",
        tools=tools,
        llm=llm,
        system_prompt=SYSTEM_PROMPT
    )

    return agent

async def handle_user_message(
        message_content: str,
        agent: FunctionAgent,
        agent_context: Context,
        verbose: bool = False
):
    handler = agent.run(message_content, ctx=agent_context)
    async for event in handler.stream_events():
        if verbose and type(event) == ToolCall:
            print(f"Calling tool {event.tool_name}")
        elif verbose and type(event) == ToolCallResult:
            print(f"Tool {event.tool_name} returned {event.tool_output}")

    response = await handler
    return str(response)

async def main():
    mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
    mcp_tool = McpToolSpec(client=mcp_client)

    agent = await get_agent(mcp_tool)
    context = Context(agent)

    tools = await mcp_tool.to_tool_list_async()
    print("Available tools: \n")
    
    for tool in tools: 
        print(f"{tool.metadata.name}: {tool.metadata.description}")

    print("\nEnter 'exit' to quit")

    while True:

        try:
            user_input = input("Enter your message: ")
            if user_input.lower() == "exit":
                break

            resp = await handle_user_message(user_input, agent, context)
            print("Agent:", resp)
        
        except KeyboardInterrupt:
            print("\nExiting...")
            break

        except Exception as e:
            print(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())