"""Non-blocking decide-policy-act pipeline for live chat messages."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from typing import Any

from decision_pattern.lurker_gate import OPTIONS, QUESTION, apply_policy

from .bedrock_replier import BedrockReplyError
from .config import AppConfig
from .context import ChatContext, build_state
from .metrics import MetricsStore
from .reactor import Reactor
from .schemas import ChatMessage, DecisionEvent, utc_now

Broadcast = Callable[[dict[str, Any]], Awaitable[None]]


async def _no_broadcast(payload: dict[str, Any]) -> None:
    del payload


class MessagePipeline:
    """Process messages in the background while broadcasting observable events."""

    def __init__(
        self,
        *,
        config: AppConfig,
        adapter: Any,
        replier: Any,
        context: ChatContext,
        metrics: MetricsStore,
        reactor: Reactor | None = None,
        broadcast: Broadcast = _no_broadcast,
    ) -> None:
        self.config = config
        self.adapter = adapter
        self.replier = replier
        self.context = context
        self.metrics = metrics
        self.reactor = reactor or Reactor()
        self.broadcast = broadcast
        self._tasks: set[asyncio.Task[DecisionEvent]] = set()

    async def process_message(self, message: ChatMessage) -> asyncio.Task[DecisionEvent]:
        """Append and broadcast immediately, then schedule decision work."""
        history = await self.context.append(message)
        await self.broadcast(
            {
                "type": "chat",
                "id": message.id,
                "sender": message.sender,
                "text": message.text,
                "is_agent": message.is_agent,
                "ts": message.ts.isoformat(),
            }
        )
        task = asyncio.create_task(self._decide_and_act(message, history))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def _decide_and_act(
        self, message: ChatMessage, history: list[dict[str, Any]]
    ) -> DecisionEvent:
        state = build_state(
            history,
            {"sender": message.sender, "text": message.text},
            self.config.context_k,
        )
        result = await asyncio.to_thread(
            self.adapter.decide, state, QUESTION, OPTIONS
        )
        final_action, downgraded, reason = apply_policy(
            result, self.config.policy_config()
        )
        direct_mention = bool(re.search(r"\blurker\b", message.text, re.IGNORECASE))
        if (
            direct_mention
            and self.config.force_reply_on_mention
            and result.error is None
        ):
            final_action, downgraded, reason = "REPLY", False, "direct_mention"

        bedrock_latency_ms: float | None = None
        input_tokens: int | None = None
        output_tokens: int | None = None
        bedrock_called = False
        error = result.error

        if final_action == "REACT":
            await self.broadcast(
                {
                    "type": "reaction",
                    "message_id": message.id,
                    "emoji": self.reactor.choose(message.text),
                    "ts": utc_now().isoformat(),
                }
            )
        elif final_action == "REPLY":
            try:
                reply_text, bedrock_latency_ms, input_tokens, output_tokens = (
                    await asyncio.to_thread(self.replier.reply, state)
                )
                bedrock_called = not bool(getattr(self.replier, "mock", False))
            except BedrockReplyError as exc:
                bedrock_latency_ms = exc.latency_ms
                bedrock_called = exc.invoked
                error = f"bedrock_error: {exc}"
                reason = "bedrock_error"
            except Exception as exc:  # injected repliers must also fail safely
                bedrock_called = not bool(getattr(self.replier, "mock", False))
                error = f"bedrock_error: {type(exc).__name__}: {exc}"
                reason = "bedrock_error"
            else:
                agent_message = ChatMessage(
                    sender="Lurker", text=reply_text, is_agent=True
                )
                await self.context.append(agent_message)
                await self.broadcast(
                    {
                        "type": "chat",
                        "id": agent_message.id,
                        "sender": agent_message.sender,
                        "text": agent_message.text,
                        "is_agent": True,
                        "ts": agent_message.ts.isoformat(),
                    }
                )

        event = DecisionEvent(
            message_id=message.id,
            sender=message.sender,
            text=message.text,
            context_k=self.config.context_k,
            raw_choice=result.choice,
            confidence=result.confidence,
            final_action=final_action,
            downgraded=downgraded,
            reason=reason,
            decider_latency_ms=result.latency_ms,
            bedrock_latency_ms=bedrock_latency_ms,
            bedrock_input_tokens=input_tokens,
            bedrock_output_tokens=output_tokens,
            bedrock_called=bedrock_called,
            direct_mention=direct_mention,
            mock=bool(getattr(self.adapter, "mock", False)),
            error=error,
        )
        self.metrics.record(event)
        await self.broadcast(
            {
                "type": "decision",
                "message_id": message.id,
                "raw_choice": event.raw_choice,
                "confidence": event.confidence,
                "final_action": event.final_action,
                "downgraded": event.downgraded,
                "reason": event.reason,
                "decider_latency_ms": event.decider_latency_ms,
                "mock": event.mock,
                "ts": event.ts.isoformat(),
            }
        )
        await self.broadcast(
            {
                "type": "metrics",
                "counters": self.metrics.counters(),
                "ts": event.ts.isoformat(),
            }
        )
        return event

    async def reset(self) -> None:
        """Cancel pending work and reset live context and metrics."""
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        await self.context.reset()
        self.metrics.reset()

    async def close(self) -> None:
        """Wait for currently scheduled message work to finish."""
        tasks = list(self._tasks)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
