extends SceneTree
func _initialize()->void:
	var packed=load("res://mf018b_r3_pulp_scene.tscn")
	if packed==null:push_error("MF018B-R3 probe scene load failed");quit(2);return
	var scene=packed.instantiate();root.add_child(scene)
	for path in ["Machines/Reactor","Machines/Console/Gauges","Machines/Console/Controls/StartupLever","Machines/Console/FourDotDevice","Machines/InformationDisplay"]:
		if scene.get_node_or_null(NodePath(path))==null:push_error("MF018B-R3 node missing: "+path);quit(3);return
	var events:=[0];scene.startup_progress_changed.connect(func(_v):events[0]+=1);scene.indicator_stage_changed.connect(func(_v):events[0]+=1);scene.linked_ring_activation_changed.connect(func(_v):events[0]+=1)
	scene.set_startup_progress(1.0);scene.set_indicator_stage(.75);scene.set_linked_ring_activation(.5)
	if events[0]!=3:push_error("MF018B-R3 preserved state API failed");quit(4);return
	var svg:String=scene.render_svg(10.5,0.75)
	if scene.DISPLAY_TITLE!="UNKNOWN PROCESS" or scene.DISPLAY_CTA!="TRY A WEB GAME" or scene.DISPLAY_URL!="rcblanzy.com/books/unknown-process" or "r3_information_display" not in svg:push_error("MF018B-R3 display copy missing");quit(5);return
	if "M398 389 H356" in svg or "M398 384 H356" in svg:push_error("MF018B-R3 L-shaped artifact remains");quit(6);return
	if "r3_complete_control_outline" not in svg:push_error("MF018B-R3 complete outline missing");quit(7);return
	print("MF018B_R3_PROBE_OK preserved_nodes=4 information_display=true copy=3 outline=complete l_artifact=false signals=3 driver_loaded=false")
	quit(0)
