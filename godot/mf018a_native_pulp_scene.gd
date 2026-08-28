extends SceneTree

func _arg(name:String,default_value:String="")->String:
	var args:=OS.get_cmdline_user_args()
	for index in range(args.size()-1):
		if args[index]==name:return args[index+1]
	return default_value

func _smooth(value:float)->float:
	value=clampf(value,0.0,1.0)
	return value*value*(3.0-2.0*value)

func _svg_frame(time_value:float,definition:Dictionary)->String:
	var duration:=float(definition.video.duration_seconds)
	var wake:=_smooth((time_value-float(definition.motion.wake_start))/2.4)
	var charge:=_smooth((time_value-float(definition.motion.charge_start))/5.0)
	var peak:=_smooth((time_value-float(definition.motion.peak_start))/1.7)
	var intensity:=0.04+0.24*wake+0.40*charge+0.28*peak
	var pulse:=0.5+0.5*sin(time_value*TAU*float(definition.motion.reactor_pulse_hz))
	var camera_progress:=_smooth(time_value/duration)
	var scale:=1.0+float(definition.motion.camera_push_percent)/100.0*camera_progress
	var svg:="<svg xmlns='http://www.w3.org/2000/svg' width='768' height='1152' viewBox='0 0 768 1152'>"
	svg+="<defs>"
	svg+="<linearGradient id='room' x1='0' y1='0' x2='0' y2='1'><stop stop-color='#061514'/><stop offset='.56' stop-color='#092d2c'/><stop offset='1' stop-color='#07100f'/></linearGradient>"
	svg+="<linearGradient id='metal' x1='0' y1='0' x2='1' y2='.3'><stop stop-color='#071110'/><stop offset='.45' stop-color='#21413a'/><stop offset='.72' stop-color='#6c6235'/><stop offset='1' stop-color='#0b1715'/></linearGradient>"
	svg+="<linearGradient id='console' x1='0' y1='0' x2='.8' y2='1'><stop stop-color='#172c27'/><stop offset='.6' stop-color='#091411'/><stop offset='1' stop-color='#423b23'/></linearGradient>"
	svg+="<radialGradient id='energy'><stop stop-color='#fff3a0' stop-opacity='%.3f'/><stop offset='.34' stop-color='#e6b905' stop-opacity='%.3f'/><stop offset='1' stop-color='#e6b905' stop-opacity='0'/></radialGradient>" % [.60+.32*intensity,.20+.35*intensity]
	svg+="<radialGradient id='halo'><stop stop-color='#ef800c' stop-opacity='%.3f'/><stop offset='1' stop-color='#ef800c' stop-opacity='0'/></radialGradient>" % (.08+.16*intensity)
	svg+="<clipPath id='chamber'><rect x='428' y='334' width='196' height='488' rx='46'/></clipPath>"
	svg+="</defs>"
	# Entire environment shares one restrained native camera transform.
	svg+="<g transform='translate(384 576) scale(%.5f) translate(-384 -576)'>" % scale
	svg+="<rect width='768' height='1152' fill='url(#room)'/>"
	# Background industrial depth uses subordinate vertical masses.
	for index in range(7):
		var x:=18.0+index*112.0
		var width:=44.0+float((index*17)%31)
		var top:=95.0+float((index*83)%140)
		svg+="<rect x='%.1f' y='%.1f' width='%.1f' height='850' rx='18' fill='#061817' stroke='#185755' stroke-opacity='.35' stroke-width='3'/>" % [x,top,width]
		for band in range(5):
			svg+="<rect x='%.1f' y='%.1f' width='%.1f' height='7' fill='#070c0b' opacity='.75'/>" % [x-3.0,top+100.0+band*136.0,width+6.0]
	# Upper-left darkness remains deliberate; one wall pipe anchors the edge.
	svg+="<rect x='38' y='118' width='211' height='300' fill='#061211' opacity='.86'/><path d='M22 470 L22 958' stroke='#050b0a' stroke-width='24'/><path d='M27 470 L27 958' stroke='#185755' stroke-opacity='.45' stroke-width='3'/>"
	# Rear catwalk is horizontal and stops before the reactor silhouette.
	svg+="<path d='M48 478 L314 478' stroke='#6e673b' stroke-opacity='.52' stroke-width='7'/>"
	for index in range(7):svg+="<path d='M%d 478 L%d 438' stroke='#b39d57' stroke-opacity='.38' stroke-width='3'/>" % [62+index*39,62+index*39]
	# Local reactor light changes surrounding native geometry, not a separate plate.
	svg+="<ellipse cx='520' cy='560' rx='280' ry='430' fill='url(#energy)' opacity='%.3f'/>" % (.16+.48*intensity)
	# Native console body with physical gauge housings.
	svg+="<path d='M42 586 L242 558 L250 943 L40 990 Z' fill='url(#console)' stroke='#b59b4e' stroke-width='6'/><path d='M57 606 L228 584 L233 902 L56 937 Z' fill='#10211d' stroke='#185755' stroke-width='3'/>"
	for gauge in range(3):
		var cx:=88.0+gauge*58.0;var cy:=666.0+float(gauge%2)*16.0
		var level:=clampf(intensity*(.78+gauge*.13)+.025*sin(time_value*(5.1+gauge*.7)+gauge),0.0,1.0)
		var angle:=deg_to_rad(215.0+220.0*level)
		var tip_x:=cx+cos(angle)*19.0;var tip_y:=cy+sin(angle)*19.0
		svg+="<circle cx='%.1f' cy='%.1f' r='27' fill='#d0bd82' stroke='#050b0a' stroke-width='5'/><path d='M%.1f %.1f L%.1f %.1f' stroke='#8e170e' stroke-width='4'/><circle cx='%.1f' cy='%.1f' r='4' fill='#07100f'/>" % [cx,cy,cx,cy,tip_x,tip_y,cx,cy]
	# Console lamps are seated in bezels.
	for lamp in range(6):
		var lx:=80.0+float(lamp%3)*60.0;var ly:=802.0+float(lamp/3)*63.0
		var active:=time_value>1.2+lamp*.34 and fmod(time_value*2.4+lamp*.63,2.1)>.24
		svg+="<circle cx='%.1f' cy='%.1f' r='12' fill='#21140b' stroke='#e0c98b' stroke-opacity='.65' stroke-width='2'/>" % [lx,ly]
		if active:
			var lamp_color:="#b12312" if lamp%3!=2 else "#ef800c"
			svg+="<circle cx='%.1f' cy='%.1f' r='22' fill='url(#halo)'/><circle cx='%.1f' cy='%.1f' r='7' fill='%s'/>" % [lx,ly,lx,ly,lamp_color]
	# Reactor shell, collar, chamber and base are one native assembly.
	svg+="<rect x='382' y='270' width='292' height='752' rx='42' fill='url(#metal)' stroke='#9f873d' stroke-width='8'/><ellipse cx='528' cy='286' rx='179' ry='91' fill='#13251f' stroke='#e6b905' stroke-width='11'/><ellipse cx='528' cy='286' rx='139' ry='51' fill='#153a31' stroke='#e0c98b' stroke-width='5'/>"
	# Attached ring lamps: housing first, bulb second.
	for lamp in range(10):
		var angle:=PI+lamp*PI/9.0;var lx:=528.0+cos(angle)*158.0;var ly:=286.0+sin(angle)*68.0
		var active:=time_value>float(definition.motion.warning_start)+lamp*.11 and fmod(time_value*3.2+lamp*.43,2.3)>.18
		svg+="<circle cx='%.1f' cy='%.1f' r='11' fill='#23160d' stroke='#d2b65e' stroke-width='3'/>" % [lx,ly]
		if active:svg+="<circle cx='%.1f' cy='%.1f' r='19' fill='url(#halo)'/><circle cx='%.1f' cy='%.1f' r='6' fill='#c52b16'/>" % [lx,ly,lx,ly]
	svg+="<rect x='422' y='326' width='212' height='506' rx='50' fill='#0c2723' stroke='#ead69a' stroke-width='7'/><rect x='444' y='347' width='168' height='466' rx='40' fill='#071311' stroke='#185755' stroke-width='3'/>"
	# Energy is clipped inside the chamber, binding motion to physical geometry.
	svg+="<g clip-path='url(#chamber)'><ellipse cx='528' cy='575' rx='100' ry='330' fill='url(#energy)' opacity='%.3f'/>" % (.30+.65*intensity)
	for filament in range(9):
		var path:=""
		for step in range(20):
			var y:=362.0+step*22.0
			var x:=528.0+sin(time_value*(2.1+filament*.06)+filament*.71+step*.62)*(10.0+44.0*intensity)
			path+=("M" if step==0 else " L")+"%.2f %.2f" % [x,y]
		var color:="#f4da97" if filament%3 else "#e6b905"
		svg+="<path d='%s' fill='none' stroke='%s' stroke-opacity='%.3f' stroke-width='%d'/>" % [path,color,.35+.58*intensity,2+filament%2]
	svg+="</g>"
	# Heavy native base and vents.
	svg+="<path d='M404 792 L652 792 L682 1008 L372 1008 Z' fill='#091512' stroke='#a18b45' stroke-width='7'/><rect x='471' y='796' width='114' height='226' fill='#07100f' stroke='#e0c98b' stroke-width='5'/>"
	for vent in range(5):svg+="<path d='M478 %d L578 %d' stroke='#8f752b' stroke-width='4'/>" % [824+vent*39,824+vent*39]
	# One native steam valve and restrained local release.
	svg+="<path d='M650 830 L704 830 L704 914' fill='none' stroke='#07100f' stroke-width='22'/><path d='M650 825 L704 825 L704 914' fill='none' stroke='#527467' stroke-opacity='.65' stroke-width='3'/><circle cx='704' cy='916' r='15' fill='#101d18' stroke='#c1a75c' stroke-width='3'/>"
	if time_value>5.0:
		for puff in range(5):
			var life:=fmod((time_value-5.0)*.25+float(puff)/5.0,1.0)
			var sx:=704.0+sin(life*6.0+puff)*8.0;var sy:=904.0-life*110.0
			svg+="<ellipse cx='%.1f' cy='%.1f' rx='%.1f' ry='%.1f' fill='#e0c98b' opacity='%.3f'/>" % [sx,sy,8.0+life*20.0,5.0+life*15.0,(1.0-life)*.08*charge]
	# Floor deck creates depth without becoming a barrier.
	svg+="<path d='M0 1048 L768 1048 L768 1152 L0 1152 Z' fill='#050b0a'/><path d='M0 1051 L768 1051' stroke='#766a37' stroke-width='4'/>"
	for index in range(9):
		var x:=float(index*96)
		svg+="<path d='M384 1048 L%.1f 1152' stroke='#24443b' stroke-opacity='.42' stroke-width='2'/>" % x
	# Deterministic distressed metal and floating depth particles.
	for index in range(96):
		var x:=float((index*83+int(definition.seed)%101)%744+12);var y:=float((index*137+int(definition.seed)%73)%1000+70)
		var length:=float(3+(index*17)%19)
		svg+="<path d='M%.1f %.1f l%.1f %.1f' stroke='%s' stroke-opacity='.12' stroke-width='%d'/>" % [x,y,length,float((index%5)-2),"#e0c98b" if index%4 else "#070c0b",1+index%2]
	for index in range(int(definition.motion.dust_particles)):
		var x:=310.0+fmod(float(index*73+int(definition.seed)%89),400.0)
		var y:=240.0+fmod(float(index*109)+time_value*(4.0+index%3),730.0)
		svg+="<circle cx='%.1f' cy='%.1f' r='1.4' fill='#f4da97' opacity='%.3f'/>" % [x,y,.05+.10*intensity]
	svg+="</g>"
	# Mild frame treatment reinforces pulp identity without hiding the scene.
	svg+="<rect x='10' y='10' width='748' height='1132' fill='none' stroke='#070c0b' stroke-opacity='.72' stroke-width='20'/></svg>"
	return svg

