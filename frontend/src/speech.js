// Web Speech API 发音：词汇记忆页和拼写测试页共用
let cachedVoice = null

function pickVoice() {
  if (cachedVoice) return cachedVoice
  const vs = typeof window !== 'undefined' && window.speechSynthesis ? window.speechSynthesis.getVoices() : []
  const en = vs.filter((v) => /^en(-|_)?/i.test(v.lang))
  const priority = [
    'Samantha',
    'Daniel',
    'Google US English',
    'Google UK English Male',
    'Google UK English Female',
    'Alex',
    'Karen',
  ]
  for (const name of priority) {
    const v = en.find((x) => x.name.includes(name))
    if (v) {
      cachedVoice = v
      return v
    }
  }
  cachedVoice = en.length ? en[0] : vs[0] || null
  return cachedVoice
}

// 首次 voices 可能为空，加载完成后刷新缓存
if (typeof window !== 'undefined' && window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => {
    cachedVoice = null
    pickVoice()
  }
}

function hasEnglish(text) {
  return /[a-zA-Z]/.test(text)
}
function hasChinese(text) {
  return /[\u4e00-\u9fa5]/.test(text)
}

export function speak(text) {
  if (!text) return
  if (typeof window === 'undefined' || !window.speechSynthesis) return
  try {
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(text)
    if (hasEnglish(text)) {
      u.lang = 'en-US'
      const v = pickVoice()
      if (v) u.voice = v
    } else if (hasChinese(text)) {
      u.lang = 'zh-CN'
    } else {
      u.lang = 'en-US'
    }
    u.rate = 0.95
    u.pitch = 1
    window.speechSynthesis.speak(u)
  } catch (e) {
    // 发音失败不影响主流程
  }
}

export { pickVoice }
