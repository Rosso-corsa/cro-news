#!/usr/bin/env python3
"""
Prompts Module

This module contains prompt templates used for AI interactions.
"""

NEWS_ANALYSIS_PROMPT = """You are a news analyst.

Analyze the news and return the results in JSON format.

Requirements. For each news item:
1. Briefly describe the main event (no more than 2 sentences).
2. Identify 1 to 5 key entities:
- companies
- people
- countries
- organizations
3. Identify 1 to 5 key topics.
4. Estimate from 1 to 10 based on how this article is aligned with the following rules:
- The article is about Croatia or Zagreb;
- It's a positive news;
- News about upcoming or passed public events or festivals in Zagreb;
- Imporant news for expacts living in Zagreb;
- Not criminal/corruption/political news;
- Lifestyle-related article.
5. Do not invent facts that are not in the text.
6. Write in English.

Response format (array of objects, one per news item):
[
  {{
    "summary": "...",
    "entities": ["..."],
    "topics": ["..."],
    "relevance": N,
    "id": "..."
  }}
]

News:
{news_data}."""

NEWS_ANALYSIS_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "entities": {
                "type": "array",
                "items": {"type": "string"}
            },
            "topics": {
                "type": "array",
                "items": {"type": "string"}
            },
            "relevance": {"type": "integer"},
            "id": {"type": "string"}
        },
        "required": ["summary", "entities", "topics", "relevance", "id"]
    }
}

NEWS_GROUPING_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "clusters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "news_ids": {
                        "type": "array",
                        "items": {"type": "integer"}
                    }
                },
                "required": ["topic", "news_ids"]
            }
        }
    },
    "required": ["clusters"]
}

DIGEST_PREPARATION_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "link": {"type": "string"},
            "resolution": {"type": "integer"},
            "justification": {"type": "string"}
        },
        "required": ["title", "description", "link", "resolution", "justification"]
    }
}

CHANNEL_REVIEW_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "needs_improvement": {"type": "boolean"},
        "justification": {"type": "string"},
        "new_prompt": {"type": "string"}
    },
    "required": ["needs_improvement", "justification"]
}

BULK_DEDUPLICATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "status": {"type": "string", "enum": ["new", "match_unpublished", "match_history"]},
                    "matched_id": {"type": ["string", "null"]},
                    "confidence": {"type": "number"}
                },
                "required": ["id", "status", "matched_id", "confidence"]
            }
        }
    },
    "required": ["results"]
}

STREAM_PUBLISH_PREPARATION_PROMPT = """You are a news editor preparing a news item for publication.

You are given:
1. A topic summary of the news
2. Multiple versions of the original article text (from different sources or updates)

Your task is to prepare a concise, engaging message for publication that:
- Summarizes the key information from all text versions
- Is written in a lifestyle magazine style
- Is suitable for expats living in Croatia/Zagreb
- Headline standard: Titles must be catchy, engaging news headlines as in professional media. Do NOT use descriptive article summaries, topic lists, or compound titles (e.g., avoid "Предупреждение о непогоде и новой волне жары..." or combining multiple topics into one title).

You should return:
1. Catchy headline title (up to 10 words). Must look like a real lifestyle media headline, not a summary.
2. Summary - description of what happened (3-5 sentences). Don't use sophisticated vocabulary, keep it simple and clear, lifestyle magazine style.
3. Link to article which describes the topic mostly.
4. Resolution - publish or not publish (1 - publish, 0 - not publish).
5. Justification - if cluster resolution is "not publish", provide short explanation why.

All text must be written in Russian. Double check grammar, fix mistakes if found.
Return JSON:

{{
  "title": "...",
  "description": "..."
}}

Topic summary:

{topic_summary}

Original text versions:

{original_texts}"""

STREAM_PUBLISH_PREPARATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"}
    },
    "required": ["title", "description"]
}


NEWS_GROUPING_PROMPT = """You are the editor of Croatia news digest.

You see a list of news items. For each item, the following information is provided:
- id
- brief description
- topics
- entities

Your task:
1. Aggregate articles into groups related to the same event or news.
2. Return from 3 to 15 main topics. Select topics based on criteria:
- This is Croatia or Zagreb specific news/event
- It affects expats living in Croatia, Zagreb
- It's not a political, corruption or criminal related news

Return strictly JSON:

{{
"clusters": [
{{
"topic": "...",
"news_ids": [1, 5, 8, 10]
}}
]
}}

News:

{news_metadata}"""


