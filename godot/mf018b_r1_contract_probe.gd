extends SceneTree
func _initialize()->void:
	var packed=load("res://mf018b_r1_pulp_scene.tscn")
	if packed==null:push_error("MF018B-R1 probe scene load failed");quit(2);return
	var scene=packed.instantiate();root.add_child(scene)
	var paths:=["Machines/Console/Controls/DialCoolant","Machines/Console/Controls/DialField","Machines/Console/Controls/StartupLever","Machines/Console/FourDotDevice","Machines/Reactor/LinkedRingIndicators"]
	for path in paths:
		if scene.get_node_or_null(NodePath(path))==null:push_error("MF018B-R1 node missing: "+path);quit(3);return
	if scene.get_node_or_null(NodePath("Machines/Console/Controls/SwitchContainment"))!=null:push_error("MF018B-R1 passive switch still present");quit(4);return
	var fired:=[0]
	scene.startup_progress_changed.connect(func(_v):fired[0]+=1);scene.indicator_stage_changed.connect(func(_v):fired[0]+=1);scene.linked_ring_activation_changed.connect(func(_v):fired[0]+=1);scene.startup_initiated.connect(func():fired[0]+=1);scene.yellow_trigger_reached.connect(func():fired[0]+=1)
	scene.set_startup_progress(1.0);scene.set_indicator_stage(.75);scene.set_linked_ring_activation(.5)
	var snapshot=scene.state_snapshot()
	if fired[0]!=5 or snapshot.startup_progress!=1.0 or snapshot.indicator_stage!=.75 or snapshot.linked_ring_activation!=.5:push_error("MF018B-R1 state API failed");quit(5);return
	print("MF018B_R1_PROBE_OK nodes=5 passive_switch=false signals="+str(fired[0])+" driver_loaded=false")
	quit(0)
