from __future__ import annotations

from typing import Any, Dict, List, Optional, cast

from django.db import transaction
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from apps.chat.models import AiChatLogs, AiModelSettings
from apps.chat.services.model_picker import pick_model_setting
from apps.recommend.services.recommend_service import generate_outfit_recommend

client = OpenAI()


def _msg(role: str, content: str) -> ChatCompletionMessageParam:
    return cast(ChatCompletionMessageParam, {"role": role, "content": content})


@transaction.atomic
def chat_and_log(
    *,
    user,
    session_id,
    user_message: str,
    weather: Dict[str, Any] | None,
    profile: Dict[str, Any] | None,
    model_name: str = "gpt-4o",
) -> dict:
    temp: Optional[float] = (
        (weather.get("feels_like") or weather.get("temperature")) if weather else None
    )
    humi: Optional[int] = weather.get("humidity") if weather else None
    cond: Optional[str] = weather.get("condition") if weather else None

    setting: Optional[AiModelSettings] = None
    if temp is not None:
        setting = pick_model_setting(temp, humi, cond)

    recent = list(
        AiChatLogs.objects.filter(user=user, session_id=session_id)
        .order_by("-created_at")
        .values_list("user_question", "ai_answer")[:3]
    )
    history: List[ChatCompletionMessageParam] = []
    for q, a in reversed(recent):
        history.append(_msg("user", q))
        history.append(_msg("assistant", a))

    system_prompt = (
        "너는 한국어로 대답하는 AI 모델이야. "
        "사용자가 날씨와 코디를 물으면 현재 날씨 정보를 활용해 코디를 추천하고, "
        "그 외 질문에는 일상 대화처럼 간결하고 유용하게 답해줘."
    )

    guidance_parts: List[str] = []
    if weather:
        guidance_parts.append(
            f"현재 날씨: {weather.get('temperature')}°C"
            f", 체감 {weather.get('feels_like')}"
            f", 습도 {weather.get('humidity')}%"
            f", 상태 {weather.get('condition')}"
        )
    if setting:
        guidance_parts.append(f"DB 룰 후보: {setting.category_combo}")
    if profile:
        guidance_parts.append(f"사용자 프로필: {profile}")

    if not setting:
        fb = None
        lat = (weather or {}).get("lat")
        lon = (weather or {}).get("lon")
        try:
            if lat is not None and lon is not None:
                fb = generate_outfit_recommend(user, float(lat), float(lon))
        except Exception:
            fb = None

        if fb:
            candidates = [
                fb.get("rec_1") or "",
                fb.get("rec_2") or "",
                fb.get("rec_3") or "",
            ]
            candidates = [c for c in candidates if c]
            if candidates:
                guidance_parts.append("룰 폴백 후보:\n- " + "\n- ".join(candidates))

    fewshot: List[ChatCompletionMessageParam] = [
        _msg(
            "system",
            "예시Q: 저녁 뭐 먹지? 예시A: 오늘은 가벼운 한식으로 비빔밥 어때요? 야채 듬뿍에 고추장 조금.",
        ),
        _msg(
            "system",
            "예시Q: 요약해줘 예시A: 핵심만 3줄로 요약할게요: 1) ..., 2) ..., 3) ...",
        ),
    ]

    messages: List[ChatCompletionMessageParam] = [
        _msg("system", system_prompt),
        *fewshot,
    ]
    if guidance_parts:
        messages.append(_msg("system", "\n".join(guidance_parts)))
    messages.extend(history)
    messages.append(_msg("user", user_message))

    completion = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.8,
    )
    answer = (completion.choices[0].message.content or "").strip()

    context_to_save = {
        "weather": weather or {},
        "profile": profile or {},
        "model_setting": setting.name if setting else None,
    }
    log: AiChatLogs = AiChatLogs.objects.create(
        user=user,
        model_setting=setting,
        session_id=session_id,
        model_name=model_name,
        user_question=user_message,
        ai_answer=answer,
        context=context_to_save,
    )

    log_id: int = cast(int, getattr(log, "id", log.pk))

    return {
        "session_id": str(session_id),
        "answer": answer,
        "used_setting": setting.category_combo if setting else None,
        "log_id": log_id,
    }
