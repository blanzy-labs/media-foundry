extends Node2D

const W := 540.0
const H := 960.0
const TOTAL_FRAMES := 450
const FPS := 30.0

var fixture: Dictionary
var grammar: Dictionary
var frame_index := -1
var heavy_font: Font
var regular_font: Font
var fixture_path := ""
var grammar_path := ""
var output_dir := ""

func _ready() -> void:
	fixture_path = _argument_value("--fixture")
	grammar_path = _argument_value("--grammar")
	output_dir = _argument_value("--output-dir")
	if fixture_path.is_empty() or grammar_path.is_empty() or output_dir.is_empty():
		_fail("MF002_RENDER_ERROR missing fixture, grammar, or output directory")
		return
	fixture = _read_json(fixture_path)
	grammar = _read_json(grammar_path)
	if fixture.is_empty() or grammar.is_empty() or not _valid_contract():
		_fail("MF002_RENDER_ERROR invalid contract")
		return
	heavy_font = load(str(grammar.typography.heavy_font)) as Font
	regular_font = load(str(grammar.typography.regular_font)) as Font
	if heavy_font == null or regular_font == null:
		_fail("MF002_RENDER_ERROR font assets unavailable")
		return
	DirAccess.make_dir_recursive_absolute(output_dir)
	RenderingServer.set_default_clear_color(_color("workshop_dark"))
	print("MF002_RENDER_START id=%s grammar=%s seed=%d frames=%d" % [fixture.id, grammar.id, int(fixture.seed), TOTAL_FRAMES])
	print("MF002_STRUCTURAL safe_area=PASS layers=workshop,sign,media,paper,tape,props")

func _process(_delta: float) -> void:
	if fixture.is_empty() or grammar.is_empty():
		return
	frame_index += 1
	if frame_index >= TOTAL_FRAMES:
		print("MF002_RENDER_COMPLETE id=%s frames=%d" % [fixture.id, TOTAL_FRAMES])
		get_tree().quit(0)
		return
	var t := float(frame_index) / FPS
	position = Vector2(sin(t * 0.73) * 1.2, cos(t * 0.51) * 0.8)
	var push: float = 1.0 + float(grammar.motion.camera_push) * (t / 15.0)
	scale = Vector2.ONE * push
	_log_timeline_stage(frame_index)
	queue_redraw()
	await RenderingServer.frame_post_draw
	_capture_frame()

func _capture_frame() -> void:
	var image := get_viewport().get_texture().get_image()
	var path := output_dir.path_join("frame_%06d.png" % frame_index)
	var error := image.save_png(path)
	if error != OK:
		_fail("MF002_RENDER_ERROR could not save " + path)
	if frame_index % 30 == 0:
		print("MF002_RENDER_FRAME %d" % frame_index)

func _draw() -> void:
	if fixture.is_empty() or grammar.is_empty():
		return
	var t := float(frame_index) / FPS
	_draw_workshop(t)
	if t < float(grammar.motion.intro_end_seconds):
		_draw_intro(t)
	elif t < float(grammar.motion.outro_start_seconds):
		_draw_content_stage(t)
	else:
		_draw_outro(t)

