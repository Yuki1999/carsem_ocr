import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './style.css'

const BOOT_RECOVER_FLAG = 'carsem_ocr_boot_recovered_v1'

function tryRecoverAndReload() {
  try {
    if (sessionStorage.getItem(BOOT_RECOVER_FLAG) === '1') return false
    sessionStorage.setItem(BOOT_RECOVER_FLAG, '1')
    window.location.reload()
    return true
  } catch {
    return false
  }
}

function renderBootError(error) {
  const root = document.getElementById('app')
  if (!root) return
  root.innerHTML = `
    <section style="max-width:780px;margin:48px auto;padding:24px;border:1px solid #f2c9c9;border-radius:12px;background:#fff8f8;color:#7b1f1f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;">
      <h2 style="margin:0 0 10px;font-size:20px;">前端启动失败</h2>
      <p style="margin:0 0 8px;">页面脚本加载异常，请刷新页面后重试。</p>
      <p style="margin:0 0 12px;">如果仍失败，请打开浏览器控制台并把错误信息发给开发者。</p>
      <pre style="margin:0;padding:10px;border-radius:8px;background:#fff;border:1px solid #f0d2d2;white-space:pre-wrap;word-break:break-word;">${String(error && error.message ? error.message : error)}</pre>
    </section>
  `
}

async function bootstrap() {
  try {
    const { default: App } = await import('./App.vue')
    const app = createApp(App)
    app.use(ElementPlus)
    app.config.errorHandler = (error, _instance, info) => {
      console.error('[VueError]', info, error)
      if (tryRecoverAndReload()) return
      renderBootError(error)
    }
    app.mount('#app')
  } catch (error) {
    console.error('[BootError]', error)
    if (tryRecoverAndReload()) return
    renderBootError(error)
  }
}

bootstrap()
