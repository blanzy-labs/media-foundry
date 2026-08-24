extends "res://causal_book_stage.gd"

## MF-006R3: one persistent recovered-record screen, powered by a subordinate node.

const NODE := Vector2(0, 125)
const CONTENT_RECT := Rect2(-171,-260,338,239)
const ACCENT_COLORS: Array[Color] = [Color("7746b4"),Color("328b5d"),Color("3478bd"),Color("238594")]
var accent_cells: Dictionary = {}
var screen_points := PackedVector2Array([Vector2(-198,-306),Vector2(202,-294),Vector2(194,32),Vector2(-206,20)])

func configure(source_fixture: Dictionary, source_timeline: Dictionary, source_layouts: Dictionary, source_heavy: Font, source_regular: Font) -> Dictionary:
	var result := super.configure(source_fixture, source_timeline, source_layouts, source_heavy, source_regular)
	if result.get("result") != "PASS": return result
	for path in circuit_paths: path[path.size()-1] = NODE
	var required := ["screen_initialize","record_typing_1","screen_refresh_1","record_typing_2","screen_refresh_2","record_typing_3","screen_collapse","energy_reclaimed"]
	for id in required:
		if _time(id) > duration: return {"result":"FAIL","error":"MF006R3_SCENE_CONFIG_FAILED: missing screen event " + id}
	var rng := RandomNumberGenerator.new(); rng.seed = int(fixture.seed)
	while accent_cells.size() < 12:
		var cell := rng.randi_range(0,53)
		if not accent_cells.has(cell): accent_cells[cell] = accent_cells.size() % 4
	return {"result":"PASS"}

func set_story_time(value: float) -> void:
	current_time=value; visible=true
	for event in events:
		if value>=float(event.time): observed_events[str(event.id)]={"id":str(event.id),"type":str(event.type),"time":float(event.time),"observed_frame":int(round(value*30.0))}
	var push:=_smooth(_ramp(value,_time("camera_push"),1.25)); var pull:=_smooth(_ramp(value,_time("camera_pull_back"),1.35)); var beat:=_record_index(); var offset:=sin(float(beat)*1.4)*6.0 if value>=_time("screen_initialize") and value<_time("screen_collapse") else 0.0
	var age:=value-_time("spark_burst"); var bump:=sin(age*43.0)*exp(-age*7.5)*4.2 if age>=0 and age<.7 else 0.0
	position=Vector2(270+offset+bump,480+bump*.2); scale=Vector2.ONE*(1.0+push*.055-pull*.045); rotation=deg_to_rad(-.35+offset*.018); queue_redraw()

func validation_report() -> Dictionary:
	var report:=super.validation_report(); report.strategy="godot_projected_data_window_refinement"; report.generated_book=null
	report.projected_codex=null
	report.projected_data_window={"id":"recovered-record-window","primary_window_count":1,"persistent_instance":true,"same_instance_all_beats":true,"single_coherent_boundary":true,"split_page_projection":false,"book_metaphor":false,"origin":"central-node/emitter-region","screen_behavior":true,"scanlines":true,"typed_text":true,"left_aligned_story_text":true,"wavy_center_line":false,"yellow_circular_graphic":false,"large_diagnostic_graphic":false,"content_first":true,"collapse_to_node":true}
	report.projection_layout={"window_bounds":{"x":72,"y":174,"width":416,"height":350},"content_bounds":{"x":99,"y":220,"width":338,"height":239},"story_text_bounds":[{"x":111,"y":295,"width":270,"height":54},{"x":111,"y":295,"width":270,"height":54},{"x":111,"y":295,"width":304,"height":54}],"all_story_text_inside_content":true,"circuit_intensity_behind_window":"suppressed","node_outside_content":true}
	report.projection_emitter={"id":"emitter","purpose":"node-coupled recovered-record projection source","connected_to_circuits":true,"projection_origin":NODE,"subordinate_to_window":true,"legacy_cradle_removed":true}
	report.background_cells={"total":54,"dark_majority":42,"accent_count":12,"accent_ratio":12.0/54.0,"counts":{"purple":3,"green":3,"blue":3,"cyan":3},"palette":["dark","current","purple","green","blue","cyan"],"seeded_irregular_placement":true,"noticeable_phone_brightness":true,"central_reading_area_dimmed":true,"event_reactive":true,"within_defined_limits":true}
	report.depth_system={"layer_count":4,"foreground_side_cables":true,"center_foreground_cable":false,"wall_parallax":true,"particles":true,"light_falloff":true,"screen_perspective":"mild"}
	report.screen_timeline={"initialize":_time("screen_initialize"),"typing_1":_time("record_typing_1"),"refresh_1":_time("screen_refresh_1"),"typing_2":_time("record_typing_2"),"refresh_2":_time("screen_refresh_2"),"typing_3":_time("record_typing_3"),"collapse":_time("screen_collapse"),"reclaimed":_time("energy_reclaimed"),"cta_energy":_time("cta_energy")}
	report.text_hidden_motion_events=18
	return report