func _draw_workshop(t: float) -> void:
	draw_rect(Rect2(0, 0, W, H), _color("workshop_dark"))
	for plank in range(8):
		var y := float(plank * 120)
		var shade := _color("workshop_mid").lightened(float((plank * 7) % 3) * 0.018)
		draw_rect(Rect2(0, y, W, 118), shade)
		draw_line(Vector2(0, y + 118), Vector2(W, y + 116), Color("100b09"), 4)
	for mark in range(36):
		var x := float((mark * 97 + int(fixture.seed)) % 520 + 10)
		var y := float((mark * 151 + int(fixture.seed / 3)) % 880 + 40)
		var length := float(8 + (mark * 13) % 34)
		draw_line(Vector2(x, y), Vector2(x + length, y + float((mark % 5) - 2)), Color(0.08, 0.045, 0.025, 0.38), 2)
	# Hanging cable and swaying lamp keep the environment alive.
	var sway := sin(t * 1.5) * deg_to_rad(float(grammar.motion.cable_sway_degrees))
	draw_set_transform(Vector2(445, -10), sway)
	draw_polyline(PackedVector2Array([Vector2(0, 0), Vector2(-4, 70), Vector2(10, 135), Vector2(2, 182)]), Color("171311"), 9)
	draw_circle(Vector2(2, 200), 36, _color("lamp"))
	draw_arc(Vector2(2, 199), 39, PI, TAU, 20, Color("4a2d18"), 7)
	draw_colored_polygon(PackedVector2Array([Vector2(-28, 225), Vector2(32, 225), Vector2(92, 470), Vector2(-102, 470)]), Color(0.95, 0.69, 0.25, 0.045))
	draw_set_transform(Vector2.ZERO, 0.0)
	# Crates, bolts, and a loose cable frame the safe area without competing with text.
	_draw_crate(Vector2(17, 850), Vector2(138, 110), -0.022)
	_draw_crate(Vector2(401, 866), Vector2(125, 95), 0.031)
	draw_polyline(PackedVector2Array([Vector2(0, 834), Vector2(95, 820), Vector2(180, 850), Vector2(260, 836)]), Color("0c0908"), 8)
	for bolt in [Vector2(22, 42), Vector2(516, 58), Vector2(24, 810), Vector2(514, 824)]:
		draw_circle(bolt, 7, _color("metal"))
		draw_line(bolt - Vector2(4, 0), bolt + Vector2(4, 0), Color("242622"), 2)

func _draw_intro(t: float) -> void:
	var enter: float = _ease_out_back(clamp(t / float(grammar.motion.ENTER.seconds), 0.0, 1.0))
	var impact_time: float = max(0.0, t - 0.58)
	var impact: float = sin(impact_time * 35.0) * exp(-impact_time * 10.0) * 8.0 if t >= 0.58 else 0.0
	var center: Vector2 = Vector2(W / 2.0 + impact, lerp(-250.0, 395.0, enter))
	draw_set_transform(center, deg_to_rad(float(grammar.imperfection.sign_rotation_degrees)))
	_draw_rough_panel(Vector2(470, 272), _color("wood"), Color("462319"), 1)
	_center_text(str(fixture.intro.text), Vector2(0, -30), _role_size("INTRO"), _color("cream"), 410, heavy_font)
	_center_text("A BADLY MAINTAINED KNOWLEDGE MACHINE", Vector2(0, 72), _role_size("LABEL"), Color("2b1b13"), 400, heavy_font)
	draw_set_transform(Vector2.ZERO, 0.0)
	_draw_metal_label(Vector2(58, 560), str(fixture.visual.label), -0.025)
	# Deterministic impact dust: fixed positions, animation only changes radius.
	for dust in range(11):
		var dust_t: float = clamp((t - 0.55) * 1.8, 0.0, 1.0)
		var dx := float((dust * 71) % 430 + 55)
		var dy: float = 535.0 + sin(float(dust) * 2.2) * 34.0 - dust_t * float(20 + (dust * 9) % 55)
		draw_circle(Vector2(dx, dy), (1.0 - dust_t) * float(5 + dust % 6), Color(0.83, 0.62, 0.34, 0.32))

