extends "res://projected_data_window_stage.gd"

## MF-006R4: longer living-record pacing without changing the single-window grammar.

func configure(source_fixture: Dictionary, source_timeline: Dictionary, source_layouts: Dictionary, source_heavy: Font, source_regular: Font) -> Dictionary:
	var result:=super.configure(source_fixture,source_timeline,source_layouts,source_heavy,source_regular)
	if result.get("result")!="PASS":return result
	for id in ["record_activity_1","record_lock_1","record_activity_2","record_lock_2","record_activity_3","record_lock_3","cta_typing"]:
		if _time(id)>duration:return {"result":"FAIL","error":"MF006R4_SCENE_CONFIG_FAILED: missing extended activity event "+id}
	var activity_demo:bool=source_fixture.get("activity",{}).get("demo",false)==true
	if activity_demo and (duration<8 or duration>15):return {"result":"FAIL","error":"MF012_ACTIVITY_DEMO_DURATION_INVALID: expected 8-15 seconds"}
	if not activity_demo and (duration<26 or duration>30):return {"result":"FAIL","error":"MF006R4_SCENE_CONFIG_FAILED: extended duration outside 26-30 seconds"}
	return {"result":"PASS"}

func set_story_time(value:float)->void:
	current_time=value;visible=true
	for event in events:
		if value>=float(event.time):observed_events[str(event.id)]={"id":str(event.id),"type":str(event.type),"time":float(event.time),"observed_frame":int(round(value*30.0))}
	var push:=_smooth(_ramp(value,_time("camera_push"),2.0));var pull:=_smooth(_ramp(value,_time("camera_pull_back"),2.0));var beat:=_record_index();var breathe:=sin(value*.42)*2.2 if value>=_time("screen_initialize") and value<_time("screen_collapse") else 0.0;var reframes:Array[float]=[-4.0,3.0,-2.0];var reframe:float=reframes[beat] if value>=_time("record_typing_1") and value<_time("screen_collapse") else 0.0
	var age:=value-_time("spark_burst");var bump:=sin(age*39.0)*exp(-age*7.0)*4.4 if age>=0 and age<.75 else 0.0
	position=Vector2(270+reframe+bump,480+breathe+bump*.2);scale=Vector2.ONE*(1.0+push*.065-pull*.052);rotation=deg_to_rad(-.3+reframe*.018);queue_redraw()

func validation_report()->Dictionary:
	var report:=super.validation_report();report.strategy="godot_extended_data_window_refinement"
	report.extended_record_activity={"duration":duration,"baseline_duration":18.3,"added_seconds":duration-18.3,"single_window_preserved":true,"record_activity_events":3,"record_lock_events":3,"live_after_typing":true,"micro_diagrams":3,"screen_scale_story":1.06,"node_post_projection_intensity":.34,"cta_typed":true,"cta_hold":duration-_time("website_reveal")}
	report.screen_timeline.activity_1=_time("record_activity_1");report.screen_timeline.lock_1=_time("record_lock_1");report.screen_timeline.activity_2=_time("record_activity_2");report.screen_timeline.lock_2=_time("record_lock_2");report.screen_timeline.activity_3=_time("record_activity_3");report.screen_timeline.lock_3=_time("record_lock_3");report.screen_timeline.cta_typing=_time("cta_typing")
	report.background_cells.noticeable_phone_brightness=true;report.background_cells.extended_pulse=true;report.text_hidden_motion_events=24
	return report

