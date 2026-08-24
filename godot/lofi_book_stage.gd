extends Node2D

## Deterministic low-resolution electronic chamber and generated physical book.

var fixture: Dictionary = {}
var timeline: Dictionary = {}
var heavy_font: Font
var regular_font: Font
var current_time := 0.0
var duration := 0.0
var components: Dictionary = {}
var events: Array = []
var observed_events: Dictionary = {}
var title := ""
var author := ""
var website := ""
var page_phrases: Array = []

const COMPONENT_TYPES := ["electronic_chamber", "circuit_crawler", "electrical_burst", "electronic_platform", "book_generation_cradle", "projection_emitter", "generated_book", "projected_codex", "projected_data_window", "page", "projection_plane", "record_channel", "data_dissolve", "projection_collapse", "screen_collapse", "lofi_light", "powered_cells", "website_reveal"]
const EVENT_TYPES := ["circuit_start", "path_draw_start", "paths_drawn", "energy_flow", "circuit_convergence", "central_node_charge", "overload", "overload_pulse", "overload_peak", "spark_burst", "title_form", "title_stabilized", "projection_emission", "codex_unfold", "screen_initialize", "record_query", "record_typing", "record_activity", "record_confirm", "record_lock", "record_hold", "record_reset", "screen_refresh", "projection_beat", "projection_transition", "book_materialized", "camera_push", "book_open", "page_turn", "page_reaction", "book_close", "projection_collapse", "screen_collapse", "energy_reclaimed", "data_dissolve", "return_energy", "camera_pull_back", "cta_energy", "cta_typing", "cta_lock", "cta_reveal", "website_reveal", "settle"]
const CAMERA_EVENT_TYPES := ["camera_push", "camera_pull_back", "settle", "spark_burst"]

func configure(source_fixture: Dictionary, source_timeline: Dictionary, _source_layouts: Dictionary, source_heavy: Font, source_regular: Font) -> Dictionary:
	fixture = source_fixture
	timeline = source_timeline
	heavy_font = source_heavy
	regular_font = source_regular
	duration = float(timeline.get("duration", 0.0))
	var subject: Dictionary = fixture.get("subject", {})
	title = str(subject.get("title", ""))
	author = str(subject.get("author", ""))
	var website_value = fixture.get("cta", {}).get("website")
	website = str(website_value) if typeof(website_value) == TYPE_STRING else ""
	page_phrases = fixture.get("page_phrases", [])
	var extended := str(fixture.get("visual_strategy", {}).get("preference", "")) in ["godot_extended_data_window_refinement", "godot_live_investigation_refinement", "godot_final_polish_refinement", "godot_lower_right_polish_refinement"]
	if title.is_empty() or author.is_empty() or page_phrases.size() < 2 or page_phrases.size() > 3 or duration < 17.0 or duration > (30.0 if extended else 20.0):
		return {"result": "FAIL", "error": "MF006_SCENE_CONFIG_FAILED: title, author, page phrases, or duration invalid"}
	var scene: Dictionary = fixture.get("generated_scene", {})
	for item in scene.get("components", []):
		if typeof(item) != TYPE_DICTIONARY or str(item.get("id", "")).is_empty() or str(item.get("type", "")) not in COMPONENT_TYPES or components.has(str(item.id)):
			return {"result": "FAIL", "error": "MF006_SCENE_CONFIG_FAILED: malformed or duplicate component"}
		components[str(item.id)] = item
	events = scene.get("events", [])
	var previous := -1.0
	for item in events:
		var event_time := float(item.get("time", -1.0))
		if typeof(item) != TYPE_DICTIONARY or str(item.get("id", "")).is_empty() or str(item.get("type", "")) not in EVENT_TYPES or event_time < 0.0 or event_time >= duration or event_time < previous:
			return {"result": "FAIL", "error": "MF006_SCENE_CONFIG_FAILED: malformed or unordered event"}
		previous = event_time
	var required := ["chamber", "circuits", "burst", "book", "page_1", "page_2", "page_3", "dissolve", "lights"]
	if required.any(func(id): return not components.has(id)):
		return {"result": "FAIL", "error": "MF006_SCENE_CONFIG_FAILED: required generated component absent"}
	if not components.has("platform") and not components.has("cradle"):
		return {"result": "FAIL", "error": "MF006_SCENE_CONFIG_FAILED: generated book support absent"}
	return {"result": "PASS"}