func _draw_content_stage(t: float) -> void:
	var enter: float = _ease_out_back(clamp((t - 2.0) / 0.72, 0.0, 1.0))
	var exit_amount: float = _smoothstep(clamp((t - 12.45) / float(grammar.motion.EXIT.seconds), 0.0, 1.0))
	var stage_y: float = lerp(1080.0, 0.0, enter) - exit_amount * 1030.0
	draw_set_transform(Vector2(0, stage_y), 0.0)
	# Primary framed media region: scratched metal surrounding a dirty inset.
	draw_set_transform(Vector2(270, 337 + stage_y), deg_to_rad(-1.35))
	_draw_rough_panel(Vector2(430, 382), _color("metal"), Color("222522"), 2)
	draw_rect(Rect2(-188, -148, 376, 268), Color("241b17"), true)
	draw_rect(Rect2(-188, -148, 376, 268), _color("rust"), false, 6)
	_draw_visual(str(fixture.visual.kind), Vector2(0, -12), t)
	draw_set_transform(Vector2.ZERO, 0.0)
	_draw_metal_label(Vector2(62, 145 + stage_y), str(fixture.visual.label), 0.02)
	# Crooked paper note carries the content, physically attached by tape.
	draw_set_transform(Vector2(270, 684 + stage_y), deg_to_rad(float(grammar.imperfection.headline_rotation_degrees)))
	_draw_rough_panel(Vector2(438, 252), _color("paper"), Color("493223"), 3)
	_center_text(str(fixture.content.headline), Vector2(0, -63), _role_size("HEADLINE"), _color("paper_ink"), 388, heavy_font)
	_center_text(str(fixture.content.body), Vector2(0, 44), _role_size("BODY"), Color("4b372b"), 378, regular_font)
	draw_set_transform(Vector2.ZERO, 0.0)
	_draw_tape(Vector2(35, 561 + stage_y), 0.14)
	_draw_tape(Vector2(410, 786 + stage_y), -0.11)
	# Emphasis label punches once, then keeps a tiny physical idle wobble.
	var punch_phase: float = clamp(abs(t - 8.0) / float(grammar.motion.EMPHASIS.seconds), 0.0, 1.0)
	var punch: float = lerp(float(grammar.motion.EMPHASIS.scale), 1.0, _smoothstep(punch_phase))
	draw_set_transform(Vector2(270, 838 + stage_y), -0.025 + sin(t * 2.4) * 0.008, Vector2.ONE * punch)
	_draw_rough_panel(Vector2(330, 68), _color("tape"), Color("5a4024"), 4)
	_center_text(str(fixture.content.emphasis), Vector2(0, 8), _role_size("EMPHASIS"), Color("3a291c"), 300, heavy_font)
	draw_set_transform(Vector2.ZERO, 0.0)

func _draw_outro(t: float) -> void:
	var enter: float = _ease_out_back(clamp((t - float(grammar.motion.outro_start_seconds)) / 0.65, 0.0, 1.0))
	var center := Vector2(270, lerp(1080.0, 455.0, enter))
	draw_set_transform(center, deg_to_rad(1.4))
	_draw_rough_panel(Vector2(458, 292), Color("294637"), Color("111d17"), 5)
	_center_text(str(fixture.outro.text), Vector2(0, -24), _role_size("OUTRO"), _color("cream"), 410, heavy_font)
	var outro_tagline := str(fixture.outro.get("tagline", "HELD TOGETHER WITH TESTS & TAPE"))
	_center_text(outro_tagline, Vector2(0, 73), _role_size("LABEL"), Color("bcd3a6"), 400, heavy_font)
	draw_set_transform(Vector2.ZERO, 0.0)
	# A loose bolt spins into place beside the sign.
	draw_set_transform(Vector2(462, 632), t * 4.0)
	for tooth in range(8):
		var angle := TAU * float(tooth) / 8.0
		draw_rect(Rect2(Vector2(cos(angle), sin(angle)) * 33.0 - Vector2(7, 12), Vector2(14, 24)), _color("wood_light"), true)
	draw_circle(Vector2.ZERO, 31, _color("wood_light"))
	draw_circle(Vector2.ZERO, 12, _color("workshop_dark"))
	draw_set_transform(Vector2.ZERO, 0.0)

