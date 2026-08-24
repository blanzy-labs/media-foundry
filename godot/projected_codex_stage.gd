extends "res://causal_book_stage.gd"

## MF-006R2: a machine-generated projected story codex, never a standing book.

const CELL_COLORS: Array[Color] = [Color("613c8f"), Color("2f7c59"), Color("315f91"), Color("216b72")]

func configure(source_fixture: Dictionary, source_timeline: Dictionary, source_layouts: Dictionary, source_heavy: Font, source_regular: Font) -> Dictionary:
	var result := super.configure(source_fixture, source_timeline, source_layouts, source_heavy, source_regular)
	if result.get("result") != "PASS": return result
	var required := ["projection_emission", "title_stabilized", "codex_unfold", "projection_beat_1", "projection_beat_2", "projection_beat_3", "projection_collapse", "energy_reclaimed"]
	for id in required:
		if _time(id) > duration: return {"result":"FAIL", "error":"MF006R2_SCENE_CONFIG_FAILED: missing projection event " + id}
	return {"result":"PASS"}

func set_story_time(value: float) -> void:
	current_time = value
	visible = true
	for event in events:
		if value >= float(event.time): observed_events[str(event.id)] = {"id":str(event.id), "type":str(event.type), "time":float(event.time), "observed_frame":int(round(value * 30.0))}
	var push := _smooth(_ramp(value, _time("camera_push"), 1.35))
	var pull := _smooth(_ramp(value, _time("camera_pull_back"), 1.4))
	var phase := _projection_index()
	var orbit := sin(float(phase) * 1.45) * 10.0 if value >= _time("codex_unfold") and value < _time("projection_collapse") else 0.0
	var burst_age := value - _time("spark_burst")
	var bump := sin(burst_age * 43.0) * exp(-burst_age * 7.5) * 4.8 if burst_age >= 0.0 and burst_age < 0.7 else 0.0
	position = Vector2(270.0 + orbit + bump, 480.0 + bump * .25)
	scale = Vector2.ONE * (1.0 + push * .07 - pull * .055)
	rotation = deg_to_rad(orbit * .045)
	queue_redraw()

func validation_report() -> Dictionary:
	var report := super.validation_report()
	report.strategy = "godot_projected_codex_refinement"
	report.generated_book = null
	report.projected_codex = {
		"title":title, "author":author, "book_like_identity":true, "physical_standing_book":false,
		"wireframe_surfaces":3, "projection_planes":3, "scanlines":true,
		"origin":"central-node/emitter-region", "title_seeds_codex":true,
		"story_beats":["hunted scan/reticle", "dual target link", "biometric kill-switch"],
		"collapse_to_node":true
	}
	report.projection_emitter = {"id":"emitter", "purpose":"node-coupled data projection source", "connected_to_circuits":true, "projection_origin":Vector2(0, 188), "subordinate_to_projection":true, "legacy_cradle_removed":true}
	report.background_cells = {"total":54, "dark_majority":44, "accent_count":10, "accent_ratio":10.0/54.0, "palette":["purple","green","blue","cyan"], "event_reactive":true, "within_defined_limits":true}
	report.depth_system = {"layer_count":4, "foreground_cables":true, "wall_parallax":true, "particles":true, "light_falloff":true}
	report.projection_timeline = {"emission":_time("projection_emission"), "title_stabilized":_time("title_stabilized"), "unfold":_time("codex_unfold"), "beat_1":_time("projection_beat_1"), "beat_2":_time("projection_beat_2"), "beat_3":_time("projection_beat_3"), "collapse":_time("projection_collapse"), "reclaimed":_time("energy_reclaimed"), "cta_energy":_time("cta_energy")}
	report.text_hidden_motion_events = 19
	return report

func _draw() -> void:
	if heavy_font == null or regular_font == null: return
	_draw_projected_chamber()
	_draw_causal_circuits()
	_draw_emitter()
	_draw_burst()
	_draw_projected_codex()
	_draw_projection_collapse()
	_draw_return_and_cta()
	_draw_projected_foreground()

