import traci
import sys
import os
import optparse
import csv

def get_options():
    opt_parser = optparse.OptionParser()
    opt_parser.add_option("--nogui", action="store_true", default=False, help="run the commandline version of sumo")
    opt_parser.add_option("--strategy", type="string", default="adaptive", help="traffic strategy: adaptive or fixed")
    options, args = opt_parser.parse_args()
    return options

def calculate_score(occupancy_pct, max_wait):
    wait_penalty = (max_wait / 10.0) ** 2  
    return (occupancy_pct * 2.5) + wait_penalty

def check_dilemma_zone():
    for lane in traci.trafficlight.getControlledLanes("C"):
        for v_id in traci.lane.getLastStepVehicleIDs(lane):
            speed = traci.vehicle.getSpeed(v_id) 
            dist_to_intersection = 200.0 - traci.vehicle.getLanePosition(v_id)
            if speed > 10.0 and 10.0 < dist_to_intersection < 45.0:
                return True
    return False

def run_control(strategy="adaptive"):
    print(f"Starting SUMO with ALL-RED CLEARANCE '{strategy.upper()}' strategy...")
    tl_id = "C"
    
    MIN_GREEN_TIME = 15
    MAX_GREEN_TIME = 45
    FIXED_GREEN_TIME = 35
    
    MIN_YELLOW = 2
    MAX_YELLOW = 6
    ALL_RED_TIME = 2  # Reduced to 2s for snappier turnover
    
    # 12-STEP SEQUENCE: Green -> Yellow -> All Red (Clearance)
    # The clearance phase prevents cars from getting stranded in the junction!
    phases = [
        # North Sequence
        {"state": "rrrrrrrrrrGGGGGrrrrr", "name": "Phase 1: NORTH Full Green", "dir": "North"},
        {"state": "rrrrrrrrrryyyyyrrrrr", "name": "Yellow 1", "is_yellow": True, "next_idx": 2},
        {"state": "rrrrrrrrrrrrrrrrrrrr", "name": "Clearance 1 (All Red)", "is_clearance": True, "next_idx": 3},
        
        # South Sequence
        {"state": "GGGGGrrrrrrrrrrrrrrr", "name": "Phase 2: SOUTH Full Green", "dir": "South"},
        {"state": "yyyyyrrrrrrrrrrrrrrr", "name": "Yellow 2", "is_yellow": True, "next_idx": 5},
        {"state": "rrrrrrrrrrrrrrrrrrrr", "name": "Clearance 2 (All Red)", "is_clearance": True, "next_idx": 6},
        
        # East Sequence (Indices 5-9)
        {"state": "rrrrrGGGGGrrrrrrrrrr", "name": "Phase 3: EAST Full Green", "dir": "East"},
        {"state": "rrrrryyyyyrrrrrrrrrr", "name": "Yellow 3", "is_yellow": True, "next_idx": 8},
        {"state": "rrrrrrrrrrrrrrrrrrrr", "name": "Clearance 3 (All Red)", "is_clearance": True, "next_idx": 9},
        
        # West Sequence (Indices 15-19)
        {"state": "rrrrrrrrrrrrrrrGGGGG", "name": "Phase 4: WEST Full Green", "dir": "West"},
        {"state": "rrrrrrrrrrrrrrryyyyy", "name": "Yellow 4", "is_yellow": True, "next_idx": 11},
        {"state": "rrrrrrrrrrrrrrrrrrrr", "name": "Clearance 4 (All Red)", "is_clearance": True, "next_idx": 0}
    ]
    
    current_phase_idx = 0
    traci.trafficlight.setRedYellowGreenState(tl_id, phases[0]["state"])
    time_in_phase = 0
    step = 0
    dataset = []
    total_vehicles_processed = set()
    
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        step += 1
        time_in_phase += 1
        
        current_phase = phases[current_phase_idx]
        metrics = {
            "North": {"occ": 0.0, "wait": 0, "emg": False, "halting": 0},
            "South": {"occ": 0.0, "wait": 0, "emg": False, "halting": 0},
            "East": {"occ": 0.0, "wait": 0, "emg": False, "halting": 0},
            "West": {"occ": 0.0, "wait": 0, "emg": False, "halting": 0},
        }
        
        for lane in traci.trafficlight.getControlledLanes(tl_id):
            occupancy_pct = traci.lane.getLastStepOccupancy(lane) * 100.0 
            wait_time = traci.lane.getWaitingTime(lane)
            halting = traci.lane.getLastStepHaltingNumber(lane)
            vehicles = traci.lane.getLastStepVehicleIDs(lane)
            has_emg = any(traci.vehicle.getVehicleClass(v) == "emergency" for v in vehicles)
            
            total_vehicles_processed.update(vehicles)
            
            if "N2C" in lane: dir_key = "North"
            elif "S2C" in lane: dir_key = "South"
            elif "E2C" in lane: dir_key = "East"
            else: dir_key = "West"
                
            metrics[dir_key]["occ"] += occupancy_pct
            metrics[dir_key]["wait"] = max(metrics[dir_key]["wait"], wait_time)
            if has_emg: metrics[dir_key]["emg"] = True
            metrics[dir_key]["halting"] += halting
            
        emergency_lockdown_target = None
        for k, v in metrics.items():
            if v["emg"]:
                emergency_lockdown_target = k
                break
                
        if step % 50 == 0:
            print(f"--- Step {step} | Phase: {current_phase['name']} ---")
            if emergency_lockdown_target:
                print(f"  [!] EMERGENCY LOCKDOWN ACTIVE FOR: {emergency_lockdown_target}")
            else:
                print(f"  North -> Occ: {metrics['North']['occ']:5.1f}%, Stop: {metrics['North']['halting']} | South -> Occ: {metrics['South']['occ']:5.1f}%, Stop: {metrics['South']['halting']}")
                print(f"  East  -> Occ: {metrics['East']['occ']:5.1f}%, Stop: {metrics['East']['halting']} | West  -> Occ: {metrics['West']['occ']:5.1f}%, Stop: {metrics['West']['halting']}")
        
        # YELLOW PHASE LOGIC (Dilemma Zone)
        if current_phase.get("is_yellow", False):
            switch_to_clearance = False
            if time_in_phase >= MIN_YELLOW:
                in_dilemma = check_dilemma_zone()
                if in_dilemma and time_in_phase < MAX_YELLOW:
                    if step % 5 == 0:
                        print("  [!] Safety Override: Extending Yellow Light for fast approaching vehicle!")
                else:
                    switch_to_clearance = True
                    
            if switch_to_clearance:
                current_phase_idx = current_phase["next_idx"]
                traci.trafficlight.setRedYellowGreenState(tl_id, phases[current_phase_idx]["state"])
                time_in_phase = 0
            continue

        # ALL-RED CLEARANCE LOGIC (Prevents junction stranding)
        if current_phase.get("is_clearance", False):
            if time_in_phase >= ALL_RED_TIME:
                
                if strategy == "adaptive":
                    # --- FULLY DYNAMIC PHASE ORDERING ---
                    scores = {}
                    for d_key, d_vals in metrics.items():
                        if emergency_lockdown_target == d_key:
                            scores[d_key] = 999999  # Absolute priority for ambulances
                        elif d_vals["occ"] == 0 and d_vals["halting"] == 0:
                            scores[d_key] = 0
                        else:
                            scores[d_key] = calculate_score(d_vals["occ"], d_vals["wait"])
                            
                    winner_dir = max(scores, key=scores.get)
                    highest_score = scores[winner_dir]
                    
                    if highest_score == 0:
                        continue # If the entire city is empty, sit in All-Red and wait
                        
                    dir_to_idx = {"North": 0, "South": 3, "East": 6, "West": 9}
                    next_idx = dir_to_idx[winner_dir]
                    
                    print(f"  [~] Dynamic Phase Bid Won By: {winner_dir} (Score: {highest_score:.1f})")
                    
                else:
                    next_idx = current_phase["next_idx"]
                    
                current_phase_idx = next_idx
                traci.trafficlight.setRedYellowGreenState(tl_id, phases[current_phase_idx]["state"])
                time_in_phase = 0
            continue
            
        # GREEN EXHAUSTIVE FLUSHING LOGIC
        switch_needed = False
        current_dir = current_phase["dir"]
        
        if strategy == "adaptive":
            if emergency_lockdown_target:
                if emergency_lockdown_target != current_dir and time_in_phase >= 5: 
                    switch_needed = True
            else:
                if time_in_phase >= MIN_GREEN_TIME:
                    scores = {k: calculate_score(v["occ"], v["wait"]) for k, v in metrics.items()}
                    highest_competitor = max([s for k, s in scores.items() if k != current_dir] + [0])
                    
                    if metrics[current_dir]["halting"] <= 2 and highest_competitor > 0:
                        switch_needed = True
                        if step % 5 == 0:
                            print(f"  [+] Queue for {current_dir} flushed (<=2 stragglers)! Switching...")
                            
                    elif time_in_phase >= MAX_GREEN_TIME:
                        if highest_competitor > 0:
                            switch_needed = True
                            print(f"  [!] Max green time reached! Forcing switch.")
        else:
            if time_in_phase >= FIXED_GREEN_TIME:
                switch_needed = True
                
        if switch_needed:
            current_phase_idx = current_phase_idx + 1
            traci.trafficlight.setRedYellowGreenState(tl_id, phases[current_phase_idx]["state"])
            time_in_phase = 0
                
        dataset.append({
            "step": step,
            "strategy": strategy,
            "phase": current_phase['name'],
            "occ_North": metrics["North"]["occ"],
            "occ_South": metrics["South"]["occ"],
            "occ_East": metrics["East"]["occ"],
            "occ_West": metrics["West"]["occ"],
            "emergency": 1 if emergency_lockdown_target else 0
        })
                
    traci.close()
    sys.stdout.flush()
    
    filename = f"dataset_{strategy}.csv"
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=dataset[0].keys())
        writer.writeheader()
        writer.writerows(dataset)
        
    avg_occ = sum(d["occ_North"] + d["occ_South"] + d["occ_East"] + d["occ_West"] for d in dataset) / len(dataset)
    print(f"\nSimulation complete for {strategy} strategy.")
    print(f"-> Dataset saved to '{filename}'")
    print(f"-> Average Asphalt Occupancy: {avg_occ:.2f}%")
    print(f"-> Total Vehicles Processed: {len(total_vehicles_processed)}")

if __name__ == "__main__":
    options = get_options()
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    sumoBinary = "sumo" if options.nogui else "sumo-gui"
    sumoCmd = [sumoBinary, "-c", "intersection.sumocfg", "--random"]
    traci.start(sumoCmd)
    run_control(options.strategy)
