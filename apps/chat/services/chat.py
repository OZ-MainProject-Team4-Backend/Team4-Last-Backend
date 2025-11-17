from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, cast

from django.db import transaction
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from apps.chat.models import AiChatLogs, AiModelSettings
from apps.chat.services.model_picker import pick_model_setting
from apps.recommend.services.recommend_service import _build_outfit_by_temp_and_cond

logger = logging.getLogger(__name__)
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

    text = (user_message or "").lower()
    outfit_keywords = [
        "뭐입지",
        "뭐 입지",
        "입을까",
        "입어야",
        "코디",
        "옷 추천",
        "코디 추천",
        "패션 추천",
        "뭐 입어",
        "오늘 입을",
        "오늘 옷",
    ]
    is_outfit_question = any(kw in text for kw in outfit_keywords)

    fb: Dict[str, Any] | None = None
    if temp is not None:
        try:
            fb = _build_outfit_by_temp_and_cond(temp, cond)
        except Exception:
            logger.exception("outfit rule build failed")
            fb = None

    logger.info(
        "chat_and_log debug: temp=%s, cond=%s, is_outfit_question=%s, has_rule=%s",
        temp,
        cond,
        is_outfit_question,
        bool(fb),
    )

    if is_outfit_question and fb:
        logger.info(">>> OUTFIT RULE BRANCH HIT")

        rec1 = fb.get("rec_1") or ""
        rec2 = fb.get("rec_2") or ""
        rec3 = fb.get("rec_3") or ""
        explanation = fb.get("explanation") or ""

        answer_lines: List[str] = []
        answer_lines.append("[RULE] 온도 기반 하드코딩 코디 추천")
        if explanation:
            answer_lines.append(explanation)

        answer_lines.append("")
        answer_lines.append("오늘의 추천 코디:")
        if rec1:
            answer_lines.append(f"1) {rec1}")
        if rec2:
            answer_lines.append(f"2) {rec2}")
        if rec3:
            answer_lines.append(f"3) {rec3}")

        final_answer = "\n".join(answer_lines).strip()

        log: AiChatLogs = AiChatLogs.objects.create(
            user=user,
            model_setting=setting,
            session_id=session_id,
            model_name=model_name,
            user_question=user_message,
            ai_answer=final_answer,
            context={
                "weather": weather or {},
                "profile": profile or {},
                "model_setting": setting.name if setting else None,
                "rule_outfits": fb,
            },
        )

        return {
            "session_id": str(session_id),
            "answer": final_answer,
            "used_setting": setting.category_combo if setting else None,
            "log_id": log.id,
            "created_at": log.created_at,
            "rule_outfits": fb,
        }

    logger.info(">>> GPT BRANCH HIT")

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
    gpt_answer = (completion.choices[0].message.content or "").strip()

    context_to_save = {
        "weather": weather or {},
        "profile": profile or {},
        "model_setting": setting.name if setting else None,
    }
    log2: AiChatLogs = AiChatLogs.objects.create(
        user=user,
        model_setting=setting,
        session_id=session_id,
        model_name=model_name,
        user_question=user_message,
        ai_answer=gpt_answer,
        context=context_to_save,
    )

    return {
        "session_id": str(session_id),
        "answer": gpt_answer,
        "used_setting": setting.category_combo if setting else None,
        "log_id": log2.id,
        "created_at": log2.created_at,
    }
