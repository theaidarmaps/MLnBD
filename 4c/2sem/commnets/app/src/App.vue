<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import axios from 'axios'
import type { Data } from '@/interfaces.ts'

const text: Ref<string, string> = ref('')
const results: Ref<Data | null> = ref(null)

const analyze = async () => {
  if (!text.value) return

  await axios
    .post('http://127.0.0.1:8000/predict', {
      text: text.value,
    })
    .then((res) => {
      results.value = res.data
    })
    .catch((err) => {
      console.log(err)
    })
}

const translate = (label: string) => {
  const dict: { [key: string]: string } = {
    normal: 'Нормальный',
    insult: 'Оскорбление',
    threat: 'Угроза',
    obscenity: 'Непристойность',
  }
  return dict[label] || label
}

const verdict = computed(() => {
  if (!results.value) return { text: '', type: '' }

  const isToxic =
    results.value.predictions.insult > 0.5 ||
    results.value.predictions.threat > 0.5 ||
    results.value.predictions.obscenity > 0.5

  if (isToxic) {
    return { text: 'Комментарий отрицательный', type: 'bad' }
  }
  return { text: 'Комментарий положительный', type: 'good' }
})

const getProgressColor = (label: string) => {
  const colors: { [key: string]: string[] } = {
    normal: ['#dcfce7', '#22c55e'],
    insult: ['#fee2e2', '#ef4444'],
    threat: ['#ffedd5', '#f97316'],
    obscenity: ['#f3e8ff', '#a855f7'],
  }
  const [bg, color] = colors[label] || ['#e2e8f0', '#64748b']
  return { bg, color }
}
</script>

<template>
  <div class="wrapper">
    <div class="main-container">
      <div class="header">
        <h1>Анализ токсичности комментариев</h1>
      </div>

      <div class="input-section">
        <textarea
          v-model="text"
          placeholder="Введите комментарий для анализа..."
          :class="{ 'has-text': text }"
        ></textarea>

        <button @click="analyze" :disabled="!text">
          <span class="btn-text">Проверить комментарий</span>
          <span class="btn-icon">→</span>
        </button>
      </div>

      <div v-if="results" class="results-section">
        <div class="verdict-card" :class="verdict.type">
          <div class="verdict-icon">{{ verdict.type === 'good' ? '✨' : '⚡' }}</div>
          <div class="verdict-text">{{ verdict.text }}</div>
        </div>

        <div class="stats-container">
          <div class="stats-title">
            <span>Детальный анализ</span>
          </div>

          <div v-for="(prob, label) in results.predictions" :key="label" class="stat-item">
            <div class="stat-label">
              <span>{{ translate(label) }}</span>
              <strong :style="{ color: getProgressColor(label).color }">
                {{ (prob * 100).toFixed(1) }}%
              </strong>
            </div>
            <div class="progress-bar-bg" :style="{ backgroundColor: getProgressColor(label).bg }">
              <div
                class="progress-bar-fill"
                :style="{
                  width: `${prob * 100}%`,
                  backgroundColor: getProgressColor(label).color,
                }"
              ></div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">
        <p>Введите текст и нажмите "Проверить"</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family:
    'Inter',
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    Roboto,
    sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.wrapper {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

.main-container {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 32px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  padding: 32px;
}

.header {
  text-align: center;
  margin-bottom: 32px;
}

.header h1 {
  font-size: 28px;
  font-weight: 700;
  background: black;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 8px;
}

.input-section {
  margin-bottom: 32px;
}

textarea {
  width: 100%;
  height: 120px;
  padding: 16px;
  border: 2px solid #e2e8f0;
  border-radius: 20px;
  font-size: 15px;
  font-family: inherit;
  resize: none;
  transition: all 0.3s ease;
  background: white;
  margin-bottom: 16px;
}

textarea:focus {
  outline: none;
  border-color: #957dad;
}

textarea.has-text {
  border-color: #957dad;
}

button {
  width: 100%;
  padding: 16px 24px;
  background-color: #957dad;
  color: white;
  border: none;
  border-radius: 20px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.3s ease;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
  box-shadow: none;
}

.btn-icon {
  font-size: 20px;
  transition: transform 0.3s ease;
}

button:hover:not(:disabled) .btn-icon {
  transform: translateX(5px);
}

.results-section {
  animation: slideUp 0.5s ease;
}

.verdict-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  border-radius: 20px;
  margin-bottom: 24px;
}

.verdict-card.good {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border-left: 4px solid #22c55e;
}

.verdict-card.bad {
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  border-left: 4px solid #ef4444;
}

.verdict-icon {
  font-size: 28px;
}

.verdict-text {
  font-size: 18px;
  font-weight: 600;
}

.verdict-card.good .verdict-text {
  color: #166534;
}

.verdict-card.bad .verdict-text {
  color: #991b1b;
}

.stats-container {
  background: #f8fafc;
  border-radius: 20px;
  padding: 20px;
}

.stats-title {
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
  color: #334155;
}

.stat-item {
  margin-bottom: 16px;
}

.stat-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 14px;
  color: #475569;
}

.progress-bar-bg {
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.5s ease;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  background: #f8fafc;
  border-radius: 20px;
}

.empty-state p {
  color: #64748b;
  font-size: 15px;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
