import json
import re
import time
import uuid
import logging
from groq import Groq
import google.generativeai as genai
from app.config import settings

logger = logging.getLogger("model_gateway")

# Rough per-1K-token USD pricing, used only for an *estimated* cost figure.
# These are ballpark public rates; adjust as provider pricing changes.
# (Groq's free tier is $0 in practice — these reflect Groq's published
#  pay-as-you-go rates so the cost-tracking math stays meaningful.)
PRICING_PER_1K = {
    "llama-3.1-8b-instant":   {"prompt": 0.00005,  "completion": 0.00008},
    "llama-3.3-70b-versatile":{"prompt": 0.00059,  "completion": 0.00079},
    "gemini-2.5-flash":       {"prompt": 0.000075, "completion": 0.0003},
}


class ModelGateway:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel("gemini-2.5-flash")

        # models in priority order (primary first, then fallbacks).
        # Current Groq free-tier model IDs (Jan 2026); the old
        # llama3-8b-8192 / mixtral-8x7b-32768 were deprecated by Groq.
        self.models = [
            {"provider": "groq",   "model": "llama-3.1-8b-instant",    "label": "Groq Llama 3.1 8B Primary"},
            {"provider": "groq",   "model": "llama-3.3-70b-versatile", "label": "Groq Llama 3.3 70B Fallback"},
            {"provider": "gemini", "model": "gemini-2.5-flash",        "label": "Gemini Flash Last Resort"},
        ]

    # cost helpers
    def _estimate_cost(self, model, prompt_tokens, completion_tokens):
        rates = PRICING_PER_1K.get(model)
        if not rates or prompt_tokens is None or completion_tokens is None:
            return 0.0
        return round(
            (prompt_tokens / 1000) * rates["prompt"]
            + (completion_tokens / 1000) * rates["completion"],
            6,
        )

    def _extract_usage(self, provider, response, prompt, raw):
        """Return (prompt_tokens, completion_tokens, total_tokens, estimated_flag)."""
        try:
            if provider == "groq" and getattr(response, "usage", None):
                u = response.usage
                return u.prompt_tokens, u.completion_tokens, u.total_tokens, False
            if provider == "gemini" and getattr(response, "usage_metadata", None):
                u = response.usage_metadata
                return (u.prompt_token_count, u.candidates_token_count,
                        u.total_token_count, False)
        except Exception:
            pass
        # fallback: rough estimate by characters / 4
        pt = max(1, len(prompt) // 4)
        ct = max(1, len(raw) // 4) if raw else 0
        return pt, ct, pt + ct, True

    # main entrypoint
    async def complete(self, prompt, temperature=0.7, max_tokens=1500,
                       db=None, feature=None, trip_id=None, prompt_version=None,
                       result_holder=None, start_at=0):
        """Try each model in priority order. Records one AICall row per attempt
        when a db session is provided. Logging never breaks the AI call itself.

        If result_holder (a dict) is passed, the successful call's id is stored
        under result_holder['call_id'] so the caller can attach an eval score.

        start_at lets a caller begin the chain at a later model (still a REAL
        call on that model). Used to deliberately exercise fallback models, e.g.
        for coverage/resilience testing — not to fake data.
        """
        last_error = None

        for position, model_config in enumerate(self.models):
            if position < start_at:
                continue
            provider = model_config["provider"]
            model = model_config["model"]
            label = model_config["label"]
            started = time.perf_counter()

            try:
                logger.info("Trying %s", label)

                if provider == "groq":
                    response = self.groq_client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    raw = response.choices[0].message.content
                elif provider == "gemini":
                    response = self.gemini_model.generate_content(prompt)
                    raw = response.text
                else:
                    raise ValueError(f"Unknown provider: {provider}")

                latency_ms = int((time.perf_counter() - started) * 1000)
                pt, ct, tt, estimated = self._extract_usage(provider, response, prompt, raw)
                cost = self._estimate_cost(model, pt, ct)

                call_id = await self._record(
                    db, provider=provider, model=model, label=label, feature=feature,
                    trip_id=trip_id, prompt_version=prompt_version, success=True,
                    fallback_position=position, latency_ms=latency_ms, error=None,
                    prompt_tokens=pt, completion_tokens=ct, total_tokens=tt,
                    tokens_estimated=estimated, estimated_cost_usd=cost,
                )
                if result_holder is not None:
                    result_holder["call_id"] = call_id
                logger.info("Success with %s (%dms, %s tokens)", label, latency_ms, tt)
                return raw

            except Exception as e:
                latency_ms = int((time.perf_counter() - started) * 1000)
                logger.warning("%s failed: %s", label, str(e))
                await self._record(
                    db, provider=provider, model=model, label=label, feature=feature,
                    trip_id=trip_id, prompt_version=prompt_version, success=False,
                    fallback_position=position, latency_ms=latency_ms,
                    error=str(e)[:500], prompt_tokens=None, completion_tokens=None,
                    total_tokens=None, tokens_estimated=False, estimated_cost_usd=None,
                )
                last_error = e
                continue

        raise Exception(f"All models failed. Last error: {str(last_error)}")

    async def _record(self, db, **fields):
        """Write one AICall row. Returns the new row id (or None). Swallows its
        own errors so logging can never break a successful AI response."""
        if db is None:
            return None
        try:
            from app.models.ai_call import AICall
            call_id = str(uuid.uuid4())
            db.add(AICall(id=call_id, **fields))
            await db.flush()
            return call_id
        except Exception as e:
            logger.warning("Failed to record AI call metrics: %s", e)
            return None

    def parse_json(self, raw):
        """Safely parse JSON from a model response.

        LLMs don't always return clean JSON — they may wrap it in ``` fences,
        add prose before/after, or use trailing commas. This tolerates all of
        those rather than 500-ing on a strict json.loads.
        """
        if raw is None:
            raise ValueError("Empty response from model")
        clean = raw.strip()

        # 1) strip code fences
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            parts = clean.split("```")
            if len(parts) >= 3:
                clean = parts[1].strip()

        # 2) first attempt — straight parse
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            pass

        # 3) extract the outermost JSON object/array if there's surrounding prose
        start = min(
            [i for i in (clean.find("{"), clean.find("[")) if i != -1],
            default=-1,
        )
        end = max(clean.rfind("}"), clean.rfind("]"))
        if start != -1 and end != -1 and end > start:
            candidate = clean[start:end + 1]
            # 4) remove trailing commas before } or ]
            candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        # 5) give callers a clear, catchable signal instead of a raw decode crash
        raise ValueError("Model did not return valid JSON")


# single instance used across the entire app
gateway = ModelGateway()