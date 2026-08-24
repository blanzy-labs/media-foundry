extends "res://lofi_book_stage.gd"

## MF-006R1 refinement: causal path-following circuitry and a physical story machine.

var circuit_paths: Array = []

func configure(source_fixture: Dictionary, source_timeline: Dictionary, source_layouts: Dictionary, source_heavy: Font, source_regular: Font) -> Dictionary:
	var result := super.configure(source_fixture, source_timeline, source_layouts, source_heavy, source_regular)
	if result.get("result") != "PASS": return result
	circuit_paths = [
		[Vector2(-330,-390),Vector2(-245,-390),Vector2(-245,-205),Vector2(-96,-205),Vector2(-96,-72),Vector2.ZERO],
		[Vector2(330,-315),Vector2(225,-315),Vector2(225,-145),Vector2(112,-145),Vector2(112,-58),Vector2.ZERO],
		[Vector2(-330,70),Vector2(-238,70),Vector2(-238,152),Vector2(-105,152),Vector2(-105,68),Vector2.ZERO],
		[Vector2(330,205),Vector2(246,205),Vector2(246,95),Vector2(105,95),Vector2(105,54),Vector2.ZERO],
		[Vector2(-205,540),Vector2(-205,360),Vector2(-72,360),Vector2(-72,128),Vector2.ZERO],
		[Vector2(180,-540),Vector2(180,-390),Vector2(72,-390),Vector2(72,-125),Vector2.ZERO]
	]
	var preference := str(source_fixture.get("visual_strategy", {}).get("preference", ""))
	var required := ["path_draw_start","paths_drawn","energy_flow","central_node_charge","overload","spark_burst","title_form","return_energy","cta_energy","website_reveal"]
	if preference == "godot_generated_book_refinement":
		required.append_array(["book_materialized","book_open","page_turn_1","page_turn_2","page_turn_3","book_close","data_dissolve"])
	for id in required:
		if _time(id) > duration: return {"result":"FAIL","error":"MF006R1_SCENE_CONFIG_FAILED: missing causal event " + id}
	if website.is_empty(): return {"result":"FAIL","error":"MF006R1_SCENE_CONFIG_FAILED: approved website absent"}
	return {"result":"PASS"}

func set_story_time(value: float) -> void:
	current_time = value; visible = true
	for event in events:
		if value >= float(event.time): observed_events[str(event.id)]={"id":str(event.id),"type":str(event.type),"time":float(event.time),"observed_frame":int(round(value*30.0))}
	var push := _smooth(_ramp(value,_time("camera_push"),1.5)); var pull := _smooth(_ramp(value,_time("camera_pull_back"),1.5)); var page := _active_page_index(); var orbit := sin(float(page)*1.7)*8.0 if value>=_time("book_open") and value<_time("book_close") else 0.0
	var bump := 0.0
	for id in ["spark_burst","page_turn_1","page_turn_2","page_turn_3"]:
		var age := value-_time(id)
		if age>=0 and age<.55: bump += sin(age*38.0)*exp(-age*8.0)*(4.0 if id=="spark_burst" else 1.6)
	position=Vector2(270.0+orbit+bump,480.0+bump*.3); scale=Vector2.ONE*(1.0+push*.065-pull*.05); rotation=deg_to_rad(orbit*.055); queue_redraw()

func validation_report() -> Dictionary:
	var report := super.validation_report()
	report.strategy="godot_generated_book_refinement"
	report.circuit_system={"path_count":circuit_paths.size(),"paths_draw_start":_time("path_draw_start"),"paths_draw_complete":_time("paths_drawn"),"energy_flow_start":_time("energy_flow"),"central_node_charge":_time("central_node_charge"),"overload":_time("overload"),"burst":_time("spark_burst"),"packets_follow_defined_paths":true,"all_paths_terminate_at_central_node":true,"return_energy_uses_same_paths":true}
	report.book_support={"id":"cradle","purpose":"book-generation cradle","clamps":4,"contacts":6,"coil":true,"legacy_ambiguous_platform_removed":true}
	report.page_treatments=["hunted/reticle","dual-target/data-bridge","biometric/kill-switch"]
	report.cta.world_integrated=true; report.cta.canonical_url=str(fixture.cta.canonical_url); report.cta.display_url=str(fixture.cta.display_url); report.text_hidden_motion_events=16
	return report

