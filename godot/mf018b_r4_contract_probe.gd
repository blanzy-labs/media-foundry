extends SceneTree
func _initialize()->void:
	var packed=load("res://mf018b_r4_pulp_scene.tscn")
	if packed==null:push_error("MF018B-R4 probe scene load failed");quit(2);return
	var scene=packed.instantiate();root.add_child(scene)
	for path in ["Machines/Reactor","Machines/Console/Gauges","Machines/Console/Controls/StartupLever","Machines/Console/FourDotDevice","Machines/InformationDisplay"]:
		if scene.get_node_or_null(NodePath(path))==null:push_error("MF018B-R4 node missing: "+path);quit(3);return
	var events:=[0];scene.startup_progress_changed.connect(func(_v):events[0]+=1);scene.indicator_stage_changed.connect(func(_v):events[0]+=1);scene.linked_ring_activation_changed.connect(func(_v):events[0]+=1)
	scene.set_startup_progress(1.0);scene.set_indicator_stage(.75);scene.set_linked_ring_activation(.5)
	if events[0]!=3:push_error("MF018B-R4 preserved state API failed");quit(4);return
	var svg:String=scene.render_svg(10.5,0.75)
	if "r4_panel_face_fill" not in svg or "M51 613 L228 575 L245 625 L235 927 L52 964 Z' fill='#0a1a17' stroke='#40756a'" in svg:push_error("MF018B-R4 legacy perimeter remains");quit(5);return
	if svg.count("r3_complete_control_outline")!=1:push_error("MF018B-R4 clean perimeter invalid");quit(6);return
	if scene.DISPLAY_TITLE!="UNKNOWN PROCESS" or scene.DISPLAY_CTA!="TRY A WEB GAME" or scene.DISPLAY_URL!="rcblanzy.com/books/unknown-process":push_error("MF018B-R4 display regression");quit(7);return
	print("MF018B_R4_PROBE_OK preserved_nodes=5 legacy_outline=false clean_perimeter=1 display_copy=3 signals=3 driver_loaded=false")
	quit(0)