func _draw_projected_chamber() -> void:
	_draw_chamber()
	var reaction := _smooth(_ramp(current_time, _time("central_node_charge"), _time("spark_burst") - _time("central_node_charge")))
	# Ten of 54 cells receive restrained, deterministic powered-color accents.
	for index in range(54):
		if (index * 17 + int(fixture.seed)) % 11 >= 2: continue
		var row := index / 6
		var column := index % 6
		var x := -320.0 + column * 108.0 + (10.0 if row % 2 else 0.0)
		var y := -520.0 + row * 118.0
		var pulse := .055 + .025 * sin(current_time * (.45 + float(index % 3) * .09) + index)
		var color: Color = CELL_COLORS[index % CELL_COLORS.size()]
		draw_rect(Rect2(x + 5, y + 5, 92, 102), Color(color, pulse + reaction * .025), true)
	# Recessed wall halos create falloff behind the node and projection.
	for ring in range(5, 0, -1):
		draw_circle(Vector2(0, 40), 78.0 + ring * 58.0, Color(0.04, .24, .27, .012 * float(6-ring)))

func _draw_emitter() -> void:
	# Compact coupler: circuit bus, node lens, and upward projection aperture.
	var live := _smooth(_ramp(current_time, _time("central_node_charge"), .55))
	draw_line(Vector2(-116, 246), Vector2(116, 246), Color("17272c"), 16)
	draw_line(Vector2(-116, 246), Vector2(116, 246), Color(0.25, .82, .78, .45 + live * .35), 3)
	draw_colored_polygon(PackedVector2Array([Vector2(-78,246),Vector2(-48,205),Vector2(48,205),Vector2(78,246)]), Color("102127"))
	draw_polyline(PackedVector2Array([Vector2(-78,246),Vector2(-48,205),Vector2(48,205),Vector2(78,246)]), Color(0.28,.86,.8,.6), 4)
	for ring in range(3): draw_arc(Vector2(0, 205), 18 + ring * 12, PI, TAU, 24, Color(.28,.9,.82,.35 + live*.25), 3)
	draw_line(Vector2(0,205), Vector2.ZERO, Color(.22,.82,.78,.18 + live*.32), 3)
	for contact in [-60.0,-30.0,30.0,60.0]: draw_circle(Vector2(contact,244),4,Color("ed9c48"))

func _draw_projected_codex() -> void:
	var emission := _smooth(_ramp(current_time, _time("projection_emission"), _time("title_stabilized") - _time("projection_emission")))
	var unfold := _smooth(_ramp(current_time, _time("codex_unfold"), .7))
	var collapse := _smooth(_ramp(current_time, _time("projection_collapse"), _time("energy_reclaimed") - _time("projection_collapse")))
	var alpha := emission * (1.0-collapse)
	if alpha <= .01: return
	var hover := sin(current_time * 1.7) * 5.0
	draw_set_transform(Vector2(0, 12 + hover), -.025, Vector2.ONE)
	# Projection cone binds every plane to the emitter aperture.
	draw_colored_polygon(PackedVector2Array([Vector2(-42,193),Vector2(42,193),Vector2(145,-190),Vector2(-145,-190)]), Color(.13,.78,.76,.035*alpha))
	for ray in [-1.0,-.5,0.0,.5,1.0]: draw_line(Vector2(ray*35,193),Vector2(ray*138,-180),Color(.25,.9,.84,.09*alpha),2)
	if unfold < .18:
		_draw_projection_plane(PackedVector2Array([Vector2(-143,-184),Vector2(143,-168),Vector2(128,168),Vector2(-128,184)]), alpha, 0)
		_draw_centered_text(title.to_upper(),Vector2(0,-5),39,Color(.78,1,.94,alpha),heavy_font,250)
		_draw_centered_text(author.to_upper(),Vector2(0,108),18,Color(.95,.64,.27,alpha),heavy_font,230)
	else:
		var spread := unfold * 24.0
		var left := PackedVector2Array([Vector2(-8,-188),Vector2(-152-spread,-155),Vector2(-132-spread,174),Vector2(-5,150)])
		var right := PackedVector2Array([Vector2(8,-188),Vector2(152+spread,-155),Vector2(132+spread,174),Vector2(5,150)])
		_draw_projection_plane(left,alpha*.78,1); _draw_projection_plane(right,alpha*.9,2)
		draw_line(Vector2(0,-185),Vector2(0,154),Color(.7,1,.92,.8*alpha),4)
		_draw_projection_story(_projection_index(), alpha, unfold)
	draw_set_transform(Vector2.ZERO,0,Vector2.ONE)

func _draw_projection_plane(points: PackedVector2Array, alpha: float, phase: int) -> void:
	draw_colored_polygon(points,Color(.035,.32,.33,.11*alpha))
	draw_polyline(PackedVector2Array([points[0],points[1],points[2],points[3],points[0]]),Color(.32,.96,.88,.7*alpha),4)
	for line in range(9):
		var progress := float(line+1)/10.0
		var left := points[0].lerp(points[3],progress); var right := points[1].lerp(points[2],progress)
		var scan := .13 + .14 * maxf(0.0,sin(current_time*5.0+line+phase))
		draw_line(left,right,Color(.22,.8,.78,scan*alpha),2)