func _draw() -> void:
	if heavy_font==null or regular_font==null:return
	_draw_window_chamber(); _draw_window_circuits(); _draw_data_emitter(); _draw_node_burst(); _draw_data_window(); _draw_window_collapse(); _draw_window_return_cta(); _draw_window_foreground()

func _draw_window_chamber() -> void:
	_draw_chamber()
	var overload:=_smooth(_ramp(current_time,_time("central_node_charge"),_time("spark_burst")-_time("central_node_charge")))
	var cta:=_smooth(_ramp(current_time,_time("cta_energy"),.6))
	for index in accent_cells:
		var row:int=int(index)/6; var column:int=int(index)%6; var x:=-320.0+column*108.0+(10.0 if row%2 else 0.0); var y:=-520.0+row*118.0
		var central:=column in [2,3] and row in [2,3,4]; var extended:=str(fixture.get("visual_strategy",{}).get("preference","")) in ["godot_extended_data_window_refinement","godot_live_investigation_refinement","godot_final_polish_refinement","godot_lower_right_polish_refinement"]; var pulse:=(.21 if extended else .18)+.045*sin(current_time*(.38+float(int(index)%3)*.07)+int(index)*1.7)+overload*.055+cta*.025
		if central: pulse*=.48
		var color:Color=ACCENT_COLORS[int(accent_cells[index])]
		draw_rect(Rect2(x+5,y+5,92,102),Color(color,pulse),true); draw_rect(Rect2(x+8,y+8,86,96),Color(color,pulse*.35),false,3)
	for ring in range(5,0,-1): draw_circle(NODE-Vector2(0,100),70+ring*55,Color(.03,.21,.23,.012*float(6-ring)))

func _draw_window_circuits() -> void:
	var draw_progress:=_smooth(_ramp(current_time,_time("path_draw_start"),_time("paths_drawn")-_time("path_draw_start"))); var flow:=_ramp(current_time,_time("energy_flow"),_time("spark_burst")-_time("energy_flow")); var return_progress:=_ramp(current_time,_time("return_energy"),2.0)
	var screen_live:=_smooth(_ramp(current_time,_time("screen_initialize"),.5))*(1.0-_smooth(_ramp(current_time,_time("screen_collapse"),1.2)))
	for index in range(circuit_paths.size()):
		var path:Array=circuit_paths[index]; _draw_partial_path(path,draw_progress,Color(.12,.62,.67,.78*(1.0-screen_live*.42)),4)
		if flow>0 and current_time<_time("spark_burst")+.12:
			for packet in range(3):
				var travel:=clampf(flow*1.28-float(index%3)*.08-float(packet)*.22,0,1); var point:=_point_on_path(path,travel); draw_rect(Rect2(point-Vector2(5,5),Vector2(10,10)),Color("a9fff1"),true)
		if return_progress>0:
			for packet in range(2):
				var travel:=clampf(return_progress-float(index%2)*.09-float(packet)*.28,0,1); var point:=_point_on_path(path,1.0-travel); draw_rect(Rect2(point-Vector2(4,4),Vector2(8,8)),Color("f09a45"),true)
	var charge:=_smooth(_ramp(current_time,_time("central_node_charge"),_time("spark_burst")-_time("central_node_charge")))
	if current_time>=_time("spark_burst"):charge*=1.0-_ramp(current_time,_time("spark_burst"),.45)
	draw_circle(NODE,11+charge*24,Color(.25,.95,.88,.22+charge*.35)); draw_circle(NODE,6+charge*9,Color("c8fff0"))
	for ring in range(3):draw_arc(NODE,23+ring*11+charge*7,0,TAU,24,Color(.18,.82,.78,.25+charge*.42),3)

func _draw_data_emitter() -> void:
	var live:=_smooth(_ramp(current_time,_time("central_node_charge"),.55)); draw_line(Vector2(-112,245),Vector2(112,245),Color("17272c"),15); draw_line(Vector2(-112,245),Vector2(112,245),Color(.25,.82,.78,.45+live*.3),3)
	draw_colored_polygon(PackedVector2Array([Vector2(-68,245),Vector2(-38,207),Vector2(38,207),Vector2(68,245)]),Color("102127")); draw_polyline(PackedVector2Array([Vector2(-68,245),Vector2(-38,207),Vector2(38,207),Vector2(68,245)]),Color(.28,.86,.8,.62),4)
	for contact in [-54.0,-18.0,18.0,54.0]:draw_circle(Vector2(contact,243),4,Color("ed9c48"))
	draw_line(Vector2(0,207),NODE,Color(.22,.82,.78,.32),3)

