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
4. Do not invent facts that are not in the text.

Response format (array of objects, one per news item):
[
  {{
    "summary": "...",
    "entities": ["..."],
    "topics": ["..."],
    "id": "..."
  }}
]

News:
{news_data}."""


NEWS_GROUPING_PROMPT = """You are the editor of Croatia news digest.

You see a list of news items. For each item, the following information is provided:
- id
- brief description
- topics
- entities

Your task:
1. Group news items into meaningful groups. 
2. Treat topics related to the same event or trend as the same.
3. Give more priority to lifestyle news and upcoming events in Zagreb, positive topics, deprioritize political, corruption or criminal news.
4. Avoid creating groups that are too small.
5. Include only topics related to Croatia or croatian cities/people.
6. Return 5 to 10 main topics.

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


DIGEST_PREPARATION_PROMPT = """You are the editor-in-chief of a news digest.

You see clusters of news items grouped by topic. Your goal is to compile a digest of 5-6 key topics of the day.
Give more priority to lifestyle news, positive topics and upcoming events in Zagreb, deprioritize political, corruption or criminal news.
You are also given history of previously published articles, avoid publishing the same again. But you can publish updated information about the same topic if it's important.

Choose the key topics and create:

1. Short topic title (up to 10 words).
2. Summary - description of what happened (3-5 sentences).
3. Link to article which describes the topic mostly.
4. Why this topic is important (for internal evaluation).

All text must be written in Russian.
Return JSON:

[
  {{
  "title": "...",
  "description": "...",
  "link": "...",
  "importance_reason": "..."
  }}
]

News:

{cluster_news}

History:

{history}"""