func set_story_time(value: float) -> void:
	current_time = value
	visible = true
	for event in events:
		if value >= float(event.time):
			observed_events[str(event.id)] = {"id": str(event.id), "type": str(event.type), "time": float(event.time), "observed_frame": int(round(value * 30.0))}
	var push := _smooth(_ramp(value, _time("camera_push"), 2.2))
	var pull := _smooth(_ramp(value, _time("camera_pull_back"), 1.8))
	var burst_age := value - _time("spark_burst")
	var bump := sin(burst_age * 45.0) * exp(-burst_age * 7.0) * 4.0 if burst_age >= 0.0 and burst_age < 0.8 else 0.0
	position = Vector2(270.0 + bump, 480.0 + bump * 0.35)
	scale = Vector2.ONE * (1.0 + push * 0.055 - pull * 0.045)
	queue_redraw()

func validation_report() -> Dictionary:
	var ordered := []
	for event in events:
		if observed_events.has(str(event.id)): ordered.append(observed_events[str(event.id)])
	return {
		"strategy": "godot_generated_scene",
		"internal_resolution": {"width": 540, "height": 960},
		"continuous_scene": {"start": 0.0, "end": duration, "duration": duration},
		"components": components.keys(),
		"configured_events": events,
		"observed_events": ordered,
		"camera_events": ordered.filter(func(item): return item.type in CAMERA_EVENT_TYPES),
		"generated_book": {"title": title, "author": author, "front_cover": true, "back_cover": true, "spine": true, "page_block": true, "independent_pages": page_phrases.size()},
		"cta": {"text": str(fixture.get("cta", {}).get("text", "")), "website": website, "safe_rect": {"x": 44, "y": 330, "width": 452, "height": 260}},
		"static_book_cover_embedded": false,
		"external_static_media_primary": false,
		"text_hidden_motion_events": ordered.filter(func(item): return item.type in ["circuit_start", "circuit_convergence", "spark_burst", "book_materialized", "book_open", "page_turn", "page_reaction", "book_close", "data_dissolve"] ).size(),
		"result": "PASS" if ordered.size() == events.size() else "FAIL"
	}

func _draw() -> void:
	if heavy_font == null or regular_font == null: return
	_draw_chamber()
	_draw_circuits()
	_draw_platform()
	_draw_burst()
	_draw_book()
	_draw_dissolve_and_cta()
	_draw_foreground()

