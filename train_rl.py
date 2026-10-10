import os
import sys
import gymnasium as gym
import numpy as np
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
import traci

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)

class SumoTrafficEnv(gym.Env):
    """
    Advanced RL Environment with Anti-Starvation Reward Function
    """
    def __init__(self, render_mode=None):
        super(SumoTrafficEnv, self).__init__()
        self.render_mode = render_mode
        self.tl_id = "C"
        
        # Action space: 4 possible green phases
        self.action_space = spaces.Discrete(4)
        
        # Observation space: 8 values (4 queues + 4 max wait times)
        self.observation_space = spaces.Box(low=0, high=1000, shape=(8,), dtype=np.float32)
        
        self.phases = [
            {"state": "GGGrrgrrrrGGGrrgrrrr", "name": "N/S Straight"},
            {"state": "rrrGGgrrrrrrrGGgrrrr", "name": "N/S Right Turn"},
            {"state": "grrrrGGGrrgrrrrGGGrr", "name": "E/W Straight"},
            {"state": "grrrrrrrGGgrrrrrrrGG", "name": "E/W Right Turn"}
        ]
        
        self.yellow_states = [
            "yyyrrgrrrryyyrrgrrrr",
            "rrryygrrrrrrryygrrrr",
            "grrrryyyrrgrrrryyyrr",
            "grrrrrrryygrrrrrrryy"
        ]
        
        self.current_phase = 0
        self.step_length = 10  # Seconds to hold a phase

    def _get_obs(self):
        queues = [0, 0, 0, 0] # NS_S, NS_R, EW_S, EW_R
        waits = [0, 0, 0, 0]
        
        for lane in traci.trafficlight.getControlledLanes(self.tl_id):
            q_len = traci.lane.getLastStepHaltingNumber(lane)
            w_time = traci.lane.getWaitingTime(lane)
            if "N2C" in lane or "S2C" in lane:
                idx = 1 if lane.endswith("_2") else 0
            else:
                idx = 3 if lane.endswith("_2") else 2
            queues[idx] += q_len
            waits[idx] = max(waits[idx], w_time)
            
        return np.array(queues + waits, dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        sumo_binary = "sumo-gui" if self.render_mode == "human" else "sumo"
        sumo_cmd = [sumo_binary, "-c", "intersection.sumocfg", "--random", "--no-warnings"]
        
        try: traci.close()
        except: pass
            
        traci.start(sumo_cmd)
        self.current_phase = 0
        traci.trafficlight.setRedYellowGreenState(self.tl_id, self.phases[self.current_phase]["state"])
        return self._get_obs(), {}

    def step(self, action):
        if action != self.current_phase:
            # Transition Phase (Yellow)
            traci.trafficlight.setRedYellowGreenState(self.tl_id, self.yellow_states[self.current_phase])
            for _ in range(4): 
                if traci.simulation.getMinExpectedNumber() > 0:
                    traci.simulationStep()
            self.current_phase = action
            
        # Apply Green Phase
        traci.trafficlight.setRedYellowGreenState(self.tl_id, self.phases[self.current_phase]["state"])
        for _ in range(self.step_length):
            if traci.simulation.getMinExpectedNumber() > 0:
                traci.simulationStep()
                
        obs = self._get_obs()
        queues = obs[0:4]
        waits = obs[4:8]
        
        # ADVANCED REWARD FUNCTION: Exponential penalty for wait time to prevent starvation
        total_queue = np.sum(queues)
        max_wait_penalty = np.sum((waits / 10.0) ** 2)
        
        reward = -(total_queue * 2.5) - max_wait_penalty
        
        terminated = traci.simulation.getMinExpectedNumber() == 0
        return obs, float(reward), terminated, False, {}

    def close(self):
        try: traci.close()
        except: pass

if __name__ == "__main__":
    print("Initializing Advanced SUMO Gym Environment...")
    env = SumoTrafficEnv(render_mode=None)
    check_env(env)
    
    print("Building PPO Model...")
    model = PPO("MlpPolicy", env, verbose=1)
    
    print("Beginning Deep Training! (Training for 150,000 timesteps...)")
    try:
        model.learn(total_timesteps=1000000)
        print("Training Complete! Saving model...")
        model.save("ppo_traffic_model_1M")
    except KeyboardInterrupt:
        print("Saved current progress...")
        model.save("ppo_traffic_model_1M")
    finally:
        env.close()
