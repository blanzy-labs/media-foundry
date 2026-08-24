extends "res://extended_data_window_stage.gd"

## MF-006R5: live evidence reconstruction inside the preserved single-window grammar.

func configure(source_fixture:Dictionary,source_timeline:Dictionary,source_layouts:Dictionary,source_heavy:Font,source_regular:Font)->Dictionary:
	var result:=super.configure(source_fixture,source_timeline,source_layouts,source_heavy,source_regular)
	if result.get("result")!="PASS":return result
	for id in ["overload_peak","record_query_1","record_confirm_1","record_query_2","record_confirm_2","record_query_3","record_confirm_3","cta_lock"]:
		if _time(id)>duration:return {"result":"FAIL","error":"MF006R5_SCENE_CONFIG_FAILED: missing investigation event "+id}
	return {"result":"PASS"}

func validation_report()->Dictionary:
	var report:=super.validation_report();report.strategy="godot_live_investigation_refinement"
	var overload_duration:=_time("spark_burst")-_time("overload")
	report.live_investigation={"single_window_preserved":true,"records":3,"animated_investigations":3,"discovery_before_confirmation":true,"query_events":3,"confirm_events":3,"beat_behaviors":["target acquisition","linked-pair discovery","hidden biometric segment reveal"],"same_window_all_records":true,"faux_ui_clutter":false}
	report.node_overload_refinement={"baseline_duration":.3,"duration":overload_duration,"added_emphasis":overload_duration-.3,"peak_event":_time("overload_peak"),"extra_packet_cadence":true,"brighter_node_pulse":true,"tighter_energy_rings":true,"environment_reaction":true}
	report.background_cells.green_phone_visible=true;report.background_cells.green_emphasis=.31;report.background_cells.overload_response=true;report.background_cells.record_initialize_response=true;report.background_cells.cta_response=true
	report.cta.live_investigation_system=true;report.cta.final_resolved_signal=true;report.cta.lock_event=_time("cta_lock");report.cta.typed_reveal=true;report.cta.url_stabilizes=true
	for index in range(3):report.screen_timeline["query_%d"%(index+1)]=_time("record_query_%d"%(index+1));report.screen_timeline["confirm_%d"%(index+1)]=_time("record_confirm_%d"%(index+1))
	report.screen_timeline.overload_peak=_time("overload_peak");report.screen_timeline.cta_lock=_time("cta_lock");report.text_hidden_motion_events=31
	return report

func _record_index()->int:
	var index:=0
	if current_time>=_time("record_query_2"):index=1
	if current_time>=_time("record_query_3"):index=2
	return index

func _draw_window_chamber()->void:
	super._draw_window_chamber()
	var overload:=_smooth(_ramp(current_time,_time("overload"),_time("spark_burst")-_time("overload")))*(1.0-_smooth(_ramp(current_time,_time("spark_burst"),.45)))
	var initialize:=0.0
	for index in range(3):initialize=maxf(initialize,_smooth(_ramp(current_time,_time("record_query_%d"%(index+1)),.22))*(1.0-_smooth(_ramp(current_time,_time("record_query_%d"%(index+1))+.7,.25))))
	for cell in accent_cells:
		if int(accent_cells[cell])!=1:continue
		var row:int=int(cell)/6;var column:int=int(cell)%6;var x:=-320.0+column*108.0+(10.0 if row%2 else 0.0);var y:=-520.0+row*118.0;var central:=column in [2,3] and row in [2,3,4];var boost:=(.055+overload*.11+initialize*.045)*(.48 if central else 1.0)
		draw_rect(Rect2(x+7,y+7,88,98),Color(Color("36a96a"),boost),true)
	if overload>0:
		for ripple in range(3):draw_arc(NODE,66+ripple*38+overload*14,PI*.08,PI*.92,20,Color(.35,1,.72,.12*overload),3)

