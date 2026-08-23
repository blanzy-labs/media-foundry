extends Node2D

## Reusable deterministic micro-stage for persistent Godot-native story scenes.

var fixture: Dictionary = {}
var timeline: Dictionary = {}
var layouts: Dictionary = {}
var heavy_font: Font
var regular_font: Font
var current_time := 0.0
var scene_start := 0.0
var scene_end := 0.0
var components: Dictionary = {}
var events: Array = []
var observed_events: Dictionary = {}
var motion_intensity := 1.0

const COMPONENT_TYPES := ["dirty_wall", "hanging_lamp", "pipe", "toilet", "primitive_character", "turd_prop", "sack", "physical_sign", "physical_title", "dust"]
const EVENT_TYPES := ["camera_push", "small_reveal", "character_enters", "turd_highlight", "character_approaches", "turd_grab", "impact_bump", "physical_sign", "physical_title", "settle"]

func configure(source_fixture: Dictionary, source_timeline: Dictionary, source_layouts: Dictionary, source_heavy: Font, source_regular: Font) -> Dictionary:
	fixture = source_fixture
	visible = false
	timeline = source_timeline
	layouts = source_layouts
	heavy_font = source_heavy
	regular_font = source_regular
	var scene: Dictionary = fixture.get("generated_scene", {})
	scene_start = float(scene.get("start", 0.0))
	scene_end = float(scene.get("end", 0.0))
	motion_intensity = float(scene.get("motion_intensity", 1.0))
	if scene_end - scene_start < 5.0 or motion_intensity < 0.5 or motion_intensity > 1.5:
		return {"result": "FAIL", "error": "GENERATED_SCENE_CONFIG_FAILED: invalid continuous interval or motion intensity"}
	for item in scene.get("components", []):
		if typeof(item) != TYPE_DICTIONARY or str(item.get("id", "")).is_empty() or str(item.get("type", "")) not in COMPONENT_TYPES or components.has(str(item.id)):
			return {"result": "FAIL", "error": "GENERATED_SCENE_CONFIG_FAILED: malformed or duplicate component"}
		components[str(item.id)] = item
	events = scene.get("events", [])
	var previous := -1.0
	for item in events:
		if typeof(item) != TYPE_DICTIONARY or str(item.get("id", "")).is_empty() or str(item.get("type", "")) not in EVENT_TYPES:
			return {"result": "FAIL", "error": "GENERATED_SCENE_CONFIG_FAILED: malformed event"}
		var event_time := float(item.get("time", -1.0))
		if event_time < scene_start or event_time >= scene_end or event_time < previous:
			return {"result": "FAIL", "error": "GENERATED_SCENE_CONFIG_FAILED: events must be ordered inside the continuous scene"}
		previous = event_time
	var required := ["wall", "lamp", "toilet", "character", "turd", "sack", "punch_sign", "title"]
	if required.any(func(id): return not components.has(id)):
		return {"result": "FAIL", "error": "GENERATED_SCENE_CONFIG_FAILED: required reusable components are absent"}
	return {"result": "PASS"}

func set_story_time(value: float) -> void:
	current_time = value
	visible = value >= scene_start and value < scene_end
	for event in events:
		if value >= float(event.time):
			observed_events[str(event.id)] = {"id": str(event.id), "type": str(event.type), "time": float(event.time), "observed_frame": int(round(value * 30.0))}
	var push := _ramp(value, _time("camera_push"), 3.6)
	var reveal := _ramp(value, _time("toilet_reveal"), 1.4)
	var bump_age := value - _time("grab_impact")
	var bump := sin(bump_age * 42.0) * exp(-bump_age * 7.0) * 4.0 * motion_intensity if bump_age >= 0.0 and bump_age < 0.8 else 0.0
	position = Vector2(270.0 - reveal * 10.0 + bump, 480.0 + cos(bump_age * 31.0) * bump * 0.45)
	scale = Vector2.ONE * (1.0 + 0.035 * push * motion_intensity)
	queue_redraw()

func validation_report() -> Dictionary:
	var ordered := []
	for event in events:
		if observed_events.has(str(event.id)):
			ordered.append(observed_events[str(event.id)])
	return {"strategy": "generated_scene", "continuous_scene": {"start": scene_start, "end": scene_end, "duration": scene_end - scene_start}, "components": components.keys(), "configured_events": events, "observed_events": ordered, "camera_events": ordered.filter(func(item): return item.type in ["camera_push", "small_reveal", "impact_bump", "settle"]), "text_only_full_frame_states": 2, "external_static_media_primary": false, "result": "PASS" if ordered.size() == events.size() else "FAIL"}

func _draw() -> void:
	if not visible or heavy_font == null:
		return
	_draw_room()
	_draw_ambient()
	_draw_toilet()
	_draw_turd()
	_draw_character()
	_draw_story_signs()

