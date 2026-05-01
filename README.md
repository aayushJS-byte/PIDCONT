# ⚙️ PID Control System Dashboard

An interactive engineering dashboard for simulating and analyzing **closed-loop control systems** using PID controllers.

This project bridges **Chemical Engineering control theory** with **modern interactive visualization**, enabling real-time experimentation with system dynamics, controller tuning, and performance evaluation.

---

## 🧠 Theoretical Background

A standard closed-loop control system is defined as:

y_sp → Comparator → Controller → Process → Output (y)  
                                             ↑  
                                      Feedback (y_m)  

Where:

- **y_sp(t)** = setpoint  
- **y(t)** = process output  
- **y_m(t)** = measured output  
- **e(t)** = error = y_sp(t) − y_m(t)  

---

### 📌 Core Equations

Error:
e(t) = y_sp(t) − y_m(t)

PID Controller:
u(t) = Kc [ e(t) + (1/τI) ∫ e(t) dt + τD (de/dt) ]

Process (example first-order):
τ dy/dt + y = K u(t)

Closed-loop transfer function:
Y(s)/Y_sp(s) = Gc(s)Gp(s) / [1 + Gc(s)Gp(s)]

---

## 🚀 Features

### 🔧 Process Models
- First-order systems (FOPDT-style)
- Second-order systems
- Disturbance modeling
- Adjustable gain, time constant, damping

---

### 🎛️ PID Controller
- Manual tuning (Kc, τI, τD)
- Ziegler–Nichols tuning
- Real-time parameter control

---

### ⚡ Control Scenarios
- Servo (setpoint tracking)
- Regulator (disturbance rejection)
- Combined mode

---

### 📊 Visualization
- Output response y(t)
- Control signal u(t)
- Error signal e(t)
- Setpoint tracking

---

### 📈 Performance Metrics

Integral Square Error (ISE):
ISE = ∫ e²(t) dt

Overshoot:
OS% = (y_max − y_ss)/y_ss × 100

Settling Time:
Time required for output to remain within tolerance band

Steady-State Error:
e_ss = |y_sp − y|

---

### 🔍 Comparison Mode
- Manual vs Ziegler–Nichols tuning
- Performance comparison
- Best controller identification

---

### 📤 Export
- Download plots (PNG / PDF)
- Export simulation results (JSON)

---

## 🛠️ Tech Stack

- Python  
- Streamlit  
- Plotly  
- NumPy  

---

## ▶️ How to Run

git clone https://github.com/aayushJS-byte/PIDCONT.git  
cd PIDCONT  
pip install -r requirements.txt  
streamlit run dashboard/app.py  

---

## 📂 Project Structure

PIDCONT/  
├── core/  
├── dashboard/  
├── requirements.txt  
└── README.md  

---

## 🎯 Future Work

- IMC tuning  
- MPC controller  
- Adaptive PID  
- Chemical reactor models  

---

## ⭐

If you found this useful, consider starring the repo!
