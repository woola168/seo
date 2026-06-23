from younilab_geo_tracking_domain import MarketType, RegionCode


def default_language(region: RegionCode) -> str:
    if region == RegionCode.UNITED_STATES:
        return "en-US"
    return "zh-TW"


def system_prompt(market_type: MarketType, region: RegionCode, language: str) -> str:
    if language == "zh-TW":
        return _zh_tw_system_prompt(market_type, region)
    return _en_us_system_prompt(market_type, region, language)


def _zh_tw_system_prompt(market_type: MarketType, region: RegionCode) -> str:
    market_context = {
        MarketType.B2C: (
            "你正在評估面向消費者的 AI 搜尋回答。請聚焦品牌提及、實際產品需求、"
            "購買疑慮與可引用來源。"
        ),
        MarketType.B2B_PROCUREMENT: (
            "你正在評估 B2B 採購導向的 AI 搜尋回答。請聚焦供應商評估、比較條件、"
            "外銷準備度、標準規範、OEM/ODM 適配性與採購風險。"
        ),
    }[market_type]
    region_context = {
        RegionCode.TAIWAN: "請使用台灣市場語氣與台灣繁體中文用語。",
        RegionCode.UNITED_STATES: "請保留美國買方脈絡，但用台灣繁體中文回答。",
    }[region]
    return (
        f"{market_context} {region_context} "
        "每次回答前都必須使用 Google Search tool 作為 reference；"
        "回答中需以目前可查證的網頁來源為依據，避免只靠既有知識。"
        "即使 query 模糊、資訊不足、可能有多種解讀或看起來需要進一步釐清，"
        "也不得只要求使用者補充資料；你仍然必須先執行 Google Search，"
        "用目前可找到的網頁判斷最可能的語意、品牌、產品、地點或供應商脈絡，"
        "再在回答中說明採用的假設與仍需要釐清的事項。"
        "不要在沒有搜尋與 references 的情況下只用模型既有知識回答。"
    )


def _en_us_system_prompt(
    market_type: MarketType,
    region: RegionCode,
    language: str,
) -> str:
    market_context = {
        MarketType.B2C: (
            "You are evaluating consumer-facing AI search answers. Focus on "
            "brand mention, practical product needs, buyer concerns, and cited sources."
        ),
        MarketType.B2B_PROCUREMENT: (
            "You are evaluating B2B procurement-oriented AI search answers. Focus on "
            "supplier evaluation, comparison criteria, export readiness, standards, "
            "OEM/ODM fit, and buyer risk."
        ),
    }[market_type]
    region_context = {
        RegionCode.TAIWAN: "Use Taiwan market context while answering in English.",
        RegionCode.UNITED_STATES: (
            "Use United States buyer language and B2B sourcing terminology."
        ),
    }[region]
    return (
        f"{market_context} {region_context} Answer in {language}. "
        "Before every answer, you must use the Google Search tool as a reference. "
        "Ground claims in currently discoverable web sources instead of relying only "
        "on prior knowledge. If the query is ambiguous, underspecified, has multiple "
        "possible meanings, or appears to need clarification, do not only ask the "
        "user for more context. You must still perform Google Search first, identify "
        "the most likely brand, product, location, supplier, or market meaning from "
        "currently discoverable web pages, then state your working assumptions and "
        "what still needs clarification. Do not answer without search-backed "
        "references."
    )


def branded_templates(market_type: MarketType, region: RegionCode) -> list[str]:
    if market_type == MarketType.B2B_PROCUREMENT:
        if region == RegionCode.TAIWAN:
            return [
                "{brand} 和 {competitor} 在 {keyword} 供應能力上怎麼比較？",
                "{brand} 是可靠的 {keyword} 供應商嗎？",
                "採購團隊選擇 {brand} 的 {keyword} 前應該評估哪些風險？",
            ]
        return [
            "How does {brand} compare with {competitor} for {keyword} sourcing?",
            "Is {brand} a reliable {keyword} supplier for US buyers?",
            "What should procurement teams know before choosing {brand} for {keyword}?",
        ]
    if region == RegionCode.UNITED_STATES:
        return [
            "What is {brand} known for in {keyword}?",
            "How does {brand} compare with {competitor} for {keyword}?",
        ]
    return [
        "{brand} 在 {keyword} 有哪些推薦產品？",
        "{brand} 和 {competitor} 在 {keyword} 上有什麼差異？",
        "{brand} 適合哪些 {keyword} 需求？",
    ]


def non_branded_templates(market_type: MarketType, region: RegionCode) -> list[str]:
    if market_type == MarketType.B2B_PROCUREMENT:
        if region == RegionCode.TAIWAN:
            return [
                "台灣 {keyword} 供應商有哪些可靠選擇？",
                "採購團隊選擇 {keyword} 供應商時應該評估哪些條件？",
                "{keyword} 的替代供應商或製造商有哪些？",
            ]
        return [
            "Reliable {keyword} suppliers for US industrial buyers",
            "What should procurement teams evaluate when choosing {keyword} suppliers?",
            "Best {keyword} manufacturer alternatives for export sourcing",
        ]
    if region == RegionCode.UNITED_STATES:
        return [
            "What are the best {keyword} options?",
            "Which brands are recommended for {keyword}?",
        ]
    return [
        "{keyword} 有哪些推薦品牌？",
        "{keyword} 適合哪些族群或使用情境？",
        "有 {keyword} 需求時應該怎麼選？",
    ]
