extends SceneTree

func _arg(name:String)->String:
	var args:=OS.get_cmdline_user_args()
	for index in range(args.size()-1):
		if args[index]==name:return args[index+1]
	return ""

func _initialize()->void:
	var manifest_file:=FileAccess.open(_arg("--manifest"),FileAccess.READ)
	if manifest_file==null:push_error("MF018B probe manifest missing");quit(2);return
	var manifest=JSON.parse_string(manifest_file.get_as_text())
	var packed=load("res://mf018b_pulp_scene.tscn")
	if packed==null:push_error("MF018B probe base scene load failed");quit(3);return
	var scene=packed.instantiate();root.add_child(scene)
	var nodes:=0
	for interaction in manifest.interaction_points:
		if scene.get_node_or_null(NodePath(interaction.node))==null:push_error("MF018B unresolved node: "+interaction.node);quit(4);return
		nodes+=1
	var fired:=[0]
	scene.reactor_energy_changed.connect(func(_v):fired[0]+=1)
	scene.temperature_changed.connect(func(_v):fired[0]+=1)
	scene.containment_changed.connect(func(_v):fired[0]+=1)
	scene.field_strength_changed.connect(func(_v):fired[0]+=1)
	scene.pressure_changed.connect(func(_v):fired[0]+=1)
	scene.warning_level_changed.connect(func(_v):fired[0]+=1)
	scene.control_activated.connect(func(_id,_v):fired[0]+=1)
	scene.set_reactor_energy(.71);scene.set_temperature(.62);scene.set_containment(.73)
	scene.set_field_strength(.66);scene.set_pressure(.54);scene.set_warning_level(.61)
	scene.set_control_value("coolant_dial",.74)
	if fired[0]!=7:push_error("MF018B signals did not fire");quit(5);return
	if scene.state_snapshot().reactor_energy!=.71:push_error("MF018B setter did not persist");quit(6);return
	print("MF018B_CONTRACT_PROBE_OK nodes="+str(nodes)+" signals="+str(fired[0])+" driver_loaded=false")
	quit(0)
