<template>
  <div class="chat-container">
    <!-- 消息列表 -->
    <div class="messages" ref="messagesContainer">
      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="['message', msg.role]"
      >
        <div class="message-header">
          <span class="role">{{ msg.role === 'user' ? '用户' : '助手' }}</span>
        </div>
        <div class="message-content">{{ msg.content }}</div>

        <!-- ReAct 推理步骤 -->
        <div v-if="msg.steps && msg.steps.length > 0" class="react-steps">
          <div class="steps-header">
            <span class="steps-title">ReAct 推理过程</span>
            <span class="steps-count">{{ msg.steps.length }} 步</span>
          </div>
          <div class="steps-list">
            <div
              v-for="(step, idx) in msg.steps"
              :key="idx"
              :class="['step-item', step.step_type]"
            >
              <span class="step-label">{{ getStepLabel(step.step_type) }}</span>
              <span class="step-content">{{ step.content }}</span>
            </div>
          </div>
        </div>

        <!-- 性能指标 -->
        <div v-if="msg.metrics" class="metrics-info">
          <div class="metrics-header">
            <span class="metrics-title">性能指标</span>
            <span v-if="msg.metrics.duration" class="duration">{{ msg.metrics.duration.toFixed(2) }}s</span>
          </div>
          <div class="metrics-grid">
            <div class="metric-item">
              <span class="metric-label">LLM 调用</span>
              <span class="metric-value">{{ msg.metrics.llm_calls }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">工具调用</span>
              <span class="metric-value">{{ msg.metrics.tool_calls }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Token 消耗</span>
              <span class="metric-value">{{ formatNumber(msg.metrics.tokens_used) }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">迭代次数</span>
              <span class="metric-value">{{ msg.metrics.iterations }}</span>
            </div>
          </div>
        </div>

        <!-- 意图分析结果 -->
        <div v-if="msg.intent" class="intent-info">
          <div class="intent-header">
            <span class="intent-title">意图分析</span>
            <span class="confidence">置信度: {{ (msg.intent.confidence * 100).toFixed(1) }}%</span>
          </div>
          <div class="intent-details">
            <div class="intent-item">
              <span class="label">查询类型:</span>
              <span class="value query-type">{{ msg.intent.query_type }}</span>
            </div>
            <div v-if="msg.intent.entities && msg.intent.entities.length > 0" class="intent-item">
              <span class="label">实体:</span>
              <span class="value">{{ msg.intent.entities.join(', ') }}</span>
            </div>
            <div v-if="msg.intent.keywords && msg.intent.keywords.length > 0" class="intent-item">
              <span class="label">关键词:</span>
              <span class="value">{{ msg.intent.keywords.join(', ') }}</span>
            </div>
            <div class="intent-item">
              <span class="label">复杂度:</span>
              <span class="value complexity" :class="msg.intent.complexity">
                {{ msg.intent.complexity }}
              </span>
            </div>
            <div v-if="msg.intent.requires && msg.intent.requires.length > 0" class="intent-item">
              <span class="label">所需能力:</span>
              <span class="value">{{ msg.intent.requires.join(', ') }}</span>
            </div>
            <div v-if="msg.intent.suggested_strategy" class="intent-item">
              <span class="label">建议策略:</span>
              <span class="value strategy">{{ msg.intent.suggested_strategy }}</span>
            </div>
            <div v-if="msg.intent.reasoning" class="intent-item reasoning">
              <span class="label">推理:</span>
              <span class="value">{{ msg.intent.reasoning }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="message assistant loading">
        <div class="message-content">
          <span class="spinner"></span>
          <span>思考中...</span>
        </div>
      </div>
    </div>

    <!-- 输入框 -->
    <div class="input-area">
      <textarea
        v-model="inputMessage"
        @keydown.enter.prevent="sendMessage"
        placeholder="输入消息... (Enter 发送)"
        :disabled="loading"
        rows="3"
      ></textarea>
      <button @click="sendMessage" :disabled="loading || !inputMessage.trim()">
        {{ loading ? '发送中...' : '发送' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { chatApi } from '../api/chat'

const messages = ref([])
const inputMessage = ref('')
const loading = ref(false)
const messagesContainer = ref(null)

// 聊天历史（用于 API 调用）
const chatHistory = ref([])

// ReAct 步骤类型标签映射
const stepLabels = {
  user: '用户',
  thought: '思考',
  action: '行动',
  observation: '观察',
  answer: '答案',
  error: '错误'
}

function getStepLabel(stepType) {
  return stepLabels[stepType] || stepType.toUpperCase()
}

function formatNumber(num) {
  if (num >= 10000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

async function sendMessage() {
  const message = inputMessage.value.trim()
  if (!message || loading.value) return

  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: message
  })

  inputMessage.value = ''
  loading.value = true

  // 滚动到底部
  await nextTick()
  scrollToBottom()

  try {
    // 调用 API
    const response = await chatApi.sendMessage(message, chatHistory.value)

    // 添加助手回复
    messages.value.push({
      role: 'assistant',
      content: response.message,
      intent: response.intent,
      steps: response.steps,
      metrics: response.metrics
    })

    // 更新历史
    chatHistory.value.push(
      { role: 'user', content: message },
      { role: 'assistant', content: response.message }
    )

  } catch (error) {
    messages.value.push({
      role: 'assistant',
      content: `错误: ${error.message}`
    })
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 900px;
  margin: 0 auto;
  background: #1a1a1a;
  color: #e0e0e0;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.message {
  margin-bottom: 20px;
  padding: 15px;
  border-radius: 8px;
  background: #2a2a2a;
}

.message.user {
  background: #1e3a5f;
  margin-left: 20%;
}

.message.assistant {
  background: #2a2a2a;
  margin-right: 20%;
}

.message-header {
  margin-bottom: 8px;
}

.role {
  font-size: 12px;
  color: #888;
  text-transform: uppercase;
}

.message-content {
  line-height: 1.6;
  white-space: pre-wrap;
}

.message.loading .message-content {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #888;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #444;
  border-top-color: #4a9eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ReAct 推理步骤 */
.react-steps {
  margin-top: 15px;
  padding: 12px;
  background: #1e1e1e;
  border-radius: 6px;
  border-left: 3px solid #9c27b0;
}

.steps-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.steps-title {
  font-size: 13px;
  font-weight: 600;
  color: #9c27b0;
}

.steps-count {
  font-size: 11px;
  color: #888;
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.step-item {
  display: flex;
  gap: 10px;
  font-size: 12px;
  padding: 8px;
  background: #252525;
  border-radius: 4px;
}

.step-label {
  min-width: 50px;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px;
}

.step-item.thought .step-label {
  background: #4a9eff;
  color: white;
}

.step-item.action .step-label {
  background: #ff9800;
  color: white;
}

.step-item.observation .step-label {
  background: #4caf50;
  color: white;
}

.step-item.answer .step-label {
  background: #9c27b0;
  color: white;
}

.step-item.error .step-label {
  background: #f44336;
  color: white;
}

.step-content {
  color: #aaa;
  line-height: 1.4;
}

/* 意图信息 */
.intent-info {
  margin-top: 15px;
  padding: 12px;
  background: #1e1e1e;
  border-radius: 6px;
  border-left: 3px solid #4a9eff;
}

.intent-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.intent-title {
  font-size: 13px;
  font-weight: 600;
  color: #4a9eff;
}

.confidence {
  font-size: 11px;
  color: #888;
}

.intent-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.intent-item {
  display: flex;
  gap: 8px;
  font-size: 13px;
}

.intent-item .label {
  color: #666;
  min-width: 80px;
}

.intent-item .value {
  color: #aaa;
}

.query-type {
  color: #4a9eff;
  font-weight: 500;
}

.complexity.low {
  color: #4caf50;
}

.complexity.medium {
  color: #ff9800;
}

.complexity.high {
  color: #f44336;
}

.strategy {
  color: #9c27b0;
  font-weight: 500;
}

.intent-item.reasoning {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #333;
}

.intent-item.reasoning .value {
  color: #888;
  font-style: italic;
}

/* 性能指标 */
.metrics-info {
  margin-top: 15px;
  padding: 12px;
  background: #1e1e1e;
  border-radius: 6px;
  border-left: 3px solid #00bcd4;
}

.metrics-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.metrics-title {
  font-size: 13px;
  font-weight: 600;
  color: #00bcd4;
}

.duration {
  font-size: 12px;
  color: #4caf50;
  font-weight: 600;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px;
  background: #252525;
  border-radius: 4px;
}

.metric-label {
  font-size: 10px;
  color: #888;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: #00bcd4;
}

/* 输入区域 */
.input-area {
  display: flex;
  gap: 10px;
  padding: 20px;
  background: #1a1a1a;
  border-top: 1px solid #333;
}

.input-area textarea {
  flex: 1;
  padding: 12px;
  border: 1px solid #333;
  border-radius: 6px;
  background: #2a2a2a;
  color: #e0e0e0;
  font-family: inherit;
  font-size: 14px;
  resize: none;
}

.input-area textarea:focus {
  outline: none;
  border-color: #4a9eff;
}

.input-area button {
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  background: #4a9eff;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.input-area button:hover:not(:disabled) {
  background: #3a8eef;
}

.input-area button:disabled {
  background: #444;
  cursor: not-allowed;
}
</style>
