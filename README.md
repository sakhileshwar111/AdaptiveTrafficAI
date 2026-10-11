# 🚦 Adaptive Traffic Signal Optimization

**Next-Generation Intersection AI designed for Indian Traffic Conditions**

A dual-AI traffic control system that abandons rigid western timers in favor of mathematical bidding and Deep Reinforcement Learning. It handles chaotic, heterogeneous driving conditions by processing spatial occupancy and penalizing wait times to mathematically eliminate gridlock.
<img width="1431" height="544" alt="image" src="https://github.com/user-attachments/assets/9765f7f6-5280-4e84-ac09-8a2f7d4b4851" />


---

## 🌟 Key Features

### 1. Dual-AI Architecture
* **The Production AI (Algorithmic Bidding):** A safe, highly deterministic controller that recalculates congestion scores every few seconds. Instead of a fixed loop (North ➔ South ➔ East), it instantly hands the green light to the highest bidder.
* **The Experimental AI (Deep RL):** Included is a massive Deep Reinforcement Learning Agent (`ppo_traffic_model_1M.zip`) trained via Proximal Policy Optimization for 1,000,000 timesteps using a custom Anti-Starvation reward function.

### 2. Indian Infrastructure Physics
* **Heterogeneous Mixed Lanes:** We explicitly configured the `netconvert` connections to allow both Center and Rightmost lanes to simultaneously go straight and turn right, accurately modeling real-world Indian junctions.
* **Absolute Split Phasing:** Because mixed lanes cause physical crossover collisions in simulations, the AI isolates traffic into 4 strictly sequential phases, ensuring 100% collision-free throughput.

### 3. Hyper-Optimizations
* **Spatial Occupancy Sensing:** Standard algorithms count cars. This AI calculates the raw percentage of asphalt covered by metal (0-100%), effortlessly handling the "3 bikes in 1 car space" problem.
* **Straggler Cutoff:** The AI holds the green light to flush heavy platoons but aggressively cuts the signal if only 1 or 2 slow stragglers remain, preventing wasted cycle time.
* **All-Red Clearance:** A mandatory 2-second `rrrrr` lockdown after every yellow light ensures heavy trucks taking wide turns clear the box before cross-traffic enters.

### 4. Advanced Safety Modules
* **Cloud-GPS Ambulance Preemption:** The AI constantly scans a 500m global radius. If an ambulance is detected, it artificially injects a massive score (`999,999`) to instantly trigger an Emergency Lockdown.
* **Dilemma-Zone Radar:** Dynamic TraCI speed tracking detects if a vehicle is approaching a yellow light too fast to stop safely, automatically overriding the timer to extend the yellow phase.

---

## 🚀 Setup & Execution

### Prerequisites
* **Python 3.8+**
* **Eclipse SUMO (Simulation of Urban MObility)**
* **Gymnasium & Stable-Baselines3** (for the RL model)

### Installation
1. Clone this repository and navigate to the directory.
2. Install the required Python packages:
   ```bash
   pip install traci gymnasium stable-baselines3
   ```
3. Generate the custom intersection physics and routes:
   ```bash
   python3 setup_sumo.py
   ```

### Running the Production AI (Bidding Controller)
To run the primary adaptive controller and watch the mathematical bidding in real-time:
```bash
python3 sumo_adaptive_controller.py
```
*(Append `--nogui` to run a high-speed headless benchmark).*

### Running the Deep Learning AI (PPO)
To witness the Reinforcement Learning agent control the intersection using its trained neural network:
```bash
python3 test_rl.py
```

---
## 📊 Benchmarks
Under extreme stress-testing (1,600+ mixed-lane vehicles), the Adaptive Bidding AI successfully flushed the entire grid in exactly **2,598 steps** without a single stranding event, while a standard fixed-timer controller resulted in permanent gridlock.
