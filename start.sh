#!/bin/bash

cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

cd ../frontend && npm run dev &
FRONTEND_PID=$!

wait $BACKEND_PID $FRONTEND_PID
