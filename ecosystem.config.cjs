const path = require('path')
const fs = require('fs')

const repoRoot = __dirname
const backendLogDir = path.join(repoRoot, 'output', 'logs')
const frontendLogDir = path.join(repoRoot, 'frontend', 'output')
const venvPython = path.join(repoRoot, '.venv', 'bin', 'python')
const backendPython = fs.existsSync(venvPython) ? venvPython : 'python3'

module.exports = {
  apps: [
    {
      name: 'carsem-ocr-backend',
      cwd: repoRoot,
      script: backendPython,
      args: '-m uvicorn app.main:app --host 0.0.0.0 --port 16068',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_restarts: 20,
      env: {
        PYTHONUNBUFFERED: '1',
      },
      error_file: path.join(backendLogDir, 'backend.err.log'),
      out_file: path.join(backendLogDir, 'backend.out.log'),
      time: true,
    },
    {
      name: 'carsem-ocr-frontend',
      cwd: path.join(repoRoot, 'frontend'),
      script: 'npm',
      args: 'run dev -- --host 0.0.0.0 --port 16066',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_restarts: 20,
      error_file: path.join(frontendLogDir, 'frontend.err.log'),
      out_file: path.join(frontendLogDir, 'frontend.out.log'),
      time: true,
    },
  ],
}
