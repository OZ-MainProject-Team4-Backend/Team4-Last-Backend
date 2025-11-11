def detect_intent(text: str) -> str:
    t = (text or "").lower()
    keywords = [
        "날씨",
        "기온",
        "우산",
        "코디",
        "옷",
        "패션",
        "뭐 입",
        "outer",
        "상의",
        "하의",
    ]
    if any(k in t for k in keywords):
        return "outfit"
    return "general"
