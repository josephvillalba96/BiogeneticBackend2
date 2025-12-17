module.exports = {
  apps: [
    {
      name: "fastapi",
      script: "venv/bin/uvicorn",
      args: "main:app --host 127.0.0.1 --port 8000",
      interpreter: "none",
      autorestart: true,
      watch: false,
    }
  ]
};