func _draw_node_burst() -> void:
	var age:=current_time-_time("spark_burst")
	if age<0 or age>1.0:return
	var fade:=1.0-age; draw_circle(NODE,105*(1.0-fade)+14,Color(.38,.95,.9,.15*fade))
	for spark in range(18):
		var angle:=float((spark*97+int(fixture.seed))%360)*PI/180.0; var distance:=(25+float((spark*23)%100))*(1.0-fade); var direction:=Vector2(cos(angle),sin(angle)); draw_line(NODE+direction*distance,NODE+direction*(distance+10+spark%8),Color(.7,1,.88,fade),3)

func _draw_data_window() -> void:
	var initialize:=_smooth(_ramp(current_time,_time("screen_initialize"),.55)); var collapse:=_smooth(_ramp(current_time,_time("screen_collapse"),_time("energy_reclaimed")-_time("screen_collapse"))); var alpha:=initialize*(1.0-collapse)
	if alpha<=.01:return
	var extended:=str(fixture.get("visual_strategy",{}).get("preference","")) in ["godot_extended_data_window_refinement","godot_live_investigation_refinement","godot_final_polish_refinement","godot_lower_right_polish_refinement"];var story_live:=extended and current_time>=_time("record_typing_1") and current_time<_time("screen_collapse");var hover:=sin(current_time*1.55)*3.0;draw_set_transform(Vector2(0,hover+(-8 if story_live else 0)),deg_to_rad(-.45),Vector2.ONE*(1.06 if story_live else 1.0))
	# The dark backing suppresses circuit/color pollution while retaining low-fi translucency.
	draw_colored_polygon(screen_points,Color(.018,.095,.11,.84*alpha)); draw_polyline(PackedVector2Array([screen_points[0],screen_points[1],screen_points[2],screen_points[3],screen_points[0]]),Color(.34,1,.9,.82*alpha),5)
	for corner in [Vector2(-190,-296),Vector2(193,-284),Vector2(185,22),Vector2(-197,10)]: draw_rect(Rect2(corner-Vector2(5,5),Vector2(10,10)),Color(.94,.62,.25,.85*alpha),true)
	for line in range(8):
		var y:=-269+line*34; var shimmer:=.045+.035*maxf(0,sin(current_time*4+line)); draw_line(Vector2(-176,y),Vector2(172,y+10),Color(.23,.82,.78,shimmer*alpha),2)
	var header:="RECOVERED RECORD // UNKNOWN PROCESS"; draw_string(regular_font,Vector2(-166,-239),header,HORIZONTAL_ALIGNMENT_LEFT,-1,14,Color(.47,.9,.84,.78*alpha)); draw_line(Vector2(-166,-221),Vector2(162,-211),Color(.34,.92,.85,.35*alpha),2)
	if current_time<_time("record_typing_1"):
		draw_string(heavy_font,Vector2(-157,-102),title.to_upper(),HORIZONTAL_ALIGNMENT_LEFT,-1,29,Color(.83,1,.94,alpha)); draw_string(regular_font,Vector2(-157,-65),author.to_upper(),HORIZONTAL_ALIGNMENT_LEFT,-1,16,Color(.95,.64,.28,alpha))
	else:_draw_record_content(_record_index(),alpha)
	draw_set_transform(Vector2.ZERO,0,Vector2.ONE)

