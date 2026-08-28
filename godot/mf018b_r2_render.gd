extends SceneTree
func _arg(name:String)->String:
	var args:=OS.get_cmdline_user_args()
	for i in range(args.size()-1):
		if args[i]==name:return args[i+1]
	return ""
func _initialize()->void:
	var file:=FileAccess.open(_arg("--config"),FileAccess.READ);var output:=_arg("--output")
	if file==null or output.is_empty():push_error("MF018B-R2 arguments invalid");quit(2);return
	var config=JSON.parse_string(file.get_as_text());var packed=load("res://mf018b_r2_pulp_scene.tscn")
	if packed==null:push_error("MF018B-R2 scene load failed");quit(3);return
	var scene=packed.instantiate();root.add_child(scene);var driver=load("res://mf018b_r1_promo_driver.gd").new();DirAccess.make_dir_recursive_absolute(output)
	var frames:=int(round(float(config.video.duration_seconds)*float(config.video.fps)))
	for index in range(frames):
		var t:=float(index)/float(config.video.fps);driver.apply(scene,t);var image:=Image.new()
		if image.load_svg_from_string(scene.render_svg(t,t/float(config.video.duration_seconds)),1.0)!=OK:push_error("MF018B-R2 rasterization failed");quit(4);return
		image.convert(Image.FORMAT_RGB8)
		if image.save_png(output.path_join("frame-%04d.png" % index))!=OK:push_error("MF018B-R2 write failed");quit(5);return
	print("MF018B_R2_NATIVE_OK frames="+str(frames)+" state="+JSON.stringify(scene.state_snapshot()))
	quit(0)
