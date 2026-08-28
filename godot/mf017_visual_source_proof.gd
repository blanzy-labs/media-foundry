extends SceneTree

func _arg(name:String,default_value:String="")->String:
	var args:=OS.get_cmdline_user_args()
	for index in range(args.size()-1):
		if args[index]==name:return args[index+1]
	return default_value

func _svg_overlay(time_value:float)->String:
	var pulse:=0.5+0.5*sin(time_value*TAU*1.35)
	var intensity:=0.60+0.30*pulse
	var svg:="<svg xmlns='http://www.w3.org/2000/svg' width='768' height='1152' viewBox='0 0 768 1152'>"
	svg+="<defs><radialGradient id='spill'><stop offset='0' stop-color='#f6cf39' stop-opacity='%.3f'/><stop offset='1' stop-color='#e6b905' stop-opacity='0'/></radialGradient></defs>" % (0.10+0.10*intensity)
	# Local illumination is composited into the source itself.
	svg+="<ellipse cx='518' cy='525' rx='250' ry='330' fill='url(#spill)'/>"
	# Animated Godot-owned reactor hero.
	for filament in range(8):
		var path:=""
		for step in range(18):
			var y:=355.0+step*23.0
			var x:=518.0+sin(time_value*(2.0+filament*.09)+filament*.83+step*.63)*(12.0+32.0*intensity)
			path+=("M" if step==0 else " L")+"%.2f %.2f" % [x,y]
		var color:="#ffe979" if filament%3 else "#e6b905"
		svg+="<path d='%s' fill='none' stroke='%s' stroke-opacity='%.3f' stroke-width='%d' stroke-linecap='round'/>" % [path,color,.62+.25*intensity,2+filament%2]
	# Incandescent lamps are independently timed, not synchronized LEDs.
	for index in range(9):
		var angle:=PI+index*PI/8.0
		var x:=518.0+cos(angle)*150.0;var y:=260.0+sin(angle)*54.0
		if fmod(time_value*3.0+index*.71,2.2)>.42:
			svg+="<circle cx='%.2f' cy='%.2f' r='13' fill='#ef2d0d' fill-opacity='.08'/><circle cx='%.2f' cy='%.2f' r='5' fill='#ef2d0d' fill-opacity='.88'/>" % [x,y,x,y]
	# One restrained deterministic steam source.
	for puff in range(5):
		var life:=fmod(time_value*.24+float(puff)/5.0,1.0)
		var x:=600.0+sin(life*7.0+puff)*8.0;var y:=850.0-life*95.0;var radius:=7.0+life*19.0
		svg+="<circle cx='%.2f' cy='%.2f' r='%.2f' fill='#e0c98b' fill-opacity='%.3f'/>" % [x,y,radius,(1.0-life)*.07]
	# Sparse local particles catch only the reactor light.
	for index in range(14):
		var x:=350.0+fmod(float(index*71+1701957%97),330.0)
		var y:=330.0+fmod(float(index*113)+time_value*(6.0+index%3),590.0)
		svg+="<circle cx='%.2f' cy='%.2f' r='1.2' fill='#f4da97' fill-opacity='.10'/>" % [x,y]
	return svg+"</svg>"

func _initialize()->void:
	var base_path:=_arg("--base")
	var output_dir:=_arg("--output")
	var proof_mode:=_arg("--mode","hybrid")
	if base_path.is_empty() or output_dir.is_empty():
		push_error("MF017 arguments missing");quit(2);return
	var base:=Image.load_from_file(base_path)
	if base.is_empty():
		push_error("MF017 base image failed to load");quit(3);return
	base.resize(768,1152,Image.INTERPOLATE_LANCZOS)
	base.convert(Image.FORMAT_RGBA8)
	DirAccess.make_dir_recursive_absolute(output_dir)
	for frame_index in range(120):
		var overlay:=Image.new()
		var svg_error:int=overlay.load_svg_from_string(_svg_overlay(float(frame_index)/30.0),1.0)
		if svg_error!=OK:
			push_error("MF017 SVG rasterization failed");quit(4);return
		overlay.convert(Image.FORMAT_RGBA8)
		var frame:=base.duplicate()
		frame.blend_rect(overlay,Rect2i(0,0,768,1152),Vector2i.ZERO)
		var write_error:int=frame.save_png(output_dir.path_join("frame-%04d.png" % frame_index))
		if write_error!=OK:
			push_error("MF017 frame write failed");quit(5);return
	print("MF017_VISUAL_SOURCE_PROOF_OK mode="+proof_mode+" frames=120")
	quit(0)