func _draw_chamber() -> void:
	draw_rect(Rect2(-330, -540, 660, 1080), Color("070b0f"))
	# Battered low-resolution metal panels.
	for row in range(9):
		for column in range(6):
			var x := -320.0 + column * 108.0 + (10.0 if row % 2 else 0.0)
			var y := -520.0 + row * 118.0
			var shade := 0.025 * float((row * 3 + column + int(fixture.seed)) % 3)
			draw_rect(Rect2(x, y, 102, 112), Color("121b22").lightened(shade), true)
			draw_rect(Rect2(x, y, 102, 112), Color("030608"), false, 4)
			if (row + column) % 4 == 0: draw_line(Vector2(x + 14, y + 15), Vector2(x + 78, y + 12), Color(0.32, 0.4, 0.42, 0.25), 2)
	# Hanging cables and dirty glass depth layer.
	for cable in range(5):
		if str(fixture.get("visual_strategy", {}).get("preference", "")) in ["godot_projected_data_window_refinement", "godot_extended_data_window_refinement", "godot_live_investigation_refinement", "godot_final_polish_refinement", "godot_lower_right_polish_refinement"] and cable == 2:
			continue
		var anchor_x := -240.0 + cable * 118.0
		var sway := sin(current_time * (0.55 + cable * 0.07) + cable) * 10.0
		var points := PackedVector2Array([Vector2(anchor_x, -540), Vector2(anchor_x + sway, -390), Vector2(anchor_x - 18 + sway, -250), Vector2(anchor_x + 8, -155)])
		draw_polyline(points, Color("26333a"), 8)
		draw_polyline(points, Color(0.05, 0.07, 0.08, 0.9), 2)
	var reaction := _page_reaction()
	for led in range(13):
		var phase := sin(current_time * (4.0 + led % 3) + led * 1.9)
		var led_color := Color("39b8c9").lerp(Color("e55b2c"), reaction)
		draw_circle(Vector2(-285 + (led * 47) % 570, -440 + (led * 83) % 650), 3.0 + maxf(0.0, phase), Color(led_color, 0.35 + maxf(0.0, phase) * 0.35))

func _draw_circuits() -> void:
	var convergence := _smooth(_ramp(current_time, _time("circuit_start"), _time("circuit_convergence") - _time("circuit_start") + 0.35))
	var fade_after := 1.0 - 0.72 * _ramp(current_time, _time("book_materialized"), 1.0)
	var targets := [Vector2(-68, -70), Vector2(68, -70), Vector2(-78, 105), Vector2(78, 105), Vector2(0, 170), Vector2(0, -180)]
	var starts := [Vector2(-330, -410), Vector2(330, -315), Vector2(-330, 120), Vector2(330, 245), Vector2(-220, 540), Vector2(190, -540)]
	for index in range(starts.size()):
		var start: Vector2 = starts[index]
		var target: Vector2 = targets[index]
		var stagger := clampf(convergence * 1.25 - float(index % 3) * 0.08, 0.0, 1.0)
		var mid := Vector2(lerpf(start.x, target.x, 0.56), start.y + (target.y - start.y) * 0.22 + float((index * 37) % 45 - 22))
		var end := mid.lerp(target, stagger)
		var color := Color(0.18, 0.82, 0.86, (0.42 + 0.25 * sin(current_time * 9.0 + index)) * fade_after)
		draw_polyline(PackedVector2Array([start, Vector2(mid.x, start.y), mid, Vector2(mid.x, end.y), end]), color, 4)
		for segment in range(3):
			var pulse := fmod(current_time * (0.55 + index * 0.03) + segment * 0.31, 1.0)
			var point := start.lerp(end, pulse)
			draw_rect(Rect2(point - Vector2(4, 4), Vector2(8, 8)), Color("a9f2e8"), true)

func _draw_platform() -> void:
	var pulse := 0.55 + 0.22 * sin(current_time * 3.2)
	draw_colored_polygon(PackedVector2Array([Vector2(-180, 245), Vector2(180, 245), Vector2(128, 330), Vector2(-128, 330)]), Color("17242a"))
	draw_polyline(PackedVector2Array([Vector2(-180, 245), Vector2(180, 245), Vector2(128, 330), Vector2(-128, 330), Vector2(-180, 245)]), Color(0.25, 0.85, 0.82, pulse), 5)
	for slot in range(7): draw_rect(Rect2(-112 + slot * 34, 282, 17, 7), Color(0.2, 0.75, 0.72, pulse), true)

func _draw_burst() -> void:
	var age := current_time - _time("spark_burst")
	if age < 0.0 or age > 1.05: return
	var fade := 1.0 - age / 1.05
	draw_circle(Vector2.ZERO, 115.0 * (1.0 - fade) + 16.0, Color(0.38, 0.95, 0.9, 0.16 * fade))
	for spark in range(18):
		var angle := float((spark * 97 + int(fixture.seed)) % 360) * PI / 180.0
		var distance := (28.0 + float((spark * 23) % 110)) * (1.0 - fade)
		var point := Vector2(cos(angle), sin(angle)) * distance
		draw_line(point, point + Vector2(cos(angle), sin(angle)) * (10.0 + spark % 9), Color(0.7, 1.0, 0.88, fade), 3)

