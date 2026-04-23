import asyncio
import atexit
import functools
import time
from concurrent.futures import ThreadPoolExecutor
from logging import getLogger
from typing import Any, Callable

from novastack.core.llms.types import ChatMessage, ChatResponse, CompletionResponse
from novastack.core.observability.types import PayloadRecord
from novastack.core.prompts.utils import extract_template_vars

logger = getLogger(__name__)

# Thread pool for callback execution in synchronous contexts
# Uses 4 workers for balanced throughput
_callback_executor = ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="obs_callback_manager"
)
atexit.register(_callback_executor.shutdown, wait=False)


async def _process_chat_callback(
    callback_manager_fns: Any,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    llm_return_val: ChatResponse,
    response_time: int,
) -> None:
    """
    Process observability callback for chat-based LLMs.

    Extracts system_prompt, template_variables, and sends payload to callback manager.
    """
    try:
        # Extract input messages
        if len(args) > 0 and isinstance(args[0], ChatMessage):
            input_chat_messages = args[0]
        elif "messages" in kwargs:
            input_chat_messages = [
                ChatMessage.model_validate(msg) for msg in kwargs["messages"]
            ]
        else:
            raise ValueError("No messages provided in positional or keyword arguments")

        # Get the user's latest message after each interaction to chat observability.
        user_messages = [msg for msg in input_chat_messages if msg.role == "user"]
        last_user_message = user_messages[-1].content if user_messages else None

        # Get the system/instruct (top) messages to chat observability.
        top_system_messages = []
        for msg in input_chat_messages:
            if msg.role == "system":
                top_system_messages.append(msg.content)
            else:
                break  # stop at the first non-system message

        system_prompt = "\n".join(top_system_messages) if top_system_messages else None

        # Extract template variables values from the prompt template if available
        template_var_values = (
            extract_template_vars(
                callback_manager_fns.prompt_template.template,
                (system_prompt or ""),
            )
            if callback_manager_fns.prompt_template
            else {}
        )

        if callback_manager_fns.input_field_name:
            template_var_values[callback_manager_fns.input_field_name] = last_user_message

        callback = callback_manager_fns(
            payload=PayloadRecord(
                system_prompt=(system_prompt or ""),
                input_text=last_user_message,
                prompt_variables=list(template_var_values.keys()),
                prompt_variable_values=template_var_values,
                generated_text=llm_return_val.message.content,
                input_token_count=llm_return_val.raw["usage"]["prompt_tokens"],
                generated_token_count=llm_return_val.raw["usage"]["completion_tokens"],
                response_time=response_time,
            )
        )

        if asyncio.iscoroutine(callback):
            await callback

    except Exception as e:
        logger.error(
            f"Unexpected error in observability callback manager: {e}", exc_info=True
        )


def _run_chat_callback(
    callback_manager_fns: Any,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    llm_return_val: ChatResponse,
    response_time: int,
) -> None:
    """
    Wrapper to run async callback via ThreadPoolExecutor.
    """
    asyncio.run(
        _process_chat_callback(
            callback_manager_fns, args, kwargs, llm_return_val, response_time
        )
    )


def llm_chat_callback() -> Callable:
    """
    Decorator to wrap observability method with llm.
    Looks for observability instances in `self.callback_manager`. For chat-based LLMs (/chat/completion).
    """

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def async_wrapper(self, *args, **kwargs):
            callback_manager_fns = getattr(self, "callback_manager", None)

            start_time = time.perf_counter()
            llm_return_val = f(self, *args, **kwargs)
            response_time = int((time.perf_counter() - start_time) * 1000)

            if callback_manager_fns:
                try:
                    # Try to use existing event loop (async)
                    loop = asyncio.get_running_loop()
                    loop.create_task(
                        _process_chat_callback(
                            callback_manager_fns,
                            args,
                            kwargs,
                            llm_return_val,
                            response_time,
                        )
                    )
                except RuntimeError:
                    # No event loop - Use ThreadPoolExecutor (sync)
                    _callback_executor.submit(
                        _run_chat_callback,
                        callback_manager_fns,
                        args,
                        kwargs,
                        llm_return_val,
                        response_time,
                    )

            return llm_return_val

        return async_wrapper

    return decorator


async def _process_completion_callback(
    callback_manager_fns: Any,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    llm_return_val: CompletionResponse,
    response_time: int,
) -> None:
    """
    Process observability callback for completion-based LLMs.

    Extracts prompt, template_variables, and sends payload to callback manager.
    """
    try:
        # Extract input prompt
        if len(args) > 0 and isinstance(args[0], str):
            input_prompt = args[0]
        elif "prompt" in kwargs:
            input_prompt = kwargs["prompt"]
        else:
            raise ValueError("No prompt provided in positional or keyword arguments")

        # Extract template variables values from the prompt template if available
        template_var_values = (
            extract_template_vars(
                callback_manager_fns.prompt_template.template,
                input_prompt or "",
            )
            if callback_manager_fns.prompt_template
            else {}
        )

        callback = callback_manager_fns(
            payload=PayloadRecord(
                system_prompt=input_prompt or "",
                prompt_variables=list(template_var_values.keys()),
                prompt_variable_values=template_var_values,
                generated_text=llm_return_val.text,
                input_token_count=llm_return_val.input_token_count,
                generated_token_count=llm_return_val.generated_token_count,
                response_time=response_time,
            )
        )

        if asyncio.iscoroutine(callback):
            await callback

    except Exception as e:
        logger.error(
            f"Unexpected error in observability callback manager: {e}", exc_info=True
        )


def _run_completion_callback(
    callback_manager_fns: Any,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    llm_return_val: CompletionResponse,
    response_time: int,
) -> None:
    """
    Wrapper to run async callback in sync context via ThreadPoolExecutor.
    """
    asyncio.run(
        _process_completion_callback(
            callback_manager_fns, args, kwargs, llm_return_val, response_time
        )
    )


def llm_completion_callback() -> Callable:
    """
    Decorator to wrap observability method with llm.
    Looks for observability instances in `self.callback_manager`. For prompt-based LLMs (/completion).
    """

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def async_wrapper(self, *args, **kwargs):
            callback_manager_fns = getattr(self, "callback_manager", None)

            start_time = time.perf_counter()
            llm_return_val = f(self, *args, **kwargs)
            response_time = int((time.perf_counter() - start_time) * 1000)

            if callback_manager_fns:
                try:
                    # Try to use existing event loop (async)
                    loop = asyncio.get_running_loop()
                    loop.create_task(
                        _process_completion_callback(
                            callback_manager_fns,
                            args,
                            kwargs,
                            llm_return_val,
                            response_time,
                        )
                    )
                except RuntimeError:
                    # No event loop - use ThreadPoolExecutor (sync)
                    _callback_executor.submit(
                        _run_completion_callback,
                        callback_manager_fns,
                        args,
                        kwargs,
                        llm_return_val,
                        response_time,
                    )

            return llm_return_val

        return async_wrapper

    return decorator
