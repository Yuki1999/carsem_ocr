module.exports = {
  apps: [
    {
      name: 'carsem-ocr-backend',
      cwd: '/home/sip-telecom/Services/carsem_ocr',
      script: 'python',
      args: '-m uvicorn app.main:app --host 0.0.0.0 --port 16068',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_restarts: 20,
      env: {
        PYTHONUNBUFFERED: '1',
      },
      error_file: '/home/sip-telecom/Services/carsem_ocr/output/logs/backend.err.log',
      out_file: '/home/sip-telecom/Services/carsem_ocr/output/logs/backend.out.log',
      time: true,
    },
    {
      name: 'carsem-ocr-frontend',
      cwd: '/home/sip-telecom/Services/carsem_ocr/frontend',
      script: 'npm',
      args: 'run dev -- --host 0.0.0.0 --port 16066',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_restarts: 20,
      error_file: '/home/sip-telecom/Services/carsem_ocr/output/logs/frontend.err.log',
      out_file: '/home/sip-telecom/Services/carsem_ocr/output/logs/frontend.out.log',
      time: true,
    },
  ],
}
