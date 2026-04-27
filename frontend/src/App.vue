<template>
  <div id="app">
    <header class="app-header">
      <h1>Agentic GraphRAG</h1>
      <p class="subtitle">智能意图理解 + 知识图谱检索</p>
    </header>
    <main class="app-main">
      <ChatInterface />
    </main>
  </div>
</template>

<script setup>
import ChatInterface from './components/ChatInterface.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background: #0d0d0d;
  color: #e0e0e0;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  padding: 20px;
  text-align: center;
  background: #111;
  border-bottom: 1px solid #333;
}

.app-header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #4a9eff;
}

.subtitle {
  font-size: 14px;
  color: #666;
  margin-top: 5px;
}

.app-main {
  flex: 1;
}
</style>