func _draw_record_content(index:int,alpha:float) -> void:
	var start:=_time("record_typing_%d"%(index+1)); var age:=maxf(0,current_time-start); var phrase:=str(page_phrases[index]).to_upper(); var count:=mini(phrase.length(),int(floor(age*34.0))); var typed:=phrase.substr(0,count); var cursor:="_" if fmod(age,0.62)<.34 and count<phrase.length() else ""
	var refresh_age:=current_time-_time("screen_refresh_%d"%(index+1)) if index<2 else -1.0; var interference:=1.0-clampf(1.0-abs(refresh_age-.12)/.12,0,1) if refresh_age>=0 and refresh_age<.24 else 0.0
	draw_string(regular_font,Vector2(-158,-177),"RECORD %02d / 03"%(index+1),HORIZONTAL_ALIGNMENT_LEFT,-1,14,Color(.48,.85,.8,.75*alpha))
	if index==0:
		draw_rect(Rect2(-156,-143,8,8),Color("e0664a"),true); draw_string(regular_font,Vector2(-137,-134),"ALERT / SUBJECT TRACKED",HORIZONTAL_ALIGNMENT_LEFT,-1,13,Color(1,.46,.34,.85*alpha))
		draw_line(Vector2(-155,-111),Vector2(-98,-109),Color(1,.39,.28,.65*alpha),3)
	elif index==1:
		for x in [-132.0,-72.0]:draw_circle(Vector2(x,-125),7,Color(.42,1,.88,.85*alpha))
		draw_line(Vector2(-125,-125),Vector2(-79,-125),Color(.4,.92,.84,.7*alpha),3); draw_string(regular_font,Vector2(-147,-145),"LEO",HORIZONTAL_ALIGNMENT_LEFT,-1,11,Color(.72,1,.92,alpha)); draw_string(regular_font,Vector2(-87,-145),"ZEPH",HORIZONTAL_ALIGNMENT_LEFT,-1,11,Color(.72,1,.92,alpha))
	else:
		# Minimal non-circular biometric identifier; the rejected yellow rings are absent.
		for bar in range(6):draw_line(Vector2(-155+bar*12,-145),Vector2(-155+bar*12,-124+(bar%3)*4),Color(.38,.92,.76,.55*alpha),3)
		draw_line(Vector2(-159+fmod(age*48,76),-151),Vector2(-159+fmod(age*48,76),-117),Color(.7,1,.87,.75*alpha),2)
	draw_string(heavy_font,Vector2(-158,-63),typed+cursor,HORIZONTAL_ALIGNMENT_LEFT,-1,21,Color(.88,1,.95,alpha))
	draw_string(regular_font,Vector2(-158,-30),"STATUS // RECORD RECONSTRUCTED",HORIZONTAL_ALIGNMENT_LEFT,-1,12,Color(.42,.78,.75,.72*alpha))
	if interference>0:
		for line in range(5):
			var y:=-190+line*42; draw_rect(Rect2(-170,y,340*interference,3+line%2),Color(.55,1,.9,.24*alpha),true)

func _draw_window_collapse() -> void:
	var collapse:=_smooth(_ramp(current_time,_time("screen_collapse"),_time("energy_reclaimed")-_time("screen_collapse")))
	if collapse<=0 or collapse>=1:return
	for fragment in range(56):
		var origin:=Vector2(float((fragment*71)%380-190),float((fragment*43)%310-285)); var point:=origin.lerp(NODE,collapse*collapse); draw_rect(Rect2(point,Vector2(3+fragment%5,3+fragment%3)),Color(.3,.98,.87,1.0-collapse*.2),true)
	draw_circle(NODE,9+collapse*20,Color(.4,1,.87,.15+collapse*.3))

func _draw_window_return_cta() -> void:
	var power:=_smooth(_ramp(current_time,_time("cta_energy"),_time("website_reveal")-_time("cta_energy")+.2)); var reveal:=_smooth(_ramp(current_time,_time("website_reveal"),.55))
	if power>0:
		_draw_partial_path([Vector2(-330,-82),Vector2(-230,-82),Vector2(-230,-126),Vector2(-190,-126)],power,Color("e68d43"),5); _draw_partial_path([Vector2(330,88),Vector2(230,88),Vector2(230,132),Vector2(190,132)],power,Color("e68d43"),5)
		for terminal in [-1.0,1.0]:draw_circle(Vector2(terminal*190,(-126 if terminal<0 else 132)),7,Color("f3b454"))
	if reveal>0:
		var flicker:=clampf(reveal+sin(current_time*31)*.045,0,1); _draw_centered_text(str(fixture.cta.text).to_upper(),Vector2(0,-42),28,Color(.86,.97,.91,flicker),heavy_font,445); _draw_centered_text(str(fixture.cta.display_url).to_upper(),Vector2(0,18),22,Color(.96,.66,.27,flicker),heavy_font,470); _draw_centered_text(author.to_upper(),Vector2(0,66),16,Color(.3,.78,.78,reveal),regular_font,430)

func _draw_window_foreground() -> void:
	_draw_foreground()
	# Side cables only. The rejected center wavy cable is removed completely.
	for cable in range(2):
		var base_x:=-310.0+cable*620.0; var sway:=sin(current_time*(.32+cable*.05)+cable)*12.0; var points:=PackedVector2Array([Vector2(base_x,-560),Vector2(base_x+sway,-275),Vector2(base_x-15+sway,30),Vector2(base_x+7,560)]); draw_polyline(points,Color(.01,.02,.025,.72),13)

func _record_index() -> int:
	var index:=0
	if current_time>=_time("record_typing_2"):index=1
	if current_time>=_time("record_typing_3"):index=2
	return index