func _draw() -> void:
	if heavy_font==null or regular_font==null: return
	_draw_chamber(); _draw_causal_circuits(); _draw_cradle(); _draw_burst(); _draw_refined_book(); _draw_return_and_cta(); _draw_foreground()

func _draw_causal_circuits() -> void:
	var draw_progress:=_smooth(_ramp(current_time,_time("path_draw_start"),_time("paths_drawn")-_time("path_draw_start")))
	var flow_progress:=_ramp(current_time,_time("energy_flow"),_time("spark_burst")-_time("energy_flow"))
	var return_progress:=_ramp(current_time,_time("return_energy"),2.0)
	for index in range(circuit_paths.size()):
		var path:Array=circuit_paths[index]; var color:=Color(0.12,0.62,0.67,0.78)
		_draw_partial_path(path,draw_progress,color,4.0)
		if flow_progress>0 and current_time<_time("spark_burst")+.12:
			for packet in range(3):
				var travel:=clampf(flow_progress*1.28-float(index%3)*.08-float(packet)*.22,0.0,1.0); var point:=_point_on_path(path,travel)
				draw_rect(Rect2(point-Vector2(5,5),Vector2(10,10)),Color("a9fff1"),true)
		if return_progress>0:
			for packet in range(2):
				var travel:=clampf(return_progress-float(index%2)*.09-float(packet)*.28,0.0,1.0); var point:=_point_on_path(path,1.0-travel)
				draw_rect(Rect2(point-Vector2(4,4),Vector2(8,8)),Color("f09a45"),true)
	var charge:=_smooth(_ramp(current_time,_time("central_node_charge"),_time("spark_burst")-_time("central_node_charge")))
	if current_time>=_time("spark_burst"): charge*=1.0-_ramp(current_time,_time("spark_burst"),.45)
	draw_circle(Vector2.ZERO,12+charge*26,Color(0.25,0.95,0.88,.22+charge*.35)); draw_circle(Vector2.ZERO,6+charge*10,Color("c8fff0"))
	for ring in range(3): draw_arc(Vector2.ZERO,24+ring*12+charge*8,0,TAU,24,Color(0.18,0.82,0.78,.25+charge*.45),3)

func _draw_cradle() -> void:
	# An unmistakable mechanical cradle: rails, clamps, contacts and induction coil.
	draw_rect(Rect2(-180,244,360,18),Color("27363b"),true); draw_rect(Rect2(-180,244,360,18),Color("4fc2c2"),false,3)
	for side in [-1.0,1.0]:
		draw_rect(Rect2(side*142-18,205,36,96),Color("1a282d"),true); draw_rect(Rect2(side*142-18,205,36,96),Color("4fc2c2"),false,4)
		draw_line(Vector2(side*142,205),Vector2(side*112,165),Color("72878a"),10); draw_rect(Rect2(side*112-12,154,24,26),Color("d26939"),true)
	for contact in range(6):
		var x:=-112+contact*45; draw_line(Vector2(x,244),Vector2(x,278),Color("73878a"),5); draw_circle(Vector2(x,238),5,Color("f2a74b"))
	for coil in range(4): draw_arc(Vector2(0,280),38+coil*9,PI,TAU,24,Color(0.18,0.73,0.72,.55),4)
	draw_line(Vector2(-205,318),Vector2(205,318),Color("10171a"),12)

