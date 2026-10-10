import os
import sys
import gymnasium as gym
from stable_baselines3 import PPO
from train_rl import SumoTrafficEnv
import traci
import csv

def get_gps_emergency_phase():
    """
    Simulates a GPS Cloud Integration. 
    """
    for v_id in traci.vehicle.getIDList():
        if traci.vehicle.getVehicleClass(v_id) == "emergency":
            edge = traci.vehicle.getRoadID(v_id)
            if edge.endswith("2C"):
                distance_to_light = 500.0 - traci.vehicle.getLanePosition(v_id)
                if distance_to_light <= 500.0:
                    lane = traci.vehicle.getLaneID(v_id)
                    if "N2C" in lane or "S2C" in lane:
                        return 1 if lane.endswith("_2") else 0
                    else:
                        return 3 if lane.endswith("_2") else 2
    return None

def run_test():
    print("Loading 1-Million Step Advanced PPO Traffic Model...")
    try:
        model = PPO.load("ppo_traffic_model_1M")
    except FileNotFoundError:
        print("Error: 'ppo_traffic_model_1M.zip' not found.")
        return
        
    print("Model loaded! Launching SUMO GUI at full speed...")
    env = SumoTrafficEnv(render_mode="human")
    obs, info = env.reset()
    
    terminated = False
    step = 0
    
    # Analytics tracking
    dataset = []
    total_vehicles_processed = set()
    
    print("RL Agent is now in control with GPS EMERGENCY PREEMPTION active!")
    
    while not terminated:
        step += 1
        
        # Check global GPS coordinates for incoming ambulances
        emergency_action = get_gps_emergency_phase()
        
        if emergency_action is not None:
            action = emergency_action
            if step % 5 == 0: # Print occasionally to avoid spam
                print(f"--- Step {step} | [!] GPS ALERT! Ambulance detected! Preempting to Phase {action} ---")
        else:
            # Normal RL behavior
            action, _states = model.predict(obs, deterministic=True)
            
        # Collect Analytics before stepping
        ns_q = 0
        ew_q = 0
        ns_wait = 0
        ew_wait = 0
        
        for lane in traci.trafficlight.getControlledLanes("C"):
            q_len = traci.lane.getLastStepHaltingNumber(lane)
            wait_time = traci.lane.getWaitingTime(lane)
            vehicles = traci.lane.getLastStepVehicleIDs(lane)
            total_vehicles_processed.update(vehicles)
            
            if "N2C" in lane or "S2C" in lane:
                ns_q += q_len
                ns_wait = max(ns_wait, wait_time)
            else:
                ew_q += q_len
                ew_wait = max(ew_wait, wait_time)
                
        dataset.append({
            "step": step,
            "strategy": "Reinforcement_Learning",
            "action_phase": action,
            "ns_queue": ns_q,
            "ns_wait": ns_wait,
            "ew_queue": ew_q,
            "ew_wait": ew_wait,
            "emergency_present": 1 if emergency_action is not None else 0
        })
            
        # Output Live Dashboard every 20 steps
        if step % 20 == 0 and emergency_action is None:
            print(f"--- Step {step} | RL Action Phase: {action} ---")
            print(f"  N/S Traffic -> Queue: {ns_q:3d}, Max Wait: {ns_wait:5.1f}s")
            print(f"  E/W Traffic -> Queue: {ew_q:3d}, Max Wait: {ew_wait:5.1f}s")
            
        obs, reward, terminated, truncated, info = env.step(action)
        
    env.close()
    
    # Save Results
    filename = "dataset_rl.csv"
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=dataset[0].keys())
        writer.writeheader()
        writer.writerows(dataset)
        
    avg_q = sum(d["ns_queue"] + d["ew_queue"] for d in dataset) / len(dataset)
    print("\n==================================================")
    print(f"✅ SIMULATION COMPLETE!")
    print(f"📊 Final Dataset saved to '{filename}'")
    print(f"🚗 Total Vehicles Processed: {len(total_vehicles_processed)}")
    print(f"📉 Average Queue Length: {avg_q:.2f} vehicles")
    print("==================================================")

if __name__ == "__main__":
    run_test()