func _draw_room() -> void:
	draw_rect(Rect2(-330, -540, 660, 1080), Color("171513"))
	var parallax := sin(current_time * 0.21) * 2.0 * motion_intensity
	for row in range(12):
		for column in range(7):
			var x := -315.0 + column * 100.0 + (50.0 if row % 2 else 0.0) + parallax
			var y := -520.0 + row * 88.0
			draw_rect(Rect2(x, y, 96, 84), Color("302b27").lightened(float((row + column) % 3) * 0.018), true)
			draw_rect(Rect2(x, y, 96, 84), Color("161210"), false, 3)
	draw_rect(Rect2(-330, 310, 660, 230), Color("211a16"))
	for line in range(9):
		draw_line(Vector2(-330, 320 + line * 24), Vector2(330, 315 + line * 24), Color("0f0c0a"), 2)
	# Reusable pipes create a foreground depth plane.
	draw_line(Vector2(-292, -510), Vector2(-292, 210), Color("59605b"), 25)
	draw_line(Vector2(-304, -510), Vector2(-304, 210), Color("1a1c1a"), 4)
	draw_arc(Vector2(-226, 210), 66, 0, PI, 24, Color("59605b"), 25)
	draw_line(Vector2(-160, 210), Vector2(-160, 330), Color("59605b"), 25)

func _draw_ambient() -> void:
	var sway := sin(current_time * 1.35) * 0.055 * motion_intensity
	var lamp_anchor := Vector2(150, -530)
	var lamp_end := lamp_anchor + Vector2(sin(sway) * 185, cos(sway) * 185)
	draw_line(lamp_anchor, lamp_end, Color("171311"), 8)
	draw_circle(lamp_end, 34, Color("e1a53e"))
	draw_arc(lamp_end, 38, PI, TAU, 20, Color("56341c"), 7)
	var flicker := 0.055 + 0.025 * sin(current_time * 7.0 + float(int(fixture.seed) % 13))
	draw_colored_polygon(PackedVector2Array([lamp_end + Vector2(-20, 28), lamp_end + Vector2(20, 28), Vector2(258, 265), Vector2(15, 265)]), Color(1.0, 0.74, 0.28, flicker))
	for mote in range(16):
		var x := -245.0 + float((mote * 83 + int(current_time * (5 + mote % 3))) % 500)
		var y := -360.0 + float((mote * 137 - int(current_time * (8 + mote % 4))) % 620)
		draw_circle(Vector2(x, y), 1.2 + float(mote % 2), Color(0.92, 0.79, 0.48, 0.19))

func _draw_toilet() -> void:
	var reveal := _smooth(_ramp(current_time, _time("toilet_reveal"), 0.9))
	var x := lerpf(350.0, 118.0, reveal)
	draw_rect(Rect2(x - 66, -12, 132, 112), Color("c4bfaa"), true)
	draw_rect(Rect2(x - 66, -12, 132, 112), Color("39352f"), false, 6)
	_draw_ellipse_shape(Vector2(x, 92), Vector2(88, 48), Color("ded8be"))
	_draw_ellipse_shape(Vector2(x, 92), Vector2(56, 25), Color("302923"))
	draw_rect(Rect2(x - 47, 118, 94, 122), Color("b3ad98"), true)
	draw_line(Vector2(x + 50, 15), Vector2(x + 76, -28), Color("827965"), 7)

func _draw_turd() -> void:
	var highlight := _ramp(current_time, _time("turd_highlight"), 0.45)
	var grab := _ramp(current_time, _time("turd_grab"), 0.28)
	if grab >= 1.0:
		return
	var center := Vector2(118, 79 - highlight * 8.0)
	var alpha := 1.0 - grab
	for item in [Vector3(0, 8, 25), Vector3(-3, -9, 20), Vector3(2, -24, 14), Vector3(-1, -36, 9)]:
		draw_circle(center + Vector2(item.x, item.y), item.z, Color(0.36, 0.18, 0.08, alpha))
		draw_arc(center + Vector2(item.x - 3, item.y - 4), item.z * 0.62, PI * 1.15, PI * 1.75, 10, Color(0.62, 0.34, 0.14, alpha), 3)
	if highlight > 0.0:
		for ray in range(6):
			var angle := TAU * float(ray) / 6.0 + current_time
			var start := center + Vector2(cos(angle), sin(angle)) * 37.0
			draw_line(start, start + Vector2(cos(angle), sin(angle)) * (8.0 + 5.0 * sin(current_time * 6.0)), Color(1.0, 0.85, 0.35, highlight * (1.0 - grab)), 3)

