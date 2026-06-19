import logging

from a2a.server.agent_execution import AgentExecutor as A2AAgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from agent import SampleAgent
from mcp_tools import get_mcp_tools, set_user_token_for_tools, reset_user_token_for_tools

logger = logging.getLogger(__name__)


class AgentExecutor(A2AAgentExecutor):
    def __init__(self):
        self.agent = SampleAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent and stream results back via A2A protocol.

        Discovers and loads MCP tools from Agent Gateway before each execution.
        Tools are fetched per-request since both listing and calling require user credentials.

        Args:
            context: Request context containing user input and task info
            event_queue: Queue for publishing task status updates

        Raises:
            ServerError: On unrecoverable agent execution errors
        """
        query = context.get_user_input()
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        # Extract user token from A2A ServerCallContext headers
        user_token = None
        if hasattr(context, 'call_context') and hasattr(context.call_context, 'state'):
            headers = context.call_context.state.get('headers', {})
            auth_header = headers.get('authorization') or headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                user_token = auth_header[7:]  # Remove "Bearer " prefix
                logger.info("Extracted user token for MCP tool calls")

        # Load MCP tools if user token is available
        tools = []

        if not user_token:
            logger.warning("No user token available - running agent without tools")
        else:
            try:
                tools = await get_mcp_tools(user_token=user_token)
            except ValueError as e:
                # User token validation error
                logger.error(f"Invalid user token: {e}")
            except Exception as e:
                # Network, AGW, or other infrastructure errors
                logger.error(f"Failed to load tools from Agent Gateway: {e}")

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        # Set user token in context for tool execution
        # This allows cached tools to access per-request user credentials
        token_ctx = set_user_token_for_tools(user_token) if user_token and tools else None

        try:
            # Stream agent responses with tools
            async for item in self.agent.stream(query, task.context_id, tools=tools):
                is_task_complete = item["is_task_complete"]
                require_user_input = item["require_user_input"]
                content = item["content"]

                if require_user_input:
                    # Agent requests more input
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(content, task.context_id, task.id),
                        final=True,
                    )
                    break
                elif is_task_complete:
                    # Completed: add artifact and complete task
                    await updater.add_artifact(
                        [Part(root=TextPart(text=content))], name="agent_result"
                    )
                    await updater.complete()
                    break
                else:
                    # Working status update
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(content, task.context_id, task.id),
                    )
        except Exception as e:
            logger.exception("Agent execution error")
            raise ServerError(error=InternalError()) from e
        finally:
            # Always reset token context after tool execution
            if token_ctx is not None:
                reset_user_token_for_tools(token_ctx)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise ServerError(error=UnsupportedOperationError())