func _draw_book() -> void:
	var materialize := _smooth(_ramp(current_time, _time("title_form"), _time("book_materialized") - _time("title_form")))
	var dissolve := _smooth(_ramp(current_time, _time("data_dissolve"), 2.0))
	if materialize <= 0.0 or dissolve >= 0.98: return
	var opening := _smooth(_ramp(current_time, _time("book_open"), 0.8))
	var closing := _smooth(_ramp(current_time, _time("book_close"), 0.75))
	var open_amount := opening * (1.0 - closing)
	var alpha := (1.0 - dissolve) * materialize
	var assemble_y := (1.0 - materialize) * 130.0
	draw_set_transform(Vector2(0, 42 + assemble_y), -0.035 + sin(current_time * 0.7) * 0.008, Vector2.ONE * (0.72 + 0.28 * materialize))
	# Back cover, spine and page block are independent generated geometry.
	draw_rect(Rect2(-145, -195, 290, 390), Color(0.08, 0.16, 0.19, alpha), true)
	draw_rect(Rect2(-145, -195, 290, 390), Color(0.24, 0.86, 0.82, alpha), false, 7)
	draw_rect(Rect2(-135, -181, 270, 360), Color(0.72, 0.72, 0.63, alpha), true)
	for line in range(14): draw_line(Vector2(-128, -170 + line * 25), Vector2(128, -168 + line * 25), Color(0.32, 0.34, 0.31, 0.22 * alpha), 2)
	var page_index := _active_page_index()
	_draw_page_turn(page_index, alpha, open_amount)
	if open_amount < 0.64:
		var cover_width := 290.0 * (1.0 - open_amount * 0.72)
		draw_rect(Rect2(-145, -195, cover_width, 390), Color(0.055, 0.12, 0.15, alpha), true)
		draw_rect(Rect2(-145, -195, cover_width, 390), Color(0.16, 0.72, 0.77, alpha), false, 7)
		if cover_width > 150.0:
			_draw_centered_text(title.to_upper(), Vector2(-145 + cover_width / 2.0, -20), 44, Color(0.85, 0.96, 0.93, alpha), heavy_font, cover_width - 20.0)
			_draw_centered_text(author.to_upper(), Vector2(-145 + cover_width / 2.0, 130), 20, Color(0.35, 0.86, 0.84, alpha), heavy_font, cover_width - 20.0)
	# Spine remains visible during opening.
	draw_rect(Rect2(-153, -195, 15, 390), Color(0.12, 0.5, 0.55, alpha), true)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

func _draw_page_turn(index: int, alpha: float, open_amount: float) -> void:
	if open_amount < 0.55: return
	var phrase := str(page_phrases[mini(index, page_phrases.size() - 1)]).to_upper()
	var turn_progress := 0.0
	for candidate in range(1, page_phrases.size() + 1):
		var turn_age := current_time - _time("page_turn_%d" % candidate)
		if turn_age >= 0.0 and turn_age < 0.55: turn_progress = _smooth(turn_age / 0.55)
	var page_color := Color(0.78, 0.78, 0.68, alpha)
	draw_rect(Rect2(-132, -178, 264, 350), page_color, true)
	draw_rect(Rect2(-132, -178, 264, 350), Color(0.16, 0.3, 0.31, alpha), false, 4)
	for rule in range(7): draw_line(Vector2(-98, -112 + rule * 34), Vector2(99, -110 + rule * 34), Color(0.18, 0.25, 0.25, 0.18 * alpha), 2)
	_draw_centered_text(phrase, Vector2(0, -5), 25, Color(0.07, 0.16, 0.18, alpha), heavy_font, 225.0)
	if turn_progress > 0.0 and turn_progress < 1.0:
		var edge_x := lerpf(132.0, -132.0, turn_progress)
		draw_colored_polygon(PackedVector2Array([Vector2(edge_x, -178), Vector2(132, -155), Vector2(132, 155), Vector2(edge_x, 172)]), Color(0.88, 0.87, 0.74, alpha))
		draw_line(Vector2(edge_x, -178), Vector2(edge_x, 172), Color(0.16, 0.32, 0.32, alpha), 4)

