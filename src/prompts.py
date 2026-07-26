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