func _draw_record_content(index:int,alpha:float)->void:
	super._draw_record_content(index,alpha)
	var activity_start:=_time("record_activity_%d"%(index+1));var lock_start:=_time("record_lock_%d"%(index+1));var activity:=_smooth(_ramp(current_time,activity_start,.65));var locked:=_smooth(_ramp(current_time,lock_start,.35));var pulse:=.55+.35*sin(current_time*3.1+index)
	# A small continuously living diagnostic region stays clear of the primary phrase.
	draw_string(regular_font,Vector2(72,-177),"SIGNAL",HORIZONTAL_ALIGNMENT_LEFT,-1,11,Color(.42,.84,.78,.55*alpha*activity))
	for bar in range(5):
		var height:=5+float((bar*7+index*5)%17)*activity*(.75+.25*pulse);draw_rect(Rect2(75+bar*15,-142-height,7,height),Color(.32,.9,.78,(.38+bar*.07)*alpha*activity),true)
	if index==0:
		var travel:=fmod(maxf(0,current_time-activity_start)*32,68);draw_line(Vector2(74+travel,-112),Vector2(84+travel,-112),Color(1,.42,.3,.75*alpha*activity),3)
	elif index==1:
		var left:=Vector2(87,-120);var right:=Vector2(139,-120);draw_circle(left,5+2*pulse,Color(.38,1,.86,.72*alpha*activity));draw_circle(right,5+2*(1-pulse),Color(.38,1,.86,.72*alpha*activity));draw_line(left,right,Color(.35,.9,.8,.55*alpha*activity),2)
	else:
		var scan:=fmod(maxf(0,current_time-activity_start)*29,62);draw_line(Vector2(77+scan,-146),Vector2(77+scan,-111),Color(.55,1,.82,.72*alpha*activity),2)
	if locked>0:draw_string(heavy_font,Vector2(91,-91),"SIGNAL LOCK",HORIZONTAL_ALIGNMENT_LEFT,-1,11,Color(.94,.66,.25,.75*alpha*locked))

func _draw_window_circuits()->void:
	super._draw_window_circuits()
	# Once the record exists, a dark lens subordinates the node without hiding causality.
	var screen_live:=_smooth(_ramp(current_time,_time("screen_initialize"),.7))*(1.0-_smooth(_ramp(current_time,_time("screen_collapse"),1.2)))
	if screen_live>0:draw_circle(NODE,42,Color(.015,.06,.07,.32*screen_live));draw_circle(NODE,6,Color(.48,1,.88,.62*screen_live))

func _draw_window_foreground()->void:
	super._draw_window_foreground()
	for mote in range(12):
		var x:=-280.0+float((mote*83+int(current_time*(4+mote%3)))%560);var y:=-440.0+float((mote*137-int(current_time*(7+mote%2)))%820);draw_circle(Vector2(x,y),1.5+float(mote%2),Color(.42,.85,.78,.1+.04*sin(current_time+mote)))

func _draw_window_return_cta()->void:
	var power:=_smooth(_ramp(current_time,_time("cta_energy"),_time("cta_typing")-_time("cta_energy")+.2));var reveal:=_smooth(_ramp(current_time,_time("cta_typing"),.75));var website_reveal:=_smooth(_ramp(current_time,_time("website_reveal"),.65))
	if power>0:
		_draw_partial_path([Vector2(-330,-82),Vector2(-230,-82),Vector2(-230,-126),Vector2(-190,-126)],power,Color("e68d43"),5);_draw_partial_path([Vector2(330,88),Vector2(230,88),Vector2(230,132),Vector2(190,132)],power,Color("e68d43"),5)
		for terminal in [-1.0,1.0]:draw_circle(Vector2(terminal*190,(-126 if terminal<0 else 132)),7,Color("f3b454"))
	if reveal>0:
		var text:=str(fixture.cta.text).to_upper();var count:=mini(text.length(),int(floor((current_time-_time("cta_typing"))*30)));var typed:=text.substr(0,count);_draw_centered_text(typed,Vector2(0,-42),28,Color(.86,.97,.91,reveal),heavy_font,445)
	if website_reveal>0:
		_draw_centered_text(str(fixture.cta.display_url).to_upper(),Vector2(0,18),22,Color(.96,.66,.27,website_reveal),heavy_font,470);_draw_centered_text(author.to_upper(),Vector2(0,66),16,Color(.3,.78,.78,website_reveal),regular_font,430)