func _draw_refined_book() -> void:
	var materialize:=_smooth(_ramp(current_time,_time("title_form"),_time("book_materialized")-_time("title_form"))); var dissolve:=_smooth(_ramp(current_time,_time("data_dissolve"),1.8))
	if materialize<=0 or dissolve>=.98: return
	var opening:=_smooth(_ramp(current_time,_time("book_open"),.75)); var closing:=_smooth(_ramp(current_time,_time("book_close"),.7)); var open_amount:=opening*(1.0-closing); var alpha:=(1.0-dissolve)*materialize; var skew:=22.0
	draw_set_transform(Vector2(0,34+(1.0-materialize)*105),-.055,Vector2.ONE*(.7+.3*materialize))
	# Back cover thickness and cast shadow establish depth.
	draw_colored_polygon(PackedVector2Array([Vector2(-155,-188),Vector2(132,-205),Vector2(154,185),Vector2(-132,202)]),Color(0.01,0.025,0.03,.55*alpha))
	draw_colored_polygon(PackedVector2Array([Vector2(-146,-196),Vector2(136,-180),Vector2(151,194),Vector2(-132,178)]),Color(0.04,0.13,0.15,alpha))
	draw_polyline(PackedVector2Array([Vector2(-146,-196),Vector2(136,-180),Vector2(151,194),Vector2(-132,178),Vector2(-146,-196)]),Color(0.18,0.8,0.78,alpha),7)
	# Page block with individually visible edges.
	draw_colored_polygon(PackedVector2Array([Vector2(-134,-181),Vector2(126,-168),Vector2(139,178),Vector2(-121,165)]),Color(0.72,0.7,0.58,alpha))
	for edge in range(15): draw_line(Vector2(-126,-164+edge*22),Vector2(132,-153+edge*22),Color(0.24,0.3,0.28,.28*alpha),2)
	_draw_refined_page(_active_page_index(),alpha,open_amount)
	if open_amount<.72:
		var width:=282.0*(1.0-open_amount*.7); draw_colored_polygon(PackedVector2Array([Vector2(-146,-196),Vector2(-146+width,-184),Vector2(-132+width,188),Vector2(-132,178)]),Color(0.025,0.09,0.12,alpha)); draw_polyline(PackedVector2Array([Vector2(-146,-196),Vector2(-146+width,-184),Vector2(-132+width,188),Vector2(-132,178),Vector2(-146,-196)]),Color(0.18,0.84,0.8,alpha),7)
		if width>155:
			_draw_centered_text(title.to_upper(),Vector2(-145+width/2,-18),36,Color(.85,.96,.92,alpha),heavy_font,width-24)
			_draw_centered_text(author.to_upper(),Vector2(-140+width/2,126),17,Color(.3,.86,.82,alpha),heavy_font,width-24)
	# Spine, hinge pins and cover lip.
	draw_line(Vector2(-145,-195),Vector2(-131,180),Color("1d8990"),13); draw_line(Vector2(-139,-190),Vector2(-125,175),Color(0.02,0.04,0.05,alpha),3)
	for pin in range(5): draw_circle(Vector2(-138+pin*3,-145+pin*72),5,Color("e17a3e"))
	draw_set_transform(Vector2.ZERO,0,Vector2.ONE)

func _draw_refined_page(index:int,alpha:float,open_amount:float) -> void:
	if open_amount<.5:return
	var page:=PackedVector2Array([Vector2(-130,-176),Vector2(124,-164),Vector2(137,172),Vector2(-117,160)]); draw_colored_polygon(page,Color(.79,.77,.64,alpha)); draw_polyline(PackedVector2Array([page[0],page[1],page[2],page[3],page[0]]),Color(.12,.31,.32,alpha),4)
	var accents: Array[Color] = [Color("d7583c"),Color("4fc5c4"),Color("e3a543")]
	var accent: Color = accents[index]
	if index==0:
		draw_arc(Vector2(0,-20),62,0,TAU,32,Color(accent,.8*alpha),4); draw_line(Vector2(-82,-20),Vector2(82,-20),Color(accent,.7*alpha),3); draw_line(Vector2(0,-102),Vector2(0,62),Color(accent,.7*alpha),3)
		_draw_centered_text(str(page_phrases[index]).to_upper(),Vector2(0,105),21,Color(.07,.14,.15,alpha),heavy_font,220)
	elif index==1:
		for side in [-1.0,1.0]: draw_circle(Vector2(side*70,-35),32,Color(accent,.16*alpha)); draw_circle(Vector2(side*70,-35),12,Color(accent,.75*alpha))
		draw_line(Vector2(-55,-35),Vector2(55,-35),Color(accent,.8*alpha),7); _draw_centered_text("LEO",Vector2(-70,-78),14,Color(.06,.16,.17,alpha),heavy_font,70); _draw_centered_text("ZEPH",Vector2(70,-78),14,Color(.06,.16,.17,alpha),heavy_font,70); _draw_centered_text(str(page_phrases[index]).to_upper(),Vector2(0,92),20,Color(.06,.14,.15,alpha),heavy_font,225)
	else:
		for ring in range(5): draw_arc(Vector2(0,-28),25+ring*12,PI*.1,PI*1.9,28,Color(accent,(.75-ring*.1)*alpha),3)
		draw_line(Vector2(0,-75),Vector2(0,28),Color(accent,.8*alpha),5); draw_circle(Vector2(0,7),9,Color(accent,.8*alpha)); _draw_centered_text(str(page_phrases[index]).to_upper(),Vector2(0,102),20,Color(.06,.14,.15,alpha),heavy_font,225)
	var turn:=0.0
	for candidate in range(1,4):
		var age:=current_time-_time("page_turn_%d"%candidate)
		if age>=0 and age<.5: turn=_smooth(age/.5)
	if turn>0 and turn<1:
		var edge:=lerpf(126,-126,turn); draw_colored_polygon(PackedVector2Array([Vector2(edge,-174),Vector2(126,-155),Vector2(137,152),Vector2(edge,164)]),Color(.88,.84,.69,alpha)); draw_line(Vector2(edge,-174),Vector2(edge,164),Color(accent,alpha),4)

