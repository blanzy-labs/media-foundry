extends SceneTree

func _arg(name:String,default_value:String="")->String:
	var args:=OS.get_cmdline_user_args()
	for index in range(args.size()-1):
		if args[index]==name:return args[index+1]
	return default_value

func _initialize()->void:
	var config_path:=_arg("--config");var output_dir:=_arg("--output")
	if config_path.is_empty() or output_dir.is_empty():push_error("MF018B arguments missing");quit(2);return
	var file:=FileAccess.open(config_path,FileAccess.READ)
	if file==null:push_error("MF018B config missing");quit(3);return
	var definition=JSON.parse_string(file.get_as_text())
	if typeof(definition)!=TYPE_DICTIONARY:push_error("MF018B config invalid");quit(4);return
	var packed=load("res://mf018b_pulp_scene.tscn")
	if packed==null:push_error("MF018B base scene failed to load");quit(5);return
	var scene=packed.instantiate();root.add_child(scene)
	var driver=load("res://mf018b_promo_driver.gd").new()
	var signal_count:=[0]
	scene.reactor_state_changed.connect(func(_value):signal_count[0]+=1)
	scene.control_activated.connect(func(_id,_value):signal_count[0]+=1)
	scene.audio_event_requested.connect(func(_id):signal_count[0]+=1)
	DirAccess.make_dir_recursive_absolute(output_dir)
	var fps:=int(definition.video.fps);var frames:=int(round(float(definition.video.duration_seconds)*fps))
	for index in range(frames):
		var time_value:=float(index)/fps;driver.apply(scene,time_value)
		var image:=Image.new();var error:=image.load_svg_from_string(scene.render_svg(time_value,time_value/float(definition.video.duration_seconds)),1.0)
		if error!=OK:push_error("MF018B SVG rasterization failed");quit(6);return
		image.convert(Image.FORMAT_RGB8)
		if image.save_png(output_dir.path_join("frame-%04d.png" % index))!=OK:push_error("MF018B frame write failed");quit(7);return
	# Diagnostic is generated from the same base scene, never added to final video.
	driver.apply(scene,8.6)
	var diagnostic:=Image.new();diagnostic.load_svg_from_string(scene.render_svg(8.6,.62,false),1.0);diagnostic.convert(Image.FORMAT_RGB8)
	diagnostic.save_png(output_dir.path_join("interaction-diagnostic.png"))
	print("MF018B_NATIVE_SCENE_OK frames="+str(frames)+" signals="+str(signal_count[0])+" state="+JSON.stringify(scene.state_snapshot()))
	quit(0)