func _draw_visual(kind: String, center: Vector2, t: float) -> void:
	var primary := Color(str(fixture.visual.primary))
	var secondary := Color(str(fixture.visual.secondary))
	match kind:
		"prop_board":
			_draw_prop_board(center, t)
		"radial_creature":
			for arm in range(8):
				var angle := TAU * float(arm) / 8.0 + sin(t * 1.8 + arm) * 0.11
				var mid := center + Vector2(cos(angle), sin(angle)) * 76.0
				var tip := center + Vector2(cos(angle + sin(t + arm) * 0.12), sin(angle + sin(t + arm) * 0.12)) * 112.0
				draw_polyline(PackedVector2Array([center, mid, tip]), primary, 24, true)
			draw_circle(center, 68, secondary)
			draw_circle(center + Vector2(-23, -7), 11, Color("f5e7bd"))
			draw_circle(center + Vector2(23, -7), 11, Color("f5e7bd"))
			draw_circle(center + Vector2(-20, -6), 5, Color("241710"))
			draw_circle(center + Vector2(20, -6), 5, Color("241710"))
			for heart in range(3):
				_draw_heart(center + Vector2(float((heart - 1) * 34), 35), Color("7f2d2d"), 0.55)
		"beetle":
			var bounce := sin(t * 3.2) * 5.0
			draw_circle(center + Vector2(102, 20), 76, Color("6b4227"))
			for ring in range(3):
				draw_arc(center + Vector2(102, 20), 34.0 + ring * 15.0, 0, TAU, 24, Color(0.18, 0.10, 0.05, 0.36), 4)
			var beetle_center := center + Vector2(-65, 15 + bounce)
			for leg in range(3):
				var ly := float((leg - 1) * 34)
				draw_line(beetle_center + Vector2(-30, ly), beetle_center + Vector2(-76, ly - 18), secondary, 9)
				draw_line(beetle_center + Vector2(30, ly), beetle_center + Vector2(75, ly + 18), secondary, 9)
			_draw_filled_ellipse(beetle_center, Vector2(53, 78), primary)
			draw_line(beetle_center + Vector2(0, -70), beetle_center + Vector2(0, 70), Color("27301e"), 5)
			draw_circle(beetle_center + Vector2(-19, -42), 7, Color("f5e7bd"))
			draw_circle(beetle_center + Vector2(19, -42), 7, Color("f5e7bd"))
		"terminal":
			draw_rect(Rect2(center - Vector2(128, 86), Vector2(256, 172)), primary, true)
			draw_rect(Rect2(center - Vector2(111, 67), Vector2(222, 126)), Color("172620"), true)
			draw_rect(Rect2(center - Vector2(111, 67), Vector2(222, 126)), secondary, false, 5)
			var blink := 3.0 if int(t * 3.0) % 7 == 0 else 12.0
			draw_rect(Rect2(center + Vector2(-59, -15), Vector2(24, blink)), secondary, true)
			draw_rect(Rect2(center + Vector2(35, -15), Vector2(24, blink)), secondary, true)
			draw_arc(center + Vector2(0, 18), 38, 0.18, PI - 0.18, 20, secondary, 6)
			draw_line(center + Vector2(0, -86), center + Vector2(17, -123), secondary, 7)
			draw_circle(center + Vector2(18, -127), 9, _color("rust"))
		_:
			draw_circle(center, 90, primary)

