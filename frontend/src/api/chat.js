/**
 * 聊天 API 客户端
 */
const API_BASE = 'http://localhost:8000/api/v1'

/**
 * 发送聊天消息
 */
export async function sendMessage(message, history = [], systemPrompt = null) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message,
      history: history || [],
      system_prompt: systemPrompt
    })
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || `HTTP error! status: ${response.status}`)
  }

  return await response.json()
}

export const chatApi = {
  sendMessage,
  getTools: async () => {
    const response = await fetch(`${API_BASE}/tools/list`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }
}