func _draw_character() -> void:
	var enter := _smooth(_ramp(current_time, _time("character_enters"), 1.2))
	var approach := _smooth(_ramp(current_time, _time("character_approaches"), 1.8))
	var exit := _smooth(_ramp(current_time, _time("character_exits"), 1.2))
	var x := lerpf(-355.0, -135.0, enter) + approach * 170.0 + exit * 380.0
	var y := 190.0 + sin(current_time * 8.5) * 3.0 * motion_intensity
	# Sack reacts after the grab.
	var sack_lift := _ramp(current_time, _time("turd_grab"), 0.35)
	draw_circle(Vector2(x - 38, y + 20 - sack_lift * 10.0), 31, Color("8d6b3e"))
	draw_line(Vector2(x - 53, y - 4), Vector2(x - 25, y - 4), Color("38291b"), 5)
	# Primitive articulated beetle with mask, eyes, antennae, and moving legs.
	_draw_ellipse_shape(Vector2(x, y), Vector2(34, 48), Color("222925"))
	draw_circle(Vector2(x, y - 47), 25, Color("303a32"))
	draw_rect(Rect2(x - 24, y - 56, 48, 15), Color("171615"), true)
	draw_circle(Vector2(x - 9, y - 48), 5, Color("e9d8a0")); draw_circle(Vector2(x + 9, y - 48), 5, Color("e9d8a0"))
	draw_line(Vector2(x - 10, y - 69), Vector2(x - 25, y - 88 + sin(current_time * 5.0) * 5), Color("20251f"), 4)
	draw_line(Vector2(x + 10, y - 69), Vector2(x + 25, y - 88 - sin(current_time * 5.0) * 5), Color("20251f"), 4)
	for side in [-1.0, 1.0]:
		for leg in range(3):
			var phase := sin(current_time * 11.0 + leg * 1.7) * 8.0
			draw_line(Vector2(x + side * 24, y - 18 + leg * 24), Vector2(x + side * (52 + phase), y - 27 + leg * 30), Color("171b18"), 5)

func _draw_story_signs() -> void:
	var setup_in := _smooth(_ramp(current_time, _time("setup_sign"), 0.55))
	var setup_out := _smooth(_ramp(current_time, _time("turd_highlight"), 0.35))
	if setup_in > 0.0 and setup_out < 1.0:
		_draw_physical_sign(Vector2(-78, -215 - (1.0 - setup_in) * 190), Vector2(360, 112), "beat_1", Color("8f4b2e"), -0.025)
	var protagonist_in := _smooth(_ramp(current_time, _time("protagonist_sign"), 0.5))
	var protagonist_out := _smooth(_ramp(current_time, _time("turd_grab"), 0.3))
	if protagonist_in > 0.0 and protagonist_out < 1.0:
		_draw_physical_sign(Vector2(-82, -210), Vector2(330, 96), "beat_2", Color("d0c28f"), 0.02)
	var punch := _smooth(_ramp(current_time, _time("punch_sign"), 0.18))
	var title := _smooth(_ramp(current_time, _time("title_reveal"), 0.42))
	if punch > 0.0 and title < 1.0:
		_draw_physical_sign(Vector2(-25, -165 + (1.0 - punch) * 80), Vector2(330, 76), "beat_4", Color("d4b863"), -0.018)
	if title > 0.0:
		var settle := 1.0 + sin((current_time - _time("title_reveal")) * 13.0) * exp(-(current_time - _time("title_reveal")) * 4.5) * 0.08
		draw_set_transform(Vector2(0, -130), -0.018, Vector2.ONE * settle)
		draw_rect(Rect2(-220, -110, 440, 220), Color("294637"), true)
		draw_rect(Rect2(-220, -110, 440, 220), Color("111d17"), false, 7)
		_draw_centered_lines("beat_5", Vector2.ZERO, Color("f4df9d"))
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

func _draw_physical_sign(center: Vector2, size: Vector2, key: String, fill: Color, rotation: float) -> void:
	draw_set_transform(center, rotation)
	draw_rect(Rect2(-size / 2.0 + Vector2(7, 9), size), Color(0.03, 0.02, 0.015, 0.6), true)
	draw_rect(Rect2(-size / 2.0, size), fill, true)
	draw_rect(Rect2(-size / 2.0, size), Color("35231a"), false, 5)
	draw_circle(Vector2(-size.x / 2 + 15, -size.y / 2 + 15), 4, Color("302c27")); draw_circle(Vector2(size.x / 2 - 15, -size.y / 2 + 15), 4, Color("302c27"))
	_draw_centered_lines(key, Vector2.ZERO, Color("231a15"))
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

func _draw_centered_lines(key: String, center: Vector2, color: Color) -> void:
	if not layouts.has(key): return
	var layout: Dictionary = layouts[key]
	var font_size := mini(int(layout.font_size), 31)
	var line_height := float(font_size) * 1.08
	var start_y := center.y - line_height * float(layout.lines.size() - 1) / 2.0 + float(font_size) * 0.35
	for index in range(layout.lines.size()):
		var text: String = layout.lines[index]
		var width := heavy_font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
		draw_string(heavy_font, Vector2(center.x - width / 2.0, start_y + index * line_height), text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, color)

func _draw_ellipse_shape(center: Vector2, radii: Vector2, color: Color) -> void:
	var points := PackedVector2Array()
	for index in range(32):
		var angle := TAU * float(index) / 32.0
		points.append(center + Vector2(cos(angle) * radii.x, sin(angle) * radii.y))
	draw_colored_polygon(points, color)

func _time(id: String) -> float:
	for event in events:
		if str(event.id) == id: return float(event.time)
	return scene_end + 10.0

func _ramp(value: float, start: float, duration: float) -> float:
	return clampf((value - start) / maxf(duration, 0.001), 0.0, 1.0)

func _smooth(value: float) -> float:
	return value * value * (3.0 - 2.0 * value)