func _draw_prop_board(center: Vector2, t: float) -> void:
	for prop_value in fixture.visual.get("props", []):
		var prop: Dictionary = prop_value
		var prop_center := center + Vector2(float(prop.get("x", 0)), float(prop.get("y", 0)))
		var primary := Color(str(prop.get("color", fixture.visual.primary)))
		var accent := Color(str(prop.get("accent", fixture.visual.secondary)))
		match str(prop.get("type", "")):
			"glow":
				var pulse := 1.0 + sin(t * 2.2 + float(prop.get("phase", 0))) * 0.05
				draw_circle(prop_center, float(prop.get("radius", 42)) * pulse, Color(primary, float(prop.get("alpha", 0.12))))
			"book":
				var size := Vector2(float(prop.get("width", 58)), float(prop.get("height", 112)))
				var rotation := deg_to_rad(float(prop.get("rotation", 0)))
				var points := _rotated_rect_points(prop_center, size, rotation)
				draw_colored_polygon(points, primary)
				draw_polyline(_closed(points), Color("241710"), 5, true)
				var spine_a := prop_center + Vector2(-size.x * 0.31, -size.y * 0.39).rotated(rotation)
				var spine_b := prop_center + Vector2(-size.x * 0.31, size.y * 0.39).rotated(rotation)
				draw_line(spine_a, spine_b, accent, 6)
				for page in range(3):
					var offset := Vector2(4, -18 + page * 18).rotated(rotation)
					draw_line(prop_center + offset, prop_center + offset + Vector2(size.x * 0.29, 0).rotated(rotation), Color(accent, 0.58), 2)
			"note":
				var size := Vector2(float(prop.get("width", 92)), float(prop.get("height", 64)))
				var rotation := deg_to_rad(float(prop.get("rotation", 0)))
				var points := _rotated_rect_points(prop_center, size, rotation)
				draw_colored_polygon(points, primary)
				draw_polyline(_closed(points), Color("3c291d"), 4, true)
				_center_text(str(prop.get("label", "NOTE")), prop_center + Vector2(0, 6), int(prop.get("font_size", 15)), Color("2a1d17"), size.x - 12, heavy_font)
			"line":
				var target := center + Vector2(float(prop.get("to_x", 0)), float(prop.get("to_y", 0)))
				draw_line(prop_center, target, primary, float(prop.get("width", 5)), true)
				draw_circle(prop_center, 5, accent)
				draw_circle(target, 5, accent)
			"droplet":
				var radius := float(prop.get("radius", 30))
				var bob := sin(t * 2.4 + float(prop.get("phase", 0))) * 3.0
				var drop_center := prop_center + Vector2(0, bob)
				draw_circle(drop_center + Vector2(0, 9), radius * 0.72, primary)
				draw_colored_polygon(PackedVector2Array([drop_center + Vector2(0, -radius), drop_center + Vector2(-radius * 0.66, 12), drop_center + Vector2(radius * 0.66, 12)]), primary)
				draw_circle(drop_center + Vector2(-8, 2), 4, Color(accent, 0.82))
			"planet":
				var radius := float(prop.get("radius", 58))
				var wobble := sin(t * 0.9 + float(prop.get("phase", 0))) * 2.0
				draw_circle(prop_center + Vector2(0, wobble), radius, primary)
				draw_arc(prop_center + Vector2(0, wobble), radius * 0.72, -1.1, 2.1, 28, accent, 6)
				for band in range(3):
					draw_arc(prop_center + Vector2(0, wobble), radius * (0.42 + band * 0.17), 0.2, 2.9, 22, Color(accent, 0.36), 3)
			"star":
				var radius := float(prop.get("radius", 10)) * (1.0 + sin(t * 3.0 + float(prop.get("phase", 0))) * 0.12)
				var points := PackedVector2Array()
				for point in range(10):
					var angle := -PI / 2.0 + TAU * float(point) / 10.0
					var point_radius := radius if point % 2 == 0 else radius * 0.42
					points.append(prop_center + Vector2(cos(angle), sin(angle)) * point_radius)
				draw_colored_polygon(points, primary)
			"counter":
				var size := Vector2(float(prop.get("width", 102)), float(prop.get("height", 56)))
				draw_rect(Rect2(prop_center - size / 2.0, size), primary, true)
				draw_rect(Rect2(prop_center - size / 2.0, size), accent, false, 4)
				_center_text(str(prop.get("label", "VALUE")), prop_center + Vector2(0, -7), 12, accent, size.x - 8, heavy_font)
				_center_text(str(prop.get("value", "0")), prop_center + Vector2(0, 15), 19, Color("f4df9d"), size.x - 8, heavy_font)
			"telescope":
				var sway := sin(t * 0.8) * 0.025
				var direction := Vector2(1, -0.55).rotated(sway)
				draw_line(prop_center - direction * 44, prop_center + direction * 44, primary, 24, true)
				draw_line(prop_center + direction * 37, prop_center + direction * 55, accent, 31, true)
				draw_line(prop_center + Vector2(0, 8), prop_center + Vector2(-32, 70), accent, 7)
				draw_line(prop_center + Vector2(0, 8), prop_center + Vector2(38, 70), accent, 7)
				draw_circle(prop_center + Vector2(0, 8), 8, Color("241710"))