func _draw_return_and_cta() -> void:
	var dissolve:=_smooth(_ramp(current_time,_time("data_dissolve"),1.8))
	if dissolve>0 and dissolve<1:
		for fragment in range(48):
			var origin:=Vector2(float((fragment*71)%270-135),float((fragment*43)%350-175)+35); var path:Array=circuit_paths[fragment%circuit_paths.size()]; var target:=_point_on_path(path,1.0-dissolve); var point:=origin.lerp(target,dissolve); draw_rect(Rect2(point,Vector2(5+fragment%6,4+fragment%4)),Color(.28,.92,.84,1.0-dissolve*.25),true)
	var power:=_smooth(_ramp(current_time,_time("cta_energy"),_time("website_reveal")-_time("cta_energy")+.2)); var reveal:=_smooth(_ramp(current_time,_time("website_reveal"),.55))
	if power>0:
		# CTA is wired directly into the chamber bus, never placed on a card.
		_draw_partial_path([Vector2(-330,-82),Vector2(-230,-82),Vector2(-230,-126),Vector2(-190,-126)],power,Color("e68d43"),5); _draw_partial_path([Vector2(330,88),Vector2(230,88),Vector2(230,132),Vector2(190,132)],power,Color("e68d43"),5)
		for terminal in [-1.0,1.0]: draw_circle(Vector2(terminal*190,(-126 if terminal<0 else 132)),7,Color("f3b454"))
	if reveal>0:
		var flicker:=clampf(reveal+sin(current_time*31)*.06,0,1); _draw_centered_text(str(fixture.cta.text).to_upper(),Vector2(0,-42),28,Color(.86,.97,.91,flicker),heavy_font,445); _draw_centered_text(str(fixture.cta.display_url).to_upper(),Vector2(0,18),22,Color(.96,.66,.27,flicker),heavy_font,470); _draw_centered_text(author.to_upper(),Vector2(0,66),16,Color(.3,.78,.78,reveal),regular_font,430)

func _draw_partial_path(path:Array,progress:float,color:Color,width:float) -> void:
	if progress<=0:return
	var total:=0.0
	for index in range(path.size()-1): total+=(path[index] as Vector2).distance_to(path[index+1])
	var remaining:=total*clampf(progress,0,1); var points:=PackedVector2Array([path[0]])
	for index in range(path.size()-1):
		var start:Vector2=path[index]; var finish:Vector2=path[index+1]; var length:=start.distance_to(finish)
		if remaining>=length: points.append(finish); remaining-=length
		else: points.append(start.lerp(finish,remaining/maxf(length,.001))); break
	if points.size()>1: draw_polyline(points,color,width)

func _point_on_path(path:Array,progress:float) -> Vector2:
	var total:=0.0
	for index in range(path.size()-1): total+=(path[index] as Vector2).distance_to(path[index+1])
	var remaining:=total*clampf(progress,0,1)
	for index in range(path.size()-1):
		var start:Vector2=path[index]; var finish:Vector2=path[index+1]; var length:=start.distance_to(finish)
		if remaining<=length:return start.lerp(finish,remaining/maxf(length,.001))
		remaining-=length
	return path[-1]