func _draw_window_circuits()->void:
	super._draw_window_circuits()
	var anticipation:=_smooth(_ramp(current_time,_time("overload"),_time("spark_burst")-_time("overload")))
	if anticipation>0 and current_time<_time("spark_burst"):
		for path_index in range(circuit_paths.size()):
			var path:Array=circuit_paths[path_index]
			for packet in range(4):
				var travel:=fmod((current_time-_time("overload"))*2.15+float(packet)*.24+float(path_index%3)*.07,1.0);var point:=_point_on_path(path,travel);draw_rect(Rect2(point-Vector2(4,4),Vector2(8,8)),Color(.75,1,.9,.55+.35*anticipation),true)
		draw_circle(NODE,18+anticipation*31,Color(.4,1,.86,.2+.34*anticipation));draw_circle(NODE,7+anticipation*12,Color("e5fff4"))
		for ring in range(4):draw_arc(NODE,19+ring*9-anticipation*3,0,TAU,28,Color(.36,1,.86,.25+.4*anticipation),3)

func _draw_record_content(index:int,alpha:float)->void:
	var query_start:=_time("record_query_%d"%(index+1));var typing_start:=_time("record_typing_%d"%(index+1));var activity_start:=_time("record_activity_%d"%(index+1));var confirm_start:=_time("record_confirm_%d"%(index+1));var lock_start:=_time("record_lock_%d"%(index+1));var query_age:=maxf(0,current_time-query_start);var typing_age:=maxf(0,current_time-typing_start);var query:=_smooth(_ramp(current_time,query_start,.42));var activity:=_smooth(_ramp(current_time,activity_start,.55));var confirmed:=_smooth(_ramp(current_time,confirm_start,.28));var locked:=_smooth(_ramp(current_time,lock_start,.3));var phrase:=str(page_phrases[index]).to_upper();var count:=mini(phrase.length(),int(floor(typing_age*27.0)));var typed:=phrase.substr(0,count);var cursor:="_" if fmod(typing_age,.62)<.34 and count<phrase.length() else "";var pulse:=.55+.35*sin(current_time*3.1+index)
	draw_string(regular_font,Vector2(-158,-177),"INVESTIGATION %02d / 03 // LIVE TRACE"%(index+1),HORIZONTAL_ALIGNMENT_LEFT,-1,13,Color(.48,.9,.8,.78*alpha))
	# Fragments and a scan precede confirmation, so conclusions feel discovered rather than displayed.
	for fragment in range(7):
		var width:=18+((fragment*19+index*11)%43);var resolved:=clampf(query*1.3-fragment*.09,0,1);draw_rect(Rect2(-156+fragment%3*70,-146+int(fragment/3)*16,width*resolved,3),Color(.3,.86,.75,.18*alpha*(1.0-confirmed)),true)
	var scan_x:=-155+fmod(query_age*77,238);draw_line(Vector2(scan_x,-151),Vector2(scan_x,-105),Color(.55,1,.84,.6*alpha*query*(1.0-confirmed*.5)),2)
	if index==0:
		var acquire:=clampf((current_time-activity_start)/1.05,0,1);var target:=Vector2(-131+acquire*63,-127+sin(acquire*PI)*8);var size:=10+confirmed*4;draw_line(Vector2(-155,-120),target,Color(1,.36,.26,.45*alpha*activity),2);for corner in [Vector2(-1,-1),Vector2(1,-1),Vector2(1,1),Vector2(-1,1)]:draw_line(target+corner*size,target+corner*size-Vector2(corner.x*6,0),Color(1,.43,.3,.8*alpha*activity),2)
		draw_string(regular_font,Vector2(-151,-92),"SUBJECT TRACE // ACQUIRING",HORIZONTAL_ALIGNMENT_LEFT,-1,11,Color(1,.48,.34,.72*alpha*activity))
	elif index==1:
		var first:=_smooth(_ramp(current_time,activity_start,.28));var second:=_smooth(_ramp(current_time,activity_start+.38,.28));var link:=_smooth(_ramp(current_time,activity_start+.72,.5));var left:=Vector2(-130,-125);var right:=Vector2(-70,-125);draw_circle(left,7,Color(.42,1,.88,.82*alpha*first));draw_circle(right,7,Color(.58,.72,1,.82*alpha*second));draw_line(left,right,Color(.38,.95,.82,.65*alpha*link),3);draw_circle(left.lerp(right,.5+.25*sin(current_time*4)),3,Color(.86,1,.92,.8*alpha*link));draw_string(regular_font,Vector2(-145,-143),"LEO",HORIZONTAL_ALIGNMENT_LEFT,-1,11,Color(.72,1,.92,alpha*first));draw_string(regular_font,Vector2(-86,-143),"ZEPH",HORIZONTAL_ALIGNMENT_LEFT,-1,11,Color(.75,.82,1,alpha*second))
	else:
		var reveal:=clampf((current_time-activity_start)/1.15,0,1);for bar in range(8):var visible:=clampf(reveal*1.7-bar*.09,0,1);var hidden:=bar in [4,5];draw_line(Vector2(-155+bar*12,-145),Vector2(-155+bar*12,-124+(bar%3)*4),Color((.98 if hidden else .38),(.58 if hidden else .92),(.28 if hidden else .76),(.75 if hidden else .5)*alpha*visible),3)
		draw_string(regular_font,Vector2(-151,-101),"HIDDEN SEGMENT // RESOLVING",HORIZONTAL_ALIGNMENT_LEFT,-1,11,Color(.96,.65,.3,.74*alpha*activity))
	draw_string(heavy_font,Vector2(-158,-63),typed+cursor,HORIZONTAL_ALIGNMENT_LEFT,-1,21,Color(.88,1,.95,alpha));draw_string(regular_font,Vector2(-158,-30),("RESULT CONFIRMED" if confirmed>.6 else "QUERY // RECONSTRUCTING"),HORIZONTAL_ALIGNMENT_LEFT,-1,12,Color(.45,.84,.76,.72*alpha))
	for bar in range(5):var height:=5+float((bar*7+index*5)%17)*activity*(.75+.25*pulse);draw_rect(Rect2(92+bar*15,-109-height,7,height),Color(.32,.9,.78,(.3+bar*.08)*alpha*query),true)
	if locked>0:draw_string(heavy_font,Vector2(91,-91),"EVIDENCE LOCK",HORIZONTAL_ALIGNMENT_LEFT,-1,10,Color(.94,.66,.25,.78*alpha*locked))