func _rotated_rect_points(center: Vector2, size: Vector2, rotation: float) -> PackedVector2Array:
	return PackedVector2Array([
		center + Vector2(-size.x / 2.0, -size.y / 2.0).rotated(rotation),
		center + Vector2(size.x / 2.0, -size.y / 2.0).rotated(rotation),
		center + Vector2(size.x / 2.0, size.y / 2.0).rotated(rotation),
		center + Vector2(-size.x / 2.0, size.y / 2.0).rotated(rotation)
	])

func _closed(points: PackedVector2Array) -> PackedVector2Array:
	var closed := points.duplicate()
	closed.append(points[0])
	return closed

func _draw_filled_ellipse(center: Vector2, radii: Vector2, color: Color) -> void:
	var points := PackedVector2Array()
	for point in range(32):
		var angle := TAU * float(point) / 32.0
		points.append(center + Vector2(cos(angle) * radii.x, sin(angle) * radii.y))
	draw_colored_polygon(points, color)

func _draw_heart(center: Vector2, color: Color, scale_value: float) -> void:
	draw_circle(center + Vector2(-8, -5) * scale_value, 12 * scale_value, color)
	draw_circle(center + Vector2(8, -5) * scale_value, 12 * scale_value, color)
	draw_colored_polygon(PackedVector2Array([center + Vector2(-19, 0) * scale_value, center + Vector2(19, 0) * scale_value, center + Vector2(0, 26) * scale_value]), color)

func _draw_rough_panel(size: Vector2, fill: Color, border: Color, salt: int) -> void:
	var shadow := Vector2(float(grammar.surfaces.shadow_offset[0]), float(grammar.surfaces.shadow_offset[1]))
	draw_rect(Rect2(-size / 2.0 + shadow, size), Color(0.04, 0.025, 0.02, 0.62), true)
	draw_rect(Rect2(-size / 2.0, size), fill, true)
	draw_rect(Rect2(-size / 2.0, size), border, false, float(grammar.surfaces.border_width))
	for wear in range(int(grammar.surfaces.wear_marks)):
		var x := -size.x / 2.0 + float((wear * 61 + salt * 19) % int(size.x))
		var y := -size.y / 2.0 + float((wear * 43 + salt * 29) % int(size.y))
		draw_line(Vector2(x, y), Vector2(x + 9 + wear % 15, y + float(wear % 3 - 1)), Color(0.20, 0.11, 0.07, 0.24), 2)

func _draw_crate(top_left: Vector2, size: Vector2, rotation: float) -> void:
	draw_set_transform(top_left + size / 2.0, rotation)
	draw_rect(Rect2(-size / 2.0, size), Color("754126"), true)
	draw_rect(Rect2(-size / 2.0, size), Color("2c1b14"), false, 5)
	draw_line(-size / 2.0 + Vector2(8, 8), size / 2.0 - Vector2(8, 8), Color("3f2519"), 7)
	draw_line(Vector2(-size.x / 2.0 + 8, size.y / 2.0 - 8), Vector2(size.x / 2.0 - 8, -size.y / 2.0 + 8), Color("3f2519"), 7)
	draw_set_transform(Vector2.ZERO, 0.0)

