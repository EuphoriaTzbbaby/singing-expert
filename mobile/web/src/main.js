import { createApp } from 'vue'
import App from './App.vue'

// 注意：mobile.css 必须放在最后引入。
// 静态 import 会按源码顺序深度优先求值，App.vue 及其子组件的 <style> 会先注入，
// 这样手机端的覆盖样式才排在后头、能在同优先级下生效。
import './mobile.css'

createApp(App).mount('#app')
