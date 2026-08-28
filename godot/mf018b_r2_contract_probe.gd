extends SceneTree
func _initialize()->void:
	var packed=load("res://mf018b_r2_pulp_scene.tscn")
	if packed==null:push_error("MF018B-R2 probe scene load failed");quit(2);return
	var scene=packed.instantiate();root.add_child(scene)
	for path in ["Machines/Reactor","Machines/Console/Gauges","Machines/Console/Controls/StartupLever","Machines/Console/FourDotDevice"]:
		if scene.get_node_or_null(NodePath(path))==null:push_error("MF018B-R2 preserved node missing: "+path);quit(3);return
	if scene.get_node_or_null(NodePath("Machines/Reactor/SteamVent"))!=null:push_error("MF018B-R2 removed lever node still exists");quit(4);return
	var events:=[0];scene.startup_progress_changed.connect(func(_v):events[0]+=1);scene.indicator_stage_changed.connect(func(_v):events[0]+=1);scene.linked_ring_activation_changed.connect(func(_v):events[0]+=1)
	scene.set_startup_progress(1.0);scene.set_indicator_stage(.75);scene.set_linked_ring_activation(.5)
	if events[0]!=3:push_error("MF018B-R2 preserved state API failed");quit(5);return
	print("MF018B_R2_PROBE_OK preserved_nodes=4 removed_steam_lever=true signals=3 driver_loaded=false")
	quit(0)
