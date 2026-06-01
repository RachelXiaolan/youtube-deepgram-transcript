# YouTube Video Summary Prompt

Use this prompt template after extracting a transcript with `fetch_transcript.py`.

---

## For single video summary

```
Summarize the following YouTube video transcript. Output in Markdown format.

Requirements:
1. Start with a 2-3 sentence overview
2. List 5-8 key takeaways as bullet points
3. Include notable quotes (if any) with timestamps
4. End with a "Who should watch this?" section
5. Output language should match the transcript language

Transcript:
{paste transcript here}
```

## For multi-video comparison (channel/playlist)

```
I have transcripts from {N} YouTube videos. For each video:

1. Write a 1-sentence summary
2. List the top 3 key points
3. Rate relevance to [topic] on a scale of 1-5

Then provide:
- A comparison table of all videos
- Your top recommendation and why

Transcripts:
{paste transcripts here, separated by dividers}
```

## For content repurposing (blog post / social media)

```
Transform the following YouTube transcript into a blog post.

Requirements:
1. Catchy title (under 60 characters)
2. Opening hook paragraph
3. Organized into 4-6 sections with H2 headings
4. Keep the original speaker's voice and tone
5. Add a conclusion with actionable takeaways
6. Target length: 800-1200 words
7. Language: {Chinese/English}

Transcript:
{paste transcript here}
```

## For Chinese social media (小红书/公众号)

```
将以下YouTube视频转录稿改写为一篇小红书笔记。

要求：
1. 标题吸引眼球，不超过25个字
2. 正文800-1200字，口语化，娓娓道来
3. 分3-5个小节，每节有小标题
4. 关键信息加粗
5. 末尾加3-5个相关话题标签
6. 保持原文干货内容，不要编造信息

Transcript:
{paste transcript here}
```