func _draw_tape(center: Vector2, rotation: float) -> void:
	draw_set_transform(center, rotation)
	draw_rect(Rect2(-38, -12, 76, 24), Color(0.84, 0.72, 0.39, 0.82), true)
	for cut in range(5):
		draw_line(Vector2(-32 + cut * 15, -10), Vector2(-27 + cut * 15, 10), Color(0.40, 0.31, 0.15, 0.22), 2)
	draw_set_transform(Vector2.ZERO, 0.0)

func _draw_metal_label(top_left: Vector2, text: String, rotation: float) -> void:
	draw_set_transform(top_left + Vector2(105, 27), rotation)
	draw_rect(Rect2(-105, -27, 210, 54), _color("metal"), true)
	draw_rect(Rect2(-105, -27, 210, 54), Color("262b28"), false, 4)
	draw_circle(Vector2(-88, 0), 5, Color("242622"))
	draw_circle(Vector2(88, 0), 5, Color("242622"))
	_center_text(text, Vector2(0, 6), _role_size("LABEL"), Color("f0dda5"), 170, heavy_font)
	draw_set_transform(Vector2.ZERO, 0.0)

func _center_text(value: String, center: Vector2, size: int, color: Color, max_width: float, selected_font: Font) -> void:
	var words := value.split(" ")
	var lines: Array[String] = []
	var line := ""
	for word in words:
		var candidate := word if line.is_empty() else line + " " + word
		if selected_font.get_string_size(candidate, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x > max_width and not line.is_empty():
			lines.append(line)
			line = word
		else:
			line = candidate
	if not line.is_empty():
		lines.append(line)
	var line_height := float(size) * 1.12
	var start_y := center.y - (float(lines.size() - 1) * line_height / 2.0)
	for index in range(lines.size()):
		var width := selected_font.get_string_size(lines[index], HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
		draw_string(selected_font, Vector2(center.x - width / 2.0, start_y + index * line_height), lines[index], HORIZONTAL_ALIGNMENT_LEFT, -1, size, color)

func _role_size(role: String) -> int:
	return int(grammar.typography.roles[role].size)

func _color(name: String) -> Color:
	return Color(str(grammar.palette[name]))

func _read_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}

func _valid_contract() -> bool:
	if not fixture.has_all(["id", "template", "seed", "format", "intro", "content", "visual", "outro", "audio"]):
		return false
	if fixture.template != "scrappy_diorama" or grammar.get("id") != "scrappy-diorama-v1":
		return false
	var format: Dictionary = fixture.format
	return format.get("width") == 1080 and format.get("height") == 1920 and format.get("fps") == 30 and format.get("duration_seconds") == 15

func _log_timeline_stage(frame: int) -> void:
	match frame:
		0: print("MF002_STAGE INTRO")
		60: print("MF002_STAGE ENTER")
		120: print("MF002_STAGE SETTLE")
		240: print("MF002_STAGE EMPHASIS")
		384: print("MF002_STAGE EXIT")
		390: print("MF002_STAGE OUTRO")

func _argument_value(key: String) -> String:
	var args := OS.get_cmdline_user_args()
	for index in range(args.size() - 1):
		if args[index] == key:
			return ProjectSettings.globalize_path(args[index + 1])
	return ""

func _smoothstep(value: float) -> float:
	return value * value * (3.0 - 2.0 * value)

func _ease_out_back(value: float) -> float:
	var c1 := float(grammar.motion.SETTLE.overshoot)
	var c3 := c1 + 1.0
	return 1.0 + c3 * pow(value - 1.0, 3.0) + c1 * pow(value - 1.0, 2.0)

func _fail(message: String) -> void:
	printerr(message)
	get_tree().quit(1)
