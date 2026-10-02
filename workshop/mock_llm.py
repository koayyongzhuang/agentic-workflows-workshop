"""A deterministic, offline stand-in for a real LLM.

Why it exists
-------------
* The workshop keeps working when wifi or API keys fail.
* Tests run in CI without network access.

How it "thinks" (deliberately simple, so you can read it):
* Tool selection: score every bound tool by keyword overlap between the user's
  request and the tool's name + description; call the best one.
* Tool arguments: pulled from the request with small regexes (numbers, IDs,
  enum values).
* After tool results arrive, it writes a short answer quoting them.
* Structured output: if the schema defines `mock_response(text)` that is used,
  otherwise fields are filled generically.

A real model does all of this far better. Switch with MODEL=... in `.env`.
"""

from __future__ import annotations

import json
import re
import typing
from typing import Any, Literal, get_args, get_origin

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel

STOPWORDS = {
    "the", "and", "for", "you", "your", "are", "can", "with", "this", "that", "what", "how", "please",
    "have", "has", "our", "from", "about", "into", "when", "will", "would", "could", "should", "any",
    "use", "using", "tool", "tools", "given", "returns", "return", "get", "all", "not", "but", "its",
    "their", "they", "them", "who", "was", "were", "also", "there", "here", "does", "did", "one",
}
GENERIC_PARAM_TOKENS = {"id", "name", "number", "value", "per", "the"}


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z][a-z0-9]+", text.lower().replace("_", " "))
    out = set()
    for w in words:
        if len(w) < 3 or w in STOPWORDS:
            continue
        out.add(w)
        # naive stemming so "booking"/"book", "eligible"/"eligibility" meet
        for suffix in ("ility", "ings", "ing", "ies", "es", "s", "ed", "le"):
            if w.endswith(suffix) and len(w) - len(suffix) >= 4:
                out.add(w[: -len(suffix)])
                break
    return out


def _last_human(messages: list[BaseMessage]) -> str:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return m.content if isinstance(m.content, str) else str(m.content)
    return ""


def _text_of(inp: Any) -> str:
    if isinstance(inp, str):
        return inp
    if isinstance(inp, BaseMessage):
        return str(inp.content)
    if isinstance(inp, dict) and "messages" in inp:
        inp = inp["messages"]
    if isinstance(inp, list):
        return "\n".join(_text_of(m) for m in inp)
    if hasattr(inp, "to_messages"):
        return _text_of(inp.to_messages())
    return str(inp)


# --------------------------------------------------------------------------- args
_NUM = r"(\d[\d,]*(?:\.\d+)?)"


def _to_number(raw: str, typ: str) -> float | int:
    val = float(raw.replace(",", ""))
    return int(val) if typ == "integer" else val


def extract_args(params: dict, text: str) -> dict:
    props: dict = params.get("properties", {})
    required = set(params.get("required", []))
    numbers = [m for m in re.finditer(_NUM, text)]
    used_spans: set[tuple[int, int]] = set()
    args: dict[str, Any] = {}
    lower = text.lower()

    for name, spec in props.items():
        typ = spec.get("type") or (spec.get("anyOf") or [{}])[0].get("type")
        enum = spec.get("enum") or next((a.get("enum") for a in spec.get("anyOf", []) if a.get("enum")), None)
        name_toks = [t for t in name.lower().split("_") if t not in GENERIC_PARAM_TOKENS]

        if enum:
            hit = next((e for e in enum if str(e).lower() in lower), None)
            if hit is not None:
                args[name] = hit
            elif name in required:
                args[name] = enum[0]
        elif typ in ("integer", "number"):
            found = None
            if {"size", "count", "people", "members"} & set(name_toks):
                found = re.search(rf"{_NUM}\s*(?:people|persons|members|pax|of us)\b", lower) or re.search(
                    rf"(?:household|family) of {_NUM}", lower
                )
                name_toks = []  # never fall back to generic matching for counts
            for tok in reversed(name_toks):  # most specific word last, e.g. monthly_household_INCOME
                for pat in (rf"{tok}\w*\D{{0,25}}?{_NUM}", rf"{_NUM}\s*{tok}"):
                    m = re.search(pat, lower)
                    if m:
                        found = m
                        break
                if found:
                    break
            if found is None and "age" in name_toks:
                found = re.search(rf"{_NUM}\s*(?:years?|yrs?|yo)\b", lower) or re.search(rf"\bi'?m\s+{_NUM}\b", lower)
            if found is None and name in required:
                found = next((m for m in numbers if (m.start(), m.end()) not in used_spans), None)
            if found is not None:
                raw = found.group(1)
                span = next(((m.start(), m.end()) for m in numbers if m.group(1) == raw), None)
                if span:
                    used_spans.add(span)
                try:
                    args[name] = _to_number(raw, typ)
                except ValueError:
                    pass
        elif typ == "boolean":
            if any(t in lower for t in name_toks):
                args[name] = True
        else:  # string
            if name.endswith("id") or name.endswith("_ref"):
                m = re.search(r"\b[A-Z]{2,5}-\d{3,6}\b", text)
                if m:
                    args[name] = m.group(0)
                elif name in required:
                    args[name] = text
            elif "date" in name or name == "slot":
                m = re.search(r"\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?", text)
                if m:
                    args[name] = m.group(0)
                elif name in required:
                    args[name] = text
            elif name in {"query", "question", "topic", "text", "request", "task", "fact"}:
                args[name] = text
            elif name in required:
                args[name] = _named_entity(text) or text
    return args