func _draw_window_return_cta()->void:
	var power:=_smooth(_ramp(current_time,_time("cta_energy"),_time("cta_typing")-_time("cta_energy")+.2));var typing:=_smooth(_ramp(current_time,_time("cta_typing"),.75));var locked:=_smooth(_ramp(current_time,_time("cta_lock"),.3));var website:=_smooth(_ramp(current_time,_time("website_reveal"),.55))
	if power>0:
		_draw_partial_path([Vector2(-330,-82),Vector2(-230,-82),Vector2(-230,-126),Vector2(-190,-126)],power,Color("e68d43"),5);_draw_partial_path([Vector2(330,88),Vector2(230,88),Vector2(230,132),Vector2(190,132)],power,Color("e68d43"),5);for terminal in [-1.0,1.0]:draw_circle(Vector2(terminal*190,(-126 if terminal<0 else 132)),7,Color("f3b454"))
	if typing>0:
		_draw_centered_text("FINAL TRANSMISSION // RESOLVING",Vector2(0,-86),13,Color(.4,.83,.78,.65*typing),regular_font,430);var text:=str(fixture.cta.text).to_upper();var count:=mini(text.length(),int(floor((current_time-_time("cta_typing"))*28)));_draw_centered_text(text.substr(0,count),Vector2(0,-42),28,Color(.86,.97,.91,typing),heavy_font,445)
	if locked>0:_draw_centered_text("SIGNAL LOCK",Vector2(0,-11),11,Color(.4,.9,.78,.7*locked),regular_font,250)
	if website>0:_draw_centered_text(str(fixture.cta.display_url).to_upper(),Vector2(0,27),22,Color(.96,.66,.27,website),heavy_font,470);_draw_centered_text(author.to_upper(),Vector2(0,70),16,Color(.3,.78,.78,website),regular_font,430)