func _initialize()->void:
	var config_path:=_arg("--config")
	var output_dir:=_arg("--output")
	if config_path.is_empty() or output_dir.is_empty():push_error("MF018A arguments missing");quit(2);return
	var config_file:=FileAccess.open(config_path,FileAccess.READ)
	if config_file==null:push_error("MF018A config missing");quit(3);return
	var definition=JSON.parse_string(config_file.get_as_text())
	if typeof(definition)!=TYPE_DICTIONARY:push_error("MF018A config invalid");quit(4);return
	DirAccess.make_dir_recursive_absolute(output_dir)
	var frame_count:=int(round(float(definition.video.duration_seconds)*float(definition.video.fps)))
	for frame_index in range(frame_count):
		var image:=Image.new()
		var svg_error:int=image.load_svg_from_string(_svg_frame(float(frame_index)/float(definition.video.fps),definition),1.0)
		if svg_error!=OK:push_error("MF018A SVG rasterization failed");quit(5);return
		image.convert(Image.FORMAT_RGB8)
		var write_error:int=image.save_png(output_dir.path_join("frame-%04d.png" % frame_index))
		if write_error!=OK:push_error("MF018A frame write failed");quit(6);return
	print("MF018A_NATIVE_SCENE_OK frames="+str(frame_count)+" seed="+str(definition.seed))
	quit(0)