def _named_entity(text: str) -> str | None:
    """Longest Title Case phrase not starting a sentence ("Senior Mobility Grant", "Tokyo"), else an acronym."""
    best: str | None = None
    for m in re.finditer(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4}\b", text):
        before = text[: m.start()].rstrip()
        if not before or before[-1] in ".?!:\n(":
            continue  # sentence-initial words are usually just capitalised
        if best is None or len(m.group(0).split()) > len(best.split()):
            best = m.group(0)
    if best:
        return best
    acronyms = [a for a in re.findall(r"\b[A-Z]{2,5}\b", text) if a not in {"NRIC", "API", "OK"}]
    return acronyms[0] if acronyms else None


# --------------------------------------------------------------------------- structured output
def fill_schema(schema: Any, text: str) -> Any:
    if hasattr(schema, "mock_response"):
        return schema.mock_response(text)
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        values = {}
        t = tokens(text)
        for fname, field in schema.model_fields.items():
            values[fname] = _fill_type(field.annotation, t, text, field.description or "")
        return schema(**values)
    raise TypeError(f"MockChatModel cannot fill schema {schema!r}")


def _fill_type(ann: Any, t: set[str], text: str, desc: str) -> Any:
    origin = get_origin(ann)
    if origin is Literal:
        opts = get_args(ann)
        return max(opts, key=lambda o: len(tokens(str(o)) & t))
    if origin in (list, typing.List):
        return [text[:200]]
    if origin is typing.Union:
        inner = [a for a in get_args(ann) if a is not type(None)]
        return _fill_type(inner[0], t, text, desc) if inner else None
    if ann is bool:
        return True
    if ann in (int, float):
        return ann(1)
    return f"(mock) {text[:160]}"


# --------------------------------------------------------------------------- the model
class MockChatModel(BaseChatModel):
    role: str = "assistant"
    tools_schema: list[dict] = []

    @property
    def _llm_type(self) -> str:
        return "workshop-mock"

    def bind_tools(self, tools, **kwargs):  # type: ignore[override]
        return self.model_copy(update={"tools_schema": [convert_to_openai_tool(t) for t in tools]})

    def with_structured_output(self, schema, **kwargs):  # type: ignore[override]
        return RunnableLambda(lambda inp: fill_schema(schema, _text_of(inp)))

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._respond(messages))])

    # ---- behaviour -------------------------------------------------------
    def _respond(self, messages: list[BaseMessage]) -> AIMessage:
        request = _last_human(messages)

        # 1) Tool results just came back -> answer using them ("result processing").
        trailing: list[ToolMessage] = []
        for m in reversed(messages):
            if isinstance(m, ToolMessage):
                trailing.append(m)
            else:
                break
        if trailing:
            return AIMessage(content=self._summarise(list(reversed(trailing))))

        # 2) Decide whether a tool helps ("tool selection").
        if self.tools_schema:
            last_h = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=-1)
            already = {
                tc["name"]
                for m in messages[last_h + 1:]
                if isinstance(m, AIMessage)
                for tc in (m.tool_calls or [])
            }
            call = self._select_tool(request, exclude=already)
            if call:
                return AIMessage(content="", tool_calls=[call])

        # 3) Plain text reply.
        system = next((m.content for m in messages if isinstance(m, SystemMessage)), "")
        persona = str(system).strip().splitlines()[0][:90] if system else f"{self.role}"
        context = messages[-1].content if messages and not isinstance(messages[-1], HumanMessage) else ""
        body = str(context or request).strip()
        return AIMessage(content=f"[mock {self.role}] ({persona}) {body[:2500]}")

    def _select_tool(self, request: str, exclude: set[str]) -> dict | None:
        req = tokens(request)
        best, best_score = None, 0
        for spec in self.tools_schema:
            fn = spec["function"]
            if fn["name"] in exclude:
                continue
            name_toks = tokens(fn["name"])
            score = 2 * len(name_toks & req) + len(tokens(fn.get("description", "")) & req)
            if score > best_score:
                best, best_score = fn, score
        if not best or best_score < 2:
            return None
        args = extract_args(best.get("parameters", {}), request)
        return {"name": best["name"], "args": args, "id": f"call_{best['name']}_{abs(hash(request)) % 10_000}", "type": "tool_call"}

    @staticmethod
    def _summarise(results: list[ToolMessage]) -> str:
        lines = ["Here is what I found:"]
        for r in results:
            content = r.content if isinstance(r.content, str) else json.dumps(r.content)
            lines.append(f"- {r.name}: {content[:700]}")
        return "\n".join(lines)