DIGEST_PREPARATION_PROMPT = """You are the editor-in-chief of a news lifestyle digest for expats.

You see clusters of news items grouped by topic. Your goal is to compile a digest of the day. Recommendations:
* It's a lifestyle media, so prioritize such topics (events, culture, local food, urban changes, leisure). Deprioritize political or criminal news unless critical;
* The digest should be specifically about Croatia and/or Zagreb;
* The news should be relevant for expats. Filter out irrelevant or weak topics (e.g., online delivery from global online stores like Marks & Spencer, routine corporate announcements);
* Headline standard: Titles must be catchy, engaging news headlines as in professional media. Do NOT use descriptive article summaries, topic lists, or compound titles (e.g., avoid "Предупреждение о непогоде и новой волне жары..." or combining multiple topics into one title).

You are also given history of previously published articles, avoid publishing the same again. But you can publish updated information about the same topic if it's important.

For each provided cluster create:
1. Catchy headline title (up to 10 words). Must look like a real lifestyle media headline, not a summary.
2. Summary - description of what happened (3-5 sentences). Don't use sophisticated vocabulary, keep it simple and clear, lifestyle magazine style.
3. Link to article which describes the topic mostly.
4. Resolution - publish or not publish (1 - publish, 0 - not publish).
5. Justification - if cluster resolution is "not publish", provide short explanation why.

All text must be written in Russian. Double check grammar, fix mistakes if found.
Return JSON:

[
  {{
  "title": "...",
  "description": "...",
  "link": "...",
  "resolution": 0/1
  "justification": "..."
  }}
]

News:

{cluster_news}

History:

{history}"""


CHANNEL_REVIEW_PROMPT = """You are a media editor reviewing a news digest channel.

You are given:
1. The current digest preparation prompt that generates the messages
2. Recent messages published to the channel

Your task is to analyze the published messages and evaluate if they meet quality standards.

Quality criteria:
- **Format**: Titles should be catchy news headlines, not article summaries. They should look like real media headlines.
- **Content**: Messages should fit the channel purpose: lifestyle media about Croatia/Zagreb, relevant for expats, avoiding political/criminal news unless critical.

Examples of bad titles (article summaries instead of headlines):
- "Предупреждение о непогоде и новой волне жары в Хорватии"
- "Новые правила медосмотра для иностранцев и изменения в HZZО"

Examples of bad content (doesn't fit channel purpose):
- "Marks & Spencer доставляет товары в Хорватию онлайн" (not lifestyle/expat relevant)

Analyze the messages and determine if the current prompt needs improvement.

If the messages are good quality and meet the criteria, return:
{{
  "needs_improvement": false,
  "justification": "Messages meet quality standards. No changes needed."
}}

If the messages have issues, return:
{{
  "needs_improvement": true,
  "new_prompt": "The complete improved DIGEST_PREPARATION_PROMPT. CRITICAL: You must preserve the EXACT structure and formatting of the original prompt template. Keep all line breaks, sections, and MOST IMPORTANTLY keep the {{cluster_news}} and {{history}} placeholders exactly as they appear. Only modify the instructions and examples, not the template structure.",
  "justification": "Detailed explanation of what problems were found and why the suggested changes will fix them"
}}

Current digest preparation prompt:

{current_prompt}

Recent published messages:

{messages}"""


BULK_DEDUPLICATION_PROMPT = """You are a professional news editor.

You are given:
1. New articles that need to be processed
2. Unpublished news items (candidates for future publishing)
3. History of already published articles

Your task is to determine for each new article whether it is:
- NEW: Not seen before, should be added to unpublished
- MATCH_UNPUBLISHED: Similar to an existing unpublished item (provide the item ID)
- MATCH_HISTORY: Similar to an already published article (provide the history entry details)

Criteria for matching:
- Same core event/topic (semantically similar content)
- Same or very similar entities involved
- Same location and timeframe
- Minor updates to the same story count as matches

When multiple new articles cover the same topic:
- Mark the first one as NEW (to create the unpublished entry)
- Mark all subsequent ones as MATCH_UNPUBLISHED
- All subsequent ones should reference the same matched_id (the ID that would be created for the first one)
- This groups similar articles together under a single unpublished entry

For each new article, return:
- id: The ID of the new article
- status: "new", "match_unpublished", or "match_history"
- matched_id: The ID of the matching item (if status is not "new")
- confidence: Your confidence in this match (0.0 to 1.0)

Return JSON:

{{
  "results": [
    {{
      "id": "...",
      "status": "new",
      "matched_id": null,
      "confidence": 1.0
    }},
    {{
      "id": "...",
      "status": "match_unpublished",
      "matched_id": "news_123_456",
      "confidence": 0.95
    }},
    {{
      "id": "...",
      "status": "match_history",
      "matched_id": "history_entry_123",
      "confidence": 0.9
    }}
  ]
}}

New articles:

{new_articles}

Unpublished news:

{unpublished_news}

History:

{history}"""
