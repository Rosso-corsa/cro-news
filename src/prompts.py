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
- Not criminal/corruption/political/beatuty/fashion news;
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
- matched_id: The ID of the matching item (if status is not "new", otherwise - return null)
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
                    "matched_id": {"type": "string", "nullable": True},
                    "confidence": {"type": "number"}
                },
                "required": ["id", "status", "matched_id", "confidence"]
            }
        }
    },
    "required": ["results"]
}