func _draw_dissolve_and_cta() -> void:
	var dissolve := _smooth(_ramp(current_time, _time("data_dissolve"), 2.25))
	if dissolve > 0.0 and dissolve < 1.0:
		for fragment in range(42):
			var origin := Vector2(float((fragment * 71) % 270 - 135), float((fragment * 43) % 360 - 180) + 42)
			var side := -1.0 if fragment % 2 == 0 else 1.0
			var target := Vector2(side * (260 + fragment % 5 * 15), -360 + float((fragment * 67) % 720))
			var point := origin.lerp(target, dissolve)
			draw_rect(Rect2(point, Vector2(5 + fragment % 7, 4 + fragment % 5)), Color(0.28, 0.92, 0.86, 1.0 - dissolve * 0.35), true)
	var cta := _smooth(_ramp(current_time, _time("cta_reveal"), 0.75))
	if cta > 0.0:
		var jitter := sin((current_time - _time("cta_reveal")) * 19.0) * exp(-(current_time - _time("cta_reveal")) * 4.0) * 5.0
		draw_rect(Rect2(-226 + jitter, -110, 452, 220), Color(0.035, 0.09, 0.11, 0.92 * cta), true)
		draw_rect(Rect2(-226 + jitter, -110, 452, 220), Color(0.22, 0.88, 0.83, cta), false, 6)
		_draw_centered_text(str(fixture.get("cta", {}).get("text", "")).to_upper(), Vector2(jitter, -28), 28, Color(0.83, 0.96, 0.91, cta), heavy_font, 420.0)
		if not website.is_empty(): _draw_centered_text(website, Vector2(jitter, 32), 28, Color(0.95, 0.68, 0.28, cta), heavy_font, 420.0)
		_draw_centered_text(author.to_upper(), Vector2(jitter, 78), 17, Color(0.32, 0.75, 0.76, cta), regular_font, 420.0)

func _draw_foreground() -> void:
	for mote in range(20):
		var x := -310.0 + float((mote * 101 + int(current_time * (7 + mote % 4))) % 620)
		var y := -490.0 + float((mote * 149 - int(current_time * (10 + mote % 3))) % 940)
		draw_rect(Rect2(x, y, 2 + mote % 3, 2 + mote % 2), Color(0.42, 0.78, 0.75, 0.15), true)

func _active_page_index() -> int:
	var index := 0
	for candidate in range(1, page_phrases.size() + 1):
		if current_time >= _time("page_turn_%d" % candidate): index = candidate - 1
	return index

func _page_reaction() -> float:
	var index := _active_page_index()
	return float(index) / maxf(1.0, float(page_phrases.size() - 1))

func _draw_centered_text(text: String, center: Vector2, font_size: int, color: Color, font: Font, maximum_width: float) -> void:
	var size := font_size
	while size > 12 and font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x > maximum_width: size -= 1
	var width := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	draw_string(font, Vector2(center.x - width / 2.0, center.y + size * 0.36), text, HORIZONTAL_ALIGNMENT_LEFT, -1, size, color)

func _time(id: String) -> float:
	for event in events:
		if str(event.id) == id: return float(event.time)
	return duration + 10.0

func _ramp(value: float, start: float, span: float) -> float:
	return clampf((value - start) / maxf(span, 0.001), 0.0, 1.0)

func _smooth(value: float) -> float:
	return value * value * (3.0 - 2.0 * value)
