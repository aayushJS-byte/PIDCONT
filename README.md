# AI Control System Dashboard

A production-grade closed-loop control simulator with PID and AI controllers,
built directly from the theory in *Linear Closed-Loop Systems* (pages 171–177).

## What it does

Simulates the full feedback control loop:

```
y_sp → [Comparator] → [Controller g_c(s)] → [Process g_p(s)] → y
              ↑                                        |
              └──────── [Sensor g_m(s)] ←─────────────┘
                              d(s) disturbance ↑
```

Two controller modes:
- **PID** — classic industry-standard, manually tuned
- **AI Neural Controller** — learned via Evolution Strategies, outperforms PID on complex processes

Two control scenarios (from page 177):
- **Servo problem** — setpoint changes, no disturbance
- **Regulator problem** — setpoint fixed, disturbance enters

## Quick start

```bash
# 1. Clone / download the project
cd ai_control_dashboard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run tests (optional but recommended)
pytest tests/ -v

# 4. Launch dashboard (ALWAYS run from project root)
streamlit run dashboard/app.py
```

## Project structure

```
ai_control_dashboard/
├── core/
│   ├── process.py       # g_p(s) — FirstOrderProcess, SecondOrderProcess
│   ├── controllers.py   # g_c(s) — PIDController, NeuralController
│   ├── simulator.py     # closed-loop runner (implements eq.5, page 175)
│   └── metrics.py       # ISE, IAE, ITAE, overshoot, settling time
├── ai/
│   └── trainer.py       # Evolution Strategies training loop
├── dashboard/
│   └── app.py           # Streamlit UI
├── tests/
│   └── test_simulator.py
└── requirements.txt
```

## Using the AI controller

1. Open the sidebar → section ② Controller
2. Select "AI Neural Controller"
3. Set training iterations (200 is a good start)
4. Click "Train AI Controller" — takes ~30 seconds
5. Switch between PID and AI to compare on the side-by-side plot

## Theory reference

| Equation | Location | Implementation |
|----------|----------|----------------|
| y(s) = g_p·m(s) + g_d·d(s) | Page 171, eq.1 | `process.step()` |
| y_m(s) = g_m·y(s) | Page 171, eq.2 | `run_simulation()` |
| ε(s) = y_sp - y_m | Page 172, eq.3 | `run_simulation()` |
| c'(s) = g_c·ε(s) | Page 172, eq.4 | `controller.compute()` |
| Closed-loop eq. (5) | Page 175 | `run_simulation()` full loop |
| Servo problem | Page 177, C1 | "Servo" scenario |
| Regulator problem | Page 177, C2 | "Regulator" scenario |# PIDCONT
