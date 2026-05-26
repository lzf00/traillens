/**
 * 极简 SSE 客户端,绕开 EventSource(EventSource 不支持 POST + headers)。
 * 用 fetch + ReadableStream 自己解析 W3C SSE 格式。
 */

export type SseEvent = { event: string; data: any };

export async function* streamSse(
  url: string,
  init?: RequestInit,
): AsyncGenerator<SseEvent> {
  const resp = await fetch(url, {
    method: "POST",
    ...init,
    headers: {
      Accept: "text/event-stream",
      ...(init?.headers || {}),
    },
  });
  if (!resp.body) return;

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // 按 SSE 规范:消息间用空行分割
    let idx;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const chunk = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const parsed = parseChunk(chunk);
      if (parsed) yield parsed;
    }
  }
}

function parseChunk(chunk: string): SseEvent | null {
  let event = "message";
  let data = "";
  for (const line of chunk.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice(7).trim();
    else if (line.startsWith("data: ")) data += line.slice(6);
  }
  if (!data) return null;
  try {
    return { event, data: JSON.parse(data) };
  } catch {
    return { event, data };
  }
}