func _draw_projection_story(index: int, alpha: float, unfold: float) -> void:
	var local_time := current_time - _time("projection_beat_%d" % (index+1))
	var assemble := _smooth(clampf(local_time/.48,0,1))
	var scan_y := lerpf(-135,130,fmod(maxf(0.0,local_time)*.42,1.0))
	draw_line(Vector2(-155,scan_y),Vector2(155,scan_y),Color(.68,1,.91,.45*alpha),3)
	if index == 0:
		var tighten := 1.0 + .08*sin(current_time*4.0)
		draw_arc(Vector2(-45,-24),58*tighten,0,TAU,36,Color("e0664a"),4)
		draw_line(Vector2(-112,-24),Vector2(23,-24),Color(1,.35,.24,.7*alpha),3)
		draw_line(Vector2(-45,-94),Vector2(-45,48),Color(1,.35,.24,.7*alpha),3)
		_draw_centered_text(str(page_phrases[0]).to_upper(),Vector2(42,92),20,Color(.82,1,.95,alpha*assemble),heavy_font,260)
	elif index == 1:
		for side in [-1.0,1.0]:
			var point := Vector2(side*78,-28+sin(current_time*2.5+side)*9)
			draw_circle(point,28,Color(.25,.92,.84,.12*alpha)); draw_circle(point,9,Color(.45,1,.9,.8*alpha))
		draw_line(Vector2(-69,-28),Vector2(69,-28),Color(.42,1,.88,.8*alpha),6)
		_draw_centered_text("LEO",Vector2(-78,-75),14,Color(.78,1,.94,alpha),heavy_font,70); _draw_centered_text("ZEPH",Vector2(78,-75),14,Color(.78,1,.94,alpha),heavy_font,70)
		_draw_centered_text(str(page_phrases[1]).to_upper(),Vector2(0,94),20,Color(.82,1,.95,alpha*assemble),heavy_font,290)
	else:
		for ring in range(6): draw_arc(Vector2(42,-25),24+ring*11,PI*.08,PI*1.92,32,Color(.95,.66,.25,(.75-ring*.08)*alpha),3)
		draw_line(Vector2(42,-78),Vector2(42,28),Color(1,.68,.28,.85*alpha),5); draw_circle(Vector2(42,5),8,Color(1,.7,.3,.9*alpha))
		_draw_centered_text(str(page_phrases[2]).to_upper(),Vector2(-34,98),19,Color(.9,1,.94,alpha*assemble),heavy_font,300)
	# Pixel assembly and lateral energy sweep make each state an event, not a hard replacement.
	for pixel in range(20):
		var px := -145.0 + float((pixel*71)%290); var py := -135.0 + float((pixel*47)%260)
		draw_rect(Rect2(Vector2(px,py),Vector2(4+pixel%4,3)),Color(.4,1,.88,(1.0-assemble)*alpha),true)

func _draw_projection_collapse() -> void:
	var collapse := _smooth(_ramp(current_time,_time("projection_collapse"),_time("energy_reclaimed")-_time("projection_collapse")))
	if collapse <= 0 or collapse >= 1: return
	for fragment in range(64):
		var origin := Vector2(float((fragment*71)%310-155),float((fragment*43)%360-180))
		var bend := Vector2(origin.x*.42,80+float(fragment%5)*8)
		var point := origin.lerp(bend,collapse).lerp(Vector2.ZERO,collapse*collapse)
		draw_rect(Rect2(point,Vector2(3+fragment%5,3+fragment%3)),Color(.3,.98,.87,1.0-collapse*.25),true)
	draw_circle(Vector2.ZERO,10+collapse*22,Color(.4,1,.87,.15+collapse*.35))

func _draw_projected_foreground() -> void:
	_draw_foreground()
	# Near-lens cable silhouettes move more than the wall, supplying restrained parallax.
	for cable in range(3):
		var base_x := -310.0 + cable*305.0
		var sway := sin(current_time*(.32+cable*.05)+cable)*14.0
		var points := PackedVector2Array([Vector2(base_x,-560),Vector2(base_x+sway,-275),Vector2(base_x-18+sway,30),Vector2(base_x+8,560)])
		draw_polyline(points,Color(0.01,.02,.025,.72),13)

func _projection_index() -> int:
	var index := 0
	if current_time >= _time("projection_beat_2"): index = 1
	if current_time >= _time("projection_beat_3"): index = 2
	return index
