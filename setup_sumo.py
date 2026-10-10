import os

def create_sumo_files():
    print("Generating Flared SUMO Network files (Structural Slip Lanes)...")
    
    nodes_xml = """<nodes>
   <node id="C" x="0.0" y="0.0" type="traffic_light"/>
   <node id="N" x="0.0" y="200.0" type="priority"/>
   <node id="E" x="200.0" y="0.0" type="priority"/>
   <node id="S" x="0.0" y="-200.0" type="priority"/>
   <node id="W" x="-200.0" y="0.0" type="priority"/>
</nodes>"""
    with open("cross.nod.xml", "w") as f: f.write(nodes_xml)
    
    edges_xml = """<edges>
   <!-- Incoming roads widened to 3 lanes -->
   <edge id="N2C" from="N" to="C" numLanes="3"/>
   <edge id="E2C" from="E" to="C" numLanes="3"/>
   <edge id="S2C" from="S" to="C" numLanes="3"/>
   <edge id="W2C" from="W" to="C" numLanes="3"/>
   
   <!-- Outgoing roads remain 2 lanes -->
   <edge id="C2N" from="C" to="N" numLanes="2"/>
   <edge id="C2E" from="C" to="E" numLanes="2"/>
   <edge id="C2S" from="C" to="S" numLanes="2"/>
   <edge id="C2W" from="C" to="W" numLanes="2"/>
</edges>"""
    with open("cross.edg.xml", "w") as f: f.write(edges_xml)
    
    # Custom Connections to mimic Indian Heterogeneous Driving
    # Lane 1 (Center): Straight AND Right Turn
    # Lane 2 (Rightmost): Straight AND Right Turn
    con_xml = """<connections>
    <!-- North -->
    <connection from="N2C" to="C2E" fromLane="0" toLane="0"/> <!-- Left -->
    <connection from="N2C" to="C2S" fromLane="1" toLane="0"/> <!-- Straight (Center) -->
    <connection from="N2C" to="C2S" fromLane="2" toLane="1"/> <!-- Straight (Right) -->
    <connection from="N2C" to="C2W" fromLane="1" toLane="0"/> <!-- Right Turn (Center) -->
    <connection from="N2C" to="C2W" fromLane="2" toLane="1"/> <!-- Right Turn (Right) -->
    
    <!-- East -->
    <connection from="E2C" to="C2S" fromLane="0" toLane="0"/>
    <connection from="E2C" to="C2W" fromLane="1" toLane="0"/>
    <connection from="E2C" to="C2W" fromLane="2" toLane="1"/>
    <connection from="E2C" to="C2N" fromLane="1" toLane="0"/>
    <connection from="E2C" to="C2N" fromLane="2" toLane="1"/>
    
    <!-- South -->
    <connection from="S2C" to="C2W" fromLane="0" toLane="0"/>
    <connection from="S2C" to="C2N" fromLane="1" toLane="0"/>
    <connection from="S2C" to="C2N" fromLane="2" toLane="1"/>
    <connection from="S2C" to="C2E" fromLane="1" toLane="0"/>
    <connection from="S2C" to="C2E" fromLane="2" toLane="1"/>
    
    <!-- West -->
    <connection from="W2C" to="C2N" fromLane="0" toLane="0"/>
    <connection from="W2C" to="C2E" fromLane="1" toLane="0"/>
    <connection from="W2C" to="C2E" fromLane="2" toLane="1"/>
    <connection from="W2C" to="C2S" fromLane="1" toLane="0"/>
    <connection from="W2C" to="C2S" fromLane="2" toLane="1"/>
</connections>"""
    with open("cross.con.xml", "w") as f: f.write(con_xml)

    print("Running netconvert to build the Indian Left-Hand Flared Intersection...")
    os.system("netconvert --lefthand --node-files cross.nod.xml --edge-files cross.edg.xml --connection-files cross.con.xml -o intersection.net.xml")
    
    print("Creating Vehicle Routes (intersection.rou.xml)...")
    routes_xml = """<routes>
    <vType id="car" accel="0.8" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="16.67" guiShape="passenger"/>
    <vType id="ambulance" accel="1.5" decel="5.0" sigma="0.5" length="7" minGap="2.5" maxSpeed="25" guiShape="emergency" color="255,0,0" vClass="emergency"/>
    
    <!-- North Incoming -->
    <route id="n_to_s" edges="N2C C2S"/> <!-- Straight -->
    <route id="n_to_e" edges="N2C C2E"/> <!-- Left Turn -->
    <route id="n_to_w" edges="N2C C2W"/> <!-- Right Turn -->
    
    <!-- South Incoming -->
    <route id="s_to_n" edges="S2C C2N"/> <!-- Straight -->
    <route id="s_to_e" edges="S2C C2E"/> <!-- Right Turn -->
    <route id="s_to_w" edges="S2C C2W"/> <!-- Left Turn -->
    
    <!-- East Incoming -->
    <route id="e_to_w" edges="E2C C2W"/> <!-- Straight -->
    <route id="e_to_n" edges="E2C C2N"/> <!-- Right Turn -->
    <route id="e_to_s" edges="E2C C2S"/> <!-- Left Turn -->
    
    <!-- West Incoming -->
    <route id="w_to_e" edges="W2C C2E"/> <!-- Straight -->
    <route id="w_to_n" edges="W2C C2N"/> <!-- Left Turn -->
    <route id="w_to_s" edges="W2C C2S"/> <!-- Right Turn -->
    
    <!-- Heavy Traffic Flows - INCREASED RIGHT TURN PROBABILITY -->
    <flow id="flow_n_s" route="n_to_s" type="car" begin="0" end="1000" probability="0.15"/>
    <flow id="flow_n_e" route="n_to_e" type="car" begin="0" end="1000" probability="0.05"/>
    <flow id="flow_n_w" route="n_to_w" type="car" begin="0" end="1000" probability="0.15"/>
    
    <flow id="flow_s_n" route="s_to_n" type="car" begin="0" end="1000" probability="0.15"/>
    <flow id="flow_s_w" route="s_to_w" type="car" begin="0" end="1000" probability="0.05"/>
    <flow id="flow_s_e" route="s_to_e" type="car" begin="0" end="1000" probability="0.15"/>
    
    <flow id="flow_e_w" route="e_to_w" type="car" begin="0" end="1000" probability="0.20"/>
    <flow id="flow_e_s" route="e_to_s" type="car" begin="0" end="1000" probability="0.05"/>
    <flow id="flow_e_n" route="e_to_n" type="car" begin="0" end="1000" probability="0.20"/>
    
    <flow id="flow_w_e" route="w_to_e" type="car" begin="0" end="1000" probability="0.20"/>
    <flow id="flow_w_n" route="w_to_n" type="car" begin="0" end="1000" probability="0.05"/>
    <flow id="flow_w_s" route="w_to_s" type="car" begin="0" end="1000" probability="0.20"/>
    
    <!-- Ambulances (Increased for more realistic emergency scenarios) -->
    <flow id="emg1" route="n_to_s" type="ambulance" begin="50" end="1000" probability="0.008"/>
    <flow id="emg2" route="e_to_w" type="ambulance" begin="150" end="1000" probability="0.008"/>
</routes>
"""
    with open("intersection.rou.xml", "w") as f: f.write(routes_xml)

    print("Creating SUMO Config (intersection.sumocfg)...")
    sumocfg_xml = """<configuration>
    <input>
        <net-file value="intersection.net.xml"/>
        <route-files value="intersection.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="1000"/>
    </time>
    <gui_only>
        <gui-settings-file value="gui-settings.xml"/>
    </gui_only>
</configuration>
"""
    with open("intersection.sumocfg", "w") as f: f.write(sumocfg_xml)
        
    print("Creating GUI settings (gui-settings.xml) for better visuals...")
    gui_xml = """<viewsettings>
    <scheme name="real world"/>
    <delay value="100"/>
</viewsettings>
"""
    with open("gui-settings.xml", "w") as f: f.write(gui_xml)
        
    print("All files generated successfully!")

if __name__ == "__main__":
    create_sumo_files()
